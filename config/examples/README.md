# Configuration Examples

This directory contains example configuration files for the Thai Tokenizer project.

## Files

### `.env.existing.example`
Example environment configuration for connecting to an existing MeiliSearch instance. This file demonstrates how to configure the Thai Tokenizer to work with a pre-existing MeiliSearch server.

## Usage

1. Copy the example file you need:
   ```bash
   cp config/examples/.env.existing.example .env
   ```

2. Edit the copied file with your actual configuration values:
   - Update MeiliSearch URL and API key
   - Adjust Thai Tokenizer settings as needed
   - Configure API settings for your environment

3. Never commit actual configuration files with real credentials to version control.

## Security Note

These are example files only. Always:
- Use environment variables for sensitive data
- Keep actual configuration files out of version control
- Use different credentials for different environments (dev, staging, production)