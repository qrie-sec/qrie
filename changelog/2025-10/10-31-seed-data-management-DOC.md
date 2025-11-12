# Quick Reference: Data Management

**Date:** October 31, 2025  
**Type:** Reference Guide

## Commands

### Seed Test Data
```bash
# Add test data (clears existing first)
./qop.py --seed-data --region us-east-1 --profile qop
```

### Purge All Data
```bash
# Delete all data (requires confirmation)
./qop.py --purge-data --region us-east-1 --profile qop

# Delete all data (skip confirmation - DANGEROUS!)
./qop.py --purge-data --region us-east-1 --profile qop --skip-confirm
```

## What Gets Purged

| Table | Description | Items |
|-------|-------------|-------|
| `qrie_accounts` | AWS accounts | Account IDs, OUs |
| `qrie_resources` | Cloud resources | S3, EC2, RDS, IAM, etc. |
| `qrie_policies` | Launched policies | Active/suspended policies |
| `qrie_findings` | Security findings | ACTIVE/RESOLVED findings |
| `qrie_summary` | Cached summaries | Dashboard, findings, inventory caches |

## Common Workflows

### Fresh Start
```bash
./qop.py --purge-data --region us-east-1 --profile qop
./qop.py --seed-data --region us-east-1 --profile qop
```

### Pre-Demo
```bash
./qop.py --purge-data --region us-east-1 --profile qop --skip-confirm
./qop.py --seed-data --region us-east-1 --profile qop --skip-confirm
```

### CI/CD Testing
```bash
./qop.py --purge-data --region us-east-1 --profile ci --skip-confirm
./qop.py --seed-data --region us-east-1 --profile ci --skip-confirm
./qop.py --test-api --region us-east-1 --profile ci
```

## Direct Script Usage

### Seed Data
```bash
cd tools/data
python seed_data.py --region us-east-1
python seed_data.py --clear --region us-east-1  # Clear first
```

### Purge Data
```bash
cd tools/data
python seed_data.py --purge --region us-east-1
python seed_data.py --purge --region us-east-1 --skip-confirm  # No confirmation
```

## Safety Tips

⚠️ **ALWAYS**:
- Verify region: `--region us-east-1`
- Verify profile: `--profile qop`
- Check environment before purging
- Read confirmation prompts carefully

❌ **NEVER**:
- Purge production without approval
- Use `--skip-confirm` interactively
- Assume data can be recovered
- Purge without checking environment

## Troubleshooting

### "Table not found"
- Deploy core infrastructure first: `./qop.py --deploy-core`

### "Access denied"
- Check AWS profile: `aws sts get-caller-identity --profile qop`
- Verify IAM permissions

### "Region required"
- Add `--region us-east-1` to command

## Help

```bash
# Show all commands
./qop.py -h

# Show seed_data.py options
python tools/data/seed_data.py -h
```
