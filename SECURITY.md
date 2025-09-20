# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please send an email to [Please fill in your security email address here]. All security vulnerabilities will be promptly addressed.

## Security Configuration

### API Keys

**IMPORTANT**: Never commit API keys to version control.

1. Replace placeholder API keys in `main.py`:

   ```python
   ZHIPU_API_KEY = "your_zhipu_api_key_here"  # Replace with your actual API key
   ```

2. Use environment variables for production:
   ```bash
   export ZHIPU_API_KEY="your_actual_api_key"
   ```

### Database Security

1. **Change default passwords**: The default Neo4j password is `passcode123`. Change it immediately after first login.

2. **Use environment variables**:

   ```bash
   export NEO4J_PASSWORD="your_secure_password"
   ```

3. **Network security**: In production, ensure Neo4j is not exposed to the internet without proper authentication.

### Docker Security

1. **Change default credentials** in `neo4j-dump-deploy/docker-compose.yml`
2. **Use secrets management** for production deployments
3. **Regular updates**: Keep Docker images updated

### File Permissions

Ensure proper file permissions:

```bash
chmod 600 .env  # If using .env file
chmod 755 scripts/*.sh
```

## Best Practices

1. **Regular Updates**: Keep all dependencies updated
2. **Input Validation**: The system validates C++ code execution
3. **Resource Limits**: Code execution has time and memory limits
4. **Sandboxing**: Code runs in isolated processes

## Known Security Considerations

1. **Code Execution**: This system executes user-provided C++ code. Use only in trusted environments.
2. **API Costs**: Protect your API keys to prevent unauthorized usage costs.
3. **Database Access**: Neo4j contains algorithm data; secure access appropriately.

## Contact

For security concerns, please contact: [Please fill in your security contact here]
