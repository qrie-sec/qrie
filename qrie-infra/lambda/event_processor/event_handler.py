import os, json, boto3, datetime, traceback, sys

# Add lambda directory to path for shared modules
lambda_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if lambda_dir not in sys.path:
    sys.path.append(lambda_dir)

from common.logger import debug, info, error
from data_access.policy_manager import PolicyManager
from data_access.inventory_manager import InventoryManager
from common_utils import get_account_from_arn, get_service_from_arn

DDB = boto3.resource('dynamodb')
RES = DDB.Table(os.environ['RESOURCES_TABLE'])
FND = DDB.Table(os.environ['FINDINGS_TABLE'])

def process_event(event, context):
    """
    Process EventBridge events from customer accounts.
    Updates inventory and evaluates policies for changed resources.
    """
    debug(f"Processing event: {event}")
    try:
        policy_manager = PolicyManager()
        inventory_manager = InventoryManager()
        
        for rec in event.get("Records", []):
            event_id = rec.get('messageId', 'unknown')
            try:
                msg = json.loads(rec["body"])
                
                # Extract resource info from CloudTrail event (raises if invalid)
                resource_arn = _extract_arn_from_event(msg)
                account_id = get_account_from_arn(resource_arn)
                service = get_service_from_arn(resource_arn)
                
                info(f"[{event_id}] Processing {service} resource: {resource_arn}")
                
                # Extract event timestamp (raises if invalid)
                try: 
                    event_time = _extract_event_time(msg)
                except Exception as e:
                    error(f"[{event_id}] Error extracting event time: {str(e)}")
                    event_time = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                
                # Check if event is stale compared to existing inventory
                existing_resource = inventory_manager.get_resource_by_arn(resource_arn)
                if existing_resource:
                    existing_snapshot_time = existing_resource['LastSeenAt']
                    if event_time <= existing_snapshot_time:
                        debug(f"[{event_id}] Skipping stale event for {resource_arn} - event time {event_time} <= existing snapshot {existing_snapshot_time}")
                        continue
                
                # Check if there is any change in the resource configuration
                # Capture the time WHEN we fetch the config - this is our snapshot time (milliseconds)
                describe_time_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                new_config = _describe_resource(resource_arn, account_id, service)
                existing_config = existing_resource['Configuration'] if existing_resource else None
                
                if not _configs_differ(existing_config, new_config):
                    debug(f"[{event_id}] No config change for {resource_arn}, skipping")
                    continue
                
                info(f"[{event_id}] Config changed for {resource_arn}, updating inventory and evaluating policies")
                    
                # Update inventory with describe time (when we fetched the config)
                inventory_manager.upsert_resource(
                    account_id=account_id,
                    service=service,
                    arn=resource_arn,
                    configuration=new_config,
                    describe_time_ms=describe_time_ms
                )
                    
                # Get active policies for this service
                service_policies = policy_manager.get_active_policies_for_service(service)
                    
                # Evaluate each policy with the same describe time
                for policy in service_policies:
                    try:
                        evaluator = policy_manager.create_policy_evaluator(policy.policy_id, policy)
                        result = evaluator.evaluate(resource_arn, new_config, describe_time_ms)
                        debug(f"[{event_id}] Evaluated {resource_arn} against {policy.policy_id}: compliant={result['compliant']}, scoped={result.get('scoped', True)}")
                    except Exception as e:
                        error(f"[{event_id}] Error evaluating {resource_arn} with policy {policy.policy_id}: {str(e)}\n{traceback.format_exc()}")
            except Exception as e:
                error(f"[{event_id}] Error processing record: {str(e)}\n{traceback.format_exc()}")
                continue
        
        return {"ok": True}
    except Exception as e:
        error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
        raise  # Let Lambda runtime handle the error


def _extract_arn_from_event(event: dict) -> str:
    """
    Extract resource ARN from CloudTrail event using service-specific extractors.
    
        Args:
            event: CloudTrail event dict (the parsed 'body' from SQS message)
            
        Returns:
            Resource ARN string
            
        Raises:
            ValueError: If ARN cannot be extracted from event
    """
    try:
        detail = event.get('detail', {})
        event_source = detail.get('eventSource', '')
        
        # Map event source to service name
        service_map = {
            's3.amazonaws.com': 's3',
            'ec2.amazonaws.com': 'ec2',
            'iam.amazonaws.com': 'iam'
        }
        
        service = service_map.get(event_source)
        if not service:
            raise ValueError(f"Unsupported event source: {event_source}")
        
        # Use service-specific ARN extractor
        from services import extract_arn_from_event as service_extract_arn
        arn = service_extract_arn(service, detail)
        
        if not arn:
            event_name = detail.get('eventName', '')
            raise ValueError(f"Could not extract ARN from event: source={event_source}, name={event_name}")
        
        return arn
    
    except Exception as e:
        error(f"Error extracting ARN from event: {str(e)}")
        raise ValueError(f"Failed to extract ARN: {str(e)}")


def _extract_event_time(event: dict) -> int:
    """
    Extract event timestamp from CloudTrail event.
    
        Args:
            event: CloudTrail event dict (the parsed 'body' from SQS message)
            
        Returns:
            Timestamp in milliseconds when the event occurred
            
        Raises:
            ValueError: If timestamp cannot be extracted from event
    """
    try:
        detail = event.get('detail', {})
        event_time_str = detail.get('eventTime')
        
        if not event_time_str:
            raise ValueError("No eventTime field in CloudTrail event")
        
        # Parse ISO 8601 timestamp (e.g., "2025-11-05T02:28:06Z")
        event_time = datetime.datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
        
        # Convert to milliseconds
        return int(event_time.timestamp() * 1000)
    
    except Exception as e:
        error(f"Error extracting event time: {str(e)}")
        raise ValueError(f"Failed to extract event time: {str(e)}")


def _describe_resource(arn: str, account_id: str, service: str) -> dict:
    """
    Describe resource using service-specific describe functions.
    
        Args:
            arn: Resource ARN
            account_id: AWS account ID
            service: Service name (s3, ec2, iam, etc.)
            
        Returns:
            Resource configuration dict
            
        Raises:
            ValueError: If resource cannot be described
            ClientError: If AWS API call fails
    """
    try:
        from services import describe_resource as service_describe
        return service_describe(service, arn, account_id)
    
    except Exception as e:
        error(f"Error describing resource {arn}: {str(e)}")
        raise


def _configs_differ(old_config: dict, new_config: dict) -> bool:
    """Compare two configs to see if they differ"""
    if not old_config:
        return True  # No existing config, so it's new
    
    # Normalize configs by removing timestamps and metadata
    def normalize(c):
        if not c:
            return {}
        filtered = {k: v for k, v in c.items() if k not in ['LastSeenAt', 'Metadata', 'LastModified']}
        return json.dumps(filtered, sort_keys=True, default=str)
    
    return normalize(old_config) != normalize(new_config)
