---
inclusion: auto
---

# Python Project Setup Standards

## Virtual Environment - CRITICAL RULE

**ALWAYS create a virtual environment BEFORE any other project setup steps.**

When starting any new Python project or when you see a requirements.txt file without a venv:

1. **First action**: Create venv using system Python (not from another venv)
   ```bash
   python -m venv venv
   ```

2. **Second action**: Add venv to .gitignore if not already present

3. **Third action**: Instruct user to activate venv:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Only then**: Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

## Why This Matters

- Prevents polluting the user's main Python environment
- Ensures project isolation and reproducibility
- Follows Python best practices
- Makes dependency management clean and predictable

## Detection

If you see any of these, check for venv first:
- requirements.txt file
- setup.py or pyproject.toml
- Python project structure (src/, tests/, etc.)
- User mentions "new project" or "setup"

## Never

- Never run `pip install` without confirming a venv is active
- Never assume packages should go in the system Python
- Never skip venv creation "to save time"
