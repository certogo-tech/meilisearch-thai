# Root Folder Organization Summary

This document describes the organization of the Thai Tokenizer project root folder.

## Directory Structure

```
thai-tokenizer/
├── src/                          # Source code
├── tests/                        # Test files
├── deployment/                   # Docker and deployment configs
├── docs/                         # Documentation
│   └── production/              # Production-specific docs
├── scripts/                      # Operational scripts
│   ├── deployment/              # Deployment scripts
│   ├── testing/                 # Testing scripts
│   └── maintenance/             # Maintenance scripts
├── data/                         # Data files (dictionaries, etc.)
├── backups/                      # Backup files
│   └── env/                     # Environment file backups
├── config/                       # Configuration files
├── logs/                         # Log files
└── ssl/                          # SSL certificates
```

## Key Files in Root

### Essential Files
- `README.md` - Main project documentation
- `pyproject.toml` - Python project configuration
- `requirements.txt` - Python dependencies
- `.env.production` - Production environment configuration
- `.gitignore` - Git ignore patterns
- `Makefile` - Build and development commands

### Main Scripts
- `deploy.sh` - Main deployment script (entry point)

### Development Files
- `.dockerignore` - Docker ignore patterns
- `QUICK_START.md` - Quick start guide

## Usage

### Deploy to Production
```bash
./deploy.sh production
```

### Test the Service
```bash
./deploy.sh test
```

### Debug Issues
```bash
./deploy.sh debug
```

### Validate Configuration
```bash
./deploy.sh validate
```

## Backup Policy

- Environment file backups are stored in `backups/env/`
- Backups are automatically created before configuration changes
- Backup files follow the pattern: `.env.production.backup.YYYYMMDD_HHMMSS`

## Script Organization

All operational scripts have been moved to the `scripts/` directory:
- **Deployment scripts**: For deploying and managing the service
- **Testing scripts**: For testing functionality and health
- **Maintenance scripts**: For debugging and maintenance tasks

This organization makes it easier to:
1. Find the right script for the task
2. Maintain and update scripts
3. Understand the project structure
4. Onboard new team members
