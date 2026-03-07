# Security Guidelines

## API Key Management

### ✅ DO:
- Store API keys as system environment variables
- Use `.env.example` as a template (without actual keys)
- Add `.env` to `.gitignore`
- Rotate API keys regularly
- Use separate API keys for development and production

### ❌ DON'T:
- Commit API keys to Git
- Share API keys in chat, email, or documentation
- Hardcode API keys in source code
- Use the same API key across multiple projects

## Setting Up API Keys

### Windows (PowerShell)
```powershell
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'your-key-here', 'User')
```

### macOS/Linux (Bash/Zsh)
```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY='your-key-here'
source ~/.bashrc
```

### Verify
```bash
python -c "import os; print('✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Not set')"
```

## Before Committing to Git

Run this checklist:

```bash
# 1. Check for API keys in files
git grep -i "sk-proj-" || echo "✓ No API keys found"
git grep -i "api.key" || echo "✓ No API keys found"

# 2. Verify .env is ignored
git check-ignore .env && echo "✓ .env is ignored" || echo "⚠️ .env is NOT ignored!"

# 3. Check what will be committed
git status
git diff --cached
```

## If You Accidentally Commit an API Key

1. **Immediately revoke the key** at https://platform.openai.com/api-keys
2. Generate a new API key
3. Remove the key from Git history:
   ```bash
   # Use git-filter-repo or BFG Repo-Cleaner
   git filter-repo --replace-text <(echo "your-old-key==>REDACTED")
   ```
4. Force push (if already pushed to remote):
   ```bash
   git push --force
   ```

## Deployment Security

### Streamlit Cloud
- Use Streamlit Secrets management
- Add secrets in app settings, not in code

### Heroku/Railway/Render
- Use platform environment variables
- Never commit `.env` files

### Docker
- Use Docker secrets or environment variables
- Don't bake secrets into images

## Additional Security Measures

1. **Rate Limiting**: Monitor API usage to detect unauthorized access
2. **IP Restrictions**: Configure OpenAI API to only accept requests from known IPs
3. **Logging**: Monitor logs for suspicious activity
4. **Regular Audits**: Review API key usage monthly

## Reporting Security Issues

If you discover a security vulnerability, please email [your-email] instead of using the issue tracker.
