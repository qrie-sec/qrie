# Debug Tools

## Monitor Lambda Logs

Real-time monitoring of Qrie Lambda function logs with color-coded output.

### Usage

```bash
./monitor-logs.sh [lambda-name] [region] [profile]
```

### Lambda Names

- **`api`** - API Handler (qrie_api_handler)
- **`event`** - Event Processor (qrie_event_processor)
- **`scan`** - Policy Scanner (qrie_policy_scanner)
- **`inventory`** - Inventory Generator (qrie_inventory_generator)
- **`all`** - Show all available Lambda functions

### Examples

```bash
# Monitor event processor (for E2E testing)
./monitor-logs.sh event us-east-1 qop

# Monitor API handler (default)
./monitor-logs.sh api

# Monitor policy scanner
./monitor-logs.sh scan us-east-1 qop

# Show all available Lambdas
./monitor-logs.sh all
```

### Color Coding

- **Gray** - DEBUG messages
- **Light Gray** - INFO messages
- **Yellow** - WARN messages
- **Red** - ERROR messages
- **Magenta** - FATAL messages

### Backward Compatibility

The old `monitor-lambda-logs.sh` script still works and defaults to monitoring the API handler:

```bash
./monitor-lambda-logs.sh [region] [profile]
```

This is equivalent to:

```bash
./monitor-logs.sh api [region] [profile]
```
