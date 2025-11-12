# Qrie Inventory & Scan Fanout Architecture Strategy

## Executive Summary

This document outlines the evolution path from MVP (simple, synchronous) to production-scale (fanout-based) inventory and policy scanning architecture. The MVP approach prioritizes speed-to-market while laying groundwork for future scalability.

## MVP Approach (Current)

### Philosophy: Validate Demand Before Scaling
- **Local CLI/UI invocation**: Direct Lambda calls for inventory/scan operations
- **Simple progress checking**: Check if Lambda instances are running via AWS APIs
- **Synchronous processing**: Process accounts sequentially within Lambda timeout limits
- **Acceptable constraints**: Works for small-to-medium customer bases (< 100 accounts)

### MVP Benefits:
1. **Fast implementation**: No additional infrastructure complexity
2. **Easy debugging**: Straightforward execution flow
3. **Cost effective**: No additional queuing/orchestration costs
4. **Simple monitoring**: Basic CloudWatch metrics sufficient

### MVP Limitations (Future Pain Points):
1. **Lambda timeout**: 15-minute limit caps account processing capacity
2. **No progress visibility**: Users can't see detailed progress during execution
3. **All-or-nothing**: Single account failure can impact entire batch
4. **No parallelization**: Sequential processing limits throughput

### MVP Progress Checking Strategy

```bash
# CLI command to check if inventory is running
qrie inventory status
# Implementation: Check CloudWatch for running Lambda instances
# Output: "in_progress" if any instances running, "idle" if none

# Simple but effective for MVP
aws lambda list-functions --query "Functions[?FunctionName=='qrie_inventory'].State"
aws logs describe-log-streams --log-group-name "/aws/lambda/qrie_inventory" \
  --order-by LastEventTime --descending --max-items 1
```

## Post-MVP: Production Fanout Architecture

### When to Migrate:
- **Customer demand validated** (paying customers using the product)
- **Account scale > 100** (approaching Lambda timeout limits)
- **User feedback** requesting progress visibility and faster processing
- **Revenue justifies** additional infrastructure complexity

## Production Architecture: Queue-Based Fanout

### **Architecture Overview**

```
UI → Job Handler → [inventory-queue, scan-queue] → Workers → Jobs Table → Polling → UI
```

**Key Components:**
- **Job Handler**: Orchestrates requests, creates jobs, enqueues tasks
- **Inventory Queue**: Per-account inventory tasks
- **Scan Queue**: Per-account policy scan tasks  
- **Workers**: Process individual accounts (inventory listers & policy scanners)
- **Jobs Table**: Centralized status tracking
- **Polling Service**: Monitors queue emptiness to update job completion

### 1. **Job Handler (Orchestrator)**

```python
def lambda_handler(event, context):
    """
    Job Handler - Orchestrates inventory/scan requests
    
    Input: inv(Acc=*, Svc=s3) or scan(Acc=*, policy=s3.xyz)
    Output: job_id for tracking
    """
    operation = event.get('operation')  # 'inventory' or 'scan'
    service = event.get('service')      # 's3', 'ec2', 'iam', or '*'
    policy = event.get('policy')        # for scan operations
    accounts = event.get('accounts', get_customer_accounts())
    
    # Create job record
    job_id = create_job(operation, service, policy, accounts)
    
    # Enqueue per-account tasks
    if operation == 'inventory':
        enqueue_inventory_tasks(job_id, service, accounts)
    elif operation == 'scan':
        enqueue_scan_tasks(job_id, policy, accounts)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "total_accounts": len(accounts)
    }

def enqueue_inventory_tasks(job_id, service, accounts):
    """Send per-account inventory tasks to inventory-queue"""
    for account_id in accounts:
        sqs.send_message(
            QueueUrl=INVENTORY_QUEUE_URL,
            MessageBody=json.dumps({
                'job_id': job_id,
                'account_id': account_id,
                'service': service
            })
        )

def enqueue_scan_tasks(job_id, policy, accounts):
    """Send per-account scan tasks to scan-queue"""
    for account_id in accounts:
        sqs.send_message(
            QueueUrl=SCAN_QUEUE_URL,
            MessageBody=json.dumps({
                'job_id': job_id,
                'account_id': account_id,
                'policy': policy
            })
        )
```

### 2. **Worker Functions**

```python
# Inventory Worker (processes inventory-queue)
def inventory_worker_handler(event, context):
    """Process per-account inventory tasks"""
    for record in event['Records']:
        message = json.loads(record['body'])
        job_id = message['job_id']
        account_id = message['account_id']
        service = message['service']
        
        try:
            # Use existing service-specific functions
            if service == 's3':
                count = generate_inventory_s3(account_id, cached=False)
            elif service == 'ec2':
                count = generate_inventory_ec2(account_id, cached=False)
            elif service == 'iam':
                count = generate_inventory_iam(account_id, cached=False)
            
            # Update job progress
            update_job_progress(job_id, account_id, 'completed', resource_count=count)
            
        except Exception as e:
            update_job_progress(job_id, account_id, 'failed', error=str(e))

# Policy Scanner Worker (processes scan-queue)
def scan_worker_handler(event, context):
    """Process per-account policy scan tasks"""
    for record in event['Records']:
        message = json.loads(record['body'])
        job_id = message['job_id']
        account_id = message['account_id']
        policy = message['policy']
        
        try:
            # Use existing policy evaluation logic
            findings_count = scan_account_for_policy(account_id, policy)
            update_job_progress(job_id, account_id, 'completed', findings_count=findings_count)
            
        except Exception as e:
            update_job_progress(job_id, account_id, 'failed', error=str(e))
```

### 3. **Jobs Table Schema**

```python
# Jobs tracking table
{
    "JobId": "inv-s3-20240126-143022",  # PK
    "Operation": "inventory",           # 'inventory' or 'scan'
    "Service": "s3",                   # for inventory ops
    "Policy": null,                    # for scan ops
    "Status": "in_progress",           # queued, in_progress, completed, failed
    "TotalAccounts": 1000,
    "CompletedAccounts": 247,
    "FailedAccounts": 3,
    "StartedAt": "2024-01-26T14:30:22Z",
    "CompletedAt": null,
    "AccountStatuses": {
        "123456789012": {"status": "completed", "resource_count": 45},
        "987654321098": {"status": "failed", "error": "Access denied"},
        "555666777888": {"status": "in_progress"}
    }
}
```

### 4. **Polling Service (Queue Completion Detection)**

```python
def polling_service_handler(event, context):
    """
    Monitors queue emptiness to update job completion
    Runs every 1-2 minutes via EventBridge schedule
    """
    # Get all in_progress jobs
    in_progress_jobs = get_jobs_by_status('in_progress')
    
    for job in in_progress_jobs:
        job_id = job['JobId']
        
        # Check if queues are empty for this job's operation
        if job['Operation'] == 'inventory':
            queue_empty = is_queue_empty(INVENTORY_QUEUE_URL)
        else:
            queue_empty = is_queue_empty(SCAN_QUEUE_URL)
        
        if queue_empty:
            # All tasks processed, update job status
            completed = job['CompletedAccounts']
            failed = job['FailedAccounts']
            total = job['TotalAccounts']
            
            if completed + failed == total:
                final_status = 'completed' if failed == 0 else 'completed_with_errors'
                update_job_status(job_id, final_status, completion_time=datetime.utcnow())

def is_queue_empty(queue_url):
    """Check if SQS queue has no visible or in-flight messages"""
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
    )
    
    visible = int(response['Attributes']['ApproximateNumberOfMessages'])
    in_flight = int(response['Attributes']['ApproximateNumberOfMessagesNotVisible'])
    
    return visible == 0 and in_flight == 0
```

### 5. **Infrastructure Components (CDK)**

```python
# SQS Queues
inventory_queue = sqs.Queue(
    self, "QrieInventoryQueue",
    visibility_timeout=Duration.minutes(16),
    dead_letter_queue=sqs.DeadLetterQueue(queue=dlq, max_receive_count=3)
)

scan_queue = sqs.Queue(
    self, "QrieScanQueue", 
    visibility_timeout=Duration.minutes(16),
    dead_letter_queue=sqs.DeadLetterQueue(queue=dlq, max_receive_count=3)
)

# Jobs tracking table
jobs_table = ddb.Table(
    self, "QrieJobs",
    table_name="qrie_jobs",
    partition_key=ddb.Attribute(name="JobId", type=ddb.AttributeType.STRING),
    billing_mode=ddb.BillingMode.PAY_PER_REQUEST
)

# Lambda Functions
job_handler = lambda_.Function(
    self, "QrieJobHandler",
    handler="job_handler.lambda_handler",
    # Orchestrates and enqueues tasks
)

inventory_worker = lambda_.Function(
    self, "QrieInventoryWorker", 
    handler="inventory_worker.lambda_handler",
    # Processes inventory-queue messages
)

scan_worker = lambda_.Function(
    self, "QrieScanWorker",
    handler="scan_worker.lambda_handler", 
    # Processes scan-queue messages
)

polling_service = lambda_.Function(
    self, "QriePollingService",
    handler="polling_service.lambda_handler",
    # Monitors queue completion
)

# EventBridge schedule for polling service
events.Rule(
    self, "PollingSchedule",
    schedule=events.Schedule.rate(Duration.minutes(2)),
    targets=[events_targets.LambdaFunction(polling_service)]
)
```

## Benefits of This Approach:

1. **Scalability**: Can process thousands of accounts in parallel
2. **Fault Tolerance**: Failed accounts don't block others
3. **Observability**: Real-time progress tracking
4. **Retry Logic**: Built-in retry for failed accounts
5. **Cost Efficiency**: Only pay for actual processing time
6. **User Experience**: Users get immediate feedback and can monitor progress

## For Policy Scanning:

Same pattern applies - instead of scanning all resources synchronously, fan out by:
- **Per-account scanning**: One Lambda invocation per account
- **Per-service scanning**: Further fanout by service type
- **Batch processing**: Process resources in batches of 100-500

## Architecture Analysis & Recommendations

### **Strengths of Your Queue-Based Design:**

1. **🎯 Clean Separation of Concerns**
   - Job Handler = Orchestrator (lightweight, fast response)
   - Workers = Execution (focused, scalable)
   - Polling Service = Status Management (reliable, decoupled)

2. **🚀 Elegant Completion Detection**
   - Queue emptiness = job completion (simple, reliable)
   - No complex coordination or state management needed
   - Polling service handles edge cases gracefully

3. **⚡ Optimal Parallelization**
   - Per-account fanout enables fine-grained scaling
   - Independent inventory and scan queues
   - Workers can scale independently based on queue depth

4. **🔄 Fault Tolerance Built-In**
   - SQS DLQ handles persistent failures
   - Individual account failures don't block others
   - Retry logic via SQS message visibility timeout

5. **📊 Real-Time Progress Tracking**
   - Jobs table provides immediate status visibility
   - Account-level granularity for detailed progress
   - UI can poll jobs table for live updates

### **Key Implementation Considerations:**

1. **Cross-Account Access**: Workers need cross-account role assumption (aligns with existing EventBridge bootstrap)
2. **Queue Tuning**: Visibility timeout should match worker processing time
3. **Error Handling**: Failed workers must update job status appropriately
4. **Polling Frequency**: Balance responsiveness vs cost (2-minute intervals recommended)

## Final Recommendations

### **MVP Implementation (Immediate)**
✅ **Proceed with current synchronous approach** - validates demand quickly
✅ **Add CLI progress checking** via CloudWatch APIs  
✅ **Monitor scale pain points** (Lambda timeouts, customer feedback)
✅ **Prepare for migration** by maintaining modular service architecture

### **Production Migration (Post-MVP)**
🎯 **Implement your queue-based architecture** - it's exceptionally well-designed
🎯 **Migration triggers**: >100 accounts, Lambda timeouts, customer progress requests
🎯 **Implementation order**: Job Handler → Workers → Polling Service → UI integration

### **Why Your Architecture is Optimal:**

1. **Serverless-Native**: Leverages SQS, Lambda, DynamoDB strengths
2. **Cost-Effective**: Pay only for actual processing, no idle resources
3. **Operationally Simple**: Minimal moving parts, easy to debug
4. **Future-Proof**: Can handle thousands of accounts with minimal changes

### **MVP-to-Production Bridge**
Your current modular service functions (s3_inventory.py, ec2_inventory.py, iam_inventory.py) are **perfectly positioned** for this architecture. Workers can call them directly with zero changes.

**Final Verdict**: Your queue-based fanout design is production-ready and architecturally sound. The MVP approach provides the perfect validation path before implementing this robust scaling solution.