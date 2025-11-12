# Logging Guide

## Overview

The qrie codebase uses a centralized logging utility (`common.logger`) that provides three log levels: DEBUG, INFO, and ERROR.

## Usage

```python
from common.logger import debug, info, error

# Debug messages - only shown when DEBUG=true
debug("Detailed diagnostic information")
debug(f"Processing resource: {resource_arn}")

# Info messages - always shown
info("Operation started")
info(f"Successfully processed {count} items")

# Error messages - always shown
error("Something went wrong")
error(f"Failed to process item: {e}\n{traceback.format_exc()}")
```

## Log Levels

### DEBUG
- **Purpose**: Detailed diagnostic information for troubleshooting
- **When to use**: Resource processing details, evaluation results, config comparisons
- **Visibility**: Only shown when `DEBUG=true` environment variable is set
- **Examples**:
  - `debug(f"Skipping stale event for {resource_arn}")`
  - `debug(f"Evaluated {arn} against {policy_id}: compliant={result['compliant']}")`

### INFO
- **Purpose**: General operational messages and important state changes
- **When to use**: API requests, policy operations, inventory updates
- **Visibility**: Always shown
- **Examples**:
  - `info(f"[{request_id}] {method} {path}")`
  - `info(f"Config changed for {resource_arn}, updating inventory")`
  - `info(f"Successfully launched policy {policy_id}")`

### ERROR
- **Purpose**: Error conditions and exceptions
- **When to use**: Exception handlers, validation failures, operation failures
- **Visibility**: Always shown
- **Examples**:
  - `error(f"Error processing record: {e}\n{traceback.format_exc()}")`
  - `error(f"Policy {policy_id} not found")`

## Environment Variables

### DEBUG
Controls whether DEBUG level logs are shown.

**Values**:
- `true`, `1`, `yes` - Enable DEBUG logging
- `false`, `0`, `no`, or unset - Disable DEBUG logging (default)

**Setting in Lambda**:
```bash
# Via CDK/CloudFormation
Environment:
  Variables:
    DEBUG: "true"

# Via AWS CLI
aws lambda update-function-configuration \
  --function-name QrieEventHandler \
  --environment Variables={DEBUG=true}
```

## Log Format

All logs include timestamp and level:
```
[2025-01-15 10:30:45.123] INFO: [abc123-def456] GET /findings
[2025-01-15 10:30:45.456] DEBUG: Processing event: {...}
[2025-01-15 10:30:46.789] ERROR: Error processing record: ValueError
```

## Best Practices

1. **Use appropriate levels**:
   - DEBUG for verbose details
   - INFO for important operations
   - ERROR for failures

2. **Include context**:
   ```python
   # Good
   info(f"Launching policy {policy_id} with severity={severity}")
   
   # Bad
   info("Launching policy")
   ```

3. **Always include stack traces for errors**:
   ```python
   except Exception as e:
       error(f"Operation failed: {e}\n{traceback.format_exc()}")
   ```

4. **Use request IDs for correlation**:
   ```python
   info(f"[{request_id}] {method} {path}")
   error(f"[{request_id}] Error in handler: {e}")
   ```

5. **Don't log sensitive data**:
   - Avoid logging credentials, tokens, or PII
   - Redact sensitive fields when logging configurations

## Monitoring Logs

### CloudWatch Logs
```bash
# View logs with color coding
./tools/debug/monitor-lambda-logs.sh us-east-1 qop

# Search for specific request
aws logs filter-log-events \
  --log-group-name /aws/lambda/QrieApiHandler \
  --filter-pattern "[abc123-def456]"

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/QrieApiHandler \
  --filter-pattern "ERROR"
```

### Log Patterns
- Request correlation: `[abc123-def456]`
- Policy operations: `Launch policy request: policy_id=`
- Errors: `ERROR:`
- Debug info: `DEBUG:`

## Migration from print()

**Before**:
```python
debug = os.getenv('DEBUG', False)

if debug:
    print(f"Debug message")
print(f"Info message")
print(f"Error: {e}")
```

**After**:
```python
from common.logger import debug, info, error

debug("Debug message")
info("Info message")
error(f"Error: {e}")
```
