---
inclusion: auto
---

# Git Branching Workflow

## Branch Strategy

This project follows a two-branch workflow:

- **main**: Production-ready code that's deployed to Streamlit Cloud
- **development**: Active development branch for new features and fixes

## Workflow Rules

1. **Never commit directly to main** once the project is stable and deployed
2. **Always create or switch to development branch** before making changes
3. **Test thoroughly on development** before merging to main
4. **Merge to main only when features are complete and tested**

## Commands

### Starting New Work
```bash
# Switch to development (or create if it doesn't exist)
git checkout development || git checkout -b development

# Make your changes, then commit
git add .
git commit -m "Description of changes"
```

### Merging to Main
```bash
# Switch to main
git checkout main

# Merge development
git merge development

# Push to GitHub (triggers Streamlit Cloud deployment)
git push origin main

# Switch back to development for next work
git checkout development
```

### Syncing Development with Main
```bash
# If main has changes from other sources
git checkout development
git merge main
```

## Why This Workflow?

- **Stability**: Main branch always has working, tested code
- **Safety**: Streamlit Cloud deploys from main, so users always see stable version
- **Flexibility**: Can experiment freely on development without breaking production
- **Rollback**: Easy to revert to last working version if needed

## When to Use Each Branch

**Use development for:**
- New features
- Bug fixes
- UI improvements
- Experimental changes
- Refactoring

**Use main for:**
- Deploying to production (Streamlit Cloud)
- Creating releases
- Hotfixes (only in emergencies)
