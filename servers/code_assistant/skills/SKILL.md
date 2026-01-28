---
name: python_bug_fixing
description: >
  Automatically detect and fix common Python bugs and anti-patterns using AST
  analysis. Identifies mutable defaults, bare except clauses, identity comparisons,
  and unused imports. Creates backups before applying fixes. Also generates new
  code from natural language descriptions.
tags:
  - code
  - python
  - debugging
  - fixing
  - analysis
  - quality
  - generation
tools:
  - analyze_code_file
  - fix_code_file
  - suggest_improvements
  - generate_code
---

# Python Bug Fixing Skill

## When to Use

Use this skill when the user asks for:

- "analyze my code for bugs"
- "check this Python file"
- "fix bugs in my script"
- "review my code quality"
- "find issues in this file"
- "what's wrong with this code"

## Workflow

### STEP 1: Always Analyze First

**NEVER fix without analyzing first!**

```
analyze_code_file("path/to/file.py")
```

This returns issues with:
- `severity`: error/warning/info
- `line`: Line number
- `message`: What's wrong
- `suggestion`: How to fix
- `fix_type`: (if auto-fixable)

### STEP 2: Review with User

Present findings clearly grouped by severity:

```
I found 3 issues in server.py:

❌ ERRORS (must fix):
• Line 145: Mutable default argument
  Function process() has items=[] - this is shared between calls!
  Fix: Use items=None, then if items is None: items = []

⚠️  WARNINGS (should fix):
• Line 203: Bare except catches all exceptions
  This catches SystemExit and KeyboardInterrupt
  Fix: Use except Exception as e:

ℹ️  INFO (optional):
• Line 89: Unused import 'json'
  Can be safely removed

Would you like me to fix these?
```

### STEP 3: Fix (if User Approves)

```
fix_code_file("path/to/file.py", backup=True)
```

**ALWAYS create backup unless user explicitly says no.**

Returns:
- `fixes_applied`: Count
- `details[]`: What was fixed
- `backup_path`: Backup location
- `formatted`: Whether code was formatted

## Python Issues Detected

### 🔴 ERRORS (Critical - Must Fix)

#### Mutable Default Arguments

**Problem:**
```python
def add_item(items=[]):  # ❌ DANGEROUS
    items.append(1)
    return items
```

**Why It's Bad:**
The empty list `[]` is created ONCE when the function is defined, not each time it's called. All calls share the same list object.

**What Happens:**
```python
>>> add_item()
[1]
>>> add_item()  # Expected [1], got [1, 1]
[1, 1]
>>> add_item()  # Expected [1], got [1, 1, 1]
[1, 1, 1]
```

**Fix:**
```python
def add_item(items=None):  # ✅ CORRECT
    if items is None:
        items = []
    items.append(1)
    return items
```

#### Identity Comparison with Literals

**Problem:**
```python
if x is 5:  # ❌ WRONG
    pass
```

**Why It's Bad:**
- `is` checks if two variables point to the SAME object in memory
- `==` checks if two variables have the SAME value
- Python caches small integers (-5 to 256), so `is 5` might work in testing but fail in production

**Fix:**
```python
if x == 5:  # ✅ CORRECT
    pass
```

**When to use `is`:**
- `if x is None:` ✅ (checking singleton)
- `if x is True:` ✅ (checking boolean singleton)
- `if x == 5:` ✅ (checking value)

### ⚠️  WARNINGS (Important - Should Fix)

#### Bare Except

**Problem:**
```python
try:
    risky_operation()
except:  # ❌ TOO BROAD
    pass
```

**Why It's Bad:**
Catches ALL exceptions including:
- `SystemExit` (from `sys.exit()`)
- `KeyboardInterrupt` (Ctrl+C)
- `GeneratorExit`

**Impact:**
- Can't stop program with Ctrl+C
- Hides critical system errors
- Makes debugging impossible

**Fix:**
```python
try:
    risky_operation()
except Exception as e:  # ✅ CORRECT
    logger.error(f"Operation failed: {e}")
    # Or handle specific exceptions:
    # except (ValueError, TypeError) as e:
```

### ℹ️  INFO (Nice to Have)

#### Unused Imports

**Problem:**
```python
import json  # Not used anywhere
import sys

sys.exit(0)
```

**Why It Matters:**
- Clutters code
- Increases import time
- Confuses readers

**Fix:**
Remove or comment out unused imports.

## Example Interaction

```
User: "analyze my api.py for bugs"

Agent: analyze_code_file("myapp/api.py")

Response shows:
{
  "total_issues": 3,
  "errors": 1,
  "warnings": 2,
  "issues": [
    {
      "severity": "error",
      "type": "MutableDefault",
      "line": 45,
      "message": "Function has mutable default argument",
      ...
    }
  ]
}

Agent presents to user:
"I found 3 issues in api.py:

❌ ERRORS:
• Line 45: Mutable default argument in process_data()
  This causes the same list to be shared between calls

⚠️  WARNINGS:  
• Line 78: Bare except clause
• Line 120: Identity comparison with literal

Would you like me to fix these?"

User: "yes fix them"

Agent: fix_code_file("myapp/api.py", backup=True)

Agent reports:
"✅ Fixed 3 issues:
• Line 45: Fixed mutable default
• Line 78: Changed to 'except Exception as e:'
• Line 120: Changed 'is' to '=='

📋 Backup saved: api.py.backup
✨ Code formatted with Black"
```

## Best Practices

1. **Always analyze before fixing** - Never fix blindly
2. **Always create backups** - Unless user explicitly says no
3. **Explain the why** - Don't just say "fixed bug", explain why it was a bug
4. **Get approval** - Present findings and wait for user confirmation
5. **Report results** - Show what was changed

## Language Support

- **Python**: Full AST analysis (deep bug detection)
- **JavaScript/TypeScript**: Linter integration (requires eslint)
- **Other languages**: Basic linter support if installed

## Safety Features

- Automatic backups before modifying
- Validates fixes don't break syntax
- Logs all changes
- Can be reverted using backup file

---

## Code Generation

### Tool: `generate_code(description, language, style, ...)`

Generate new code from natural language descriptions.

### When to Use

User asks to:
- "create a function that..."
- "generate code for..."
- "write a class that..."
- "make an API endpoint for..."
- "build a component that..."

### Workflow

**STEP 1: Get Clear Requirements**

Ask clarifying questions:
- What are the inputs?
- What should it return?
- Any edge cases to handle?
- Any specific frameworks?

**STEP 2: Generate Code**

```
generate_code(
    description="Calculate factorial recursively with error handling",
    language="python",
    style="function",
    include_tests=True,
    include_docstrings=True
)
```

**STEP 3: Review and Refine**

Show the generated code to the user and ask:
- Does this match what you wanted?
- Any changes needed?
- Should I save this to a file?

### Examples

```
User: "create a function to validate email addresses"

Agent: "I'll create an email validator. Should it:
- Return True/False or raise exceptions?
- Allow plus signs in the local part?
- Require specific domains?"

User: "return true/false and allow plus signs"

Agent: generate_code(
    description="Validate email addresses, returns True/False,
                 allows + in local part, checks for @ and domain",
    language="python",
    style="function",
    include_docstrings=True
)

Generated:
def validate_email(email: str) -> bool:
    \"\"\"
    Validate an email address.
    
    Allows + sign in local part.
    Returns True if valid, False otherwise.
    \"\"\"
    if '@' not in email:
        return False
    
    local, domain = email.split('@', 1)
    if not local or not domain:
        return False
    
    if '.' not in domain:
        return False
    
    return True

Agent: "Here's the email validator. Would you like me to:
1. Add unit tests?
2. Save to a file?
3. Make any changes?"
```

### Supported Languages

- **Python**: Functions, classes, modules, FastAPI/Flask endpoints
- **JavaScript**: Functions, classes, React components, Express routes
- **TypeScript**: Typed versions of JavaScript
- **Rust**: Functions, structs, traits (basic support)
- **Go**: Functions, structs, interfaces (basic support)

### Best Practices

1. **Get specifics** - Don't generate from vague descriptions
2. **Show before saving** - Let user review first
3. **Offer tests** - Ask if they want unit tests
4. **Ask about framework** - FastAPI vs Flask, React vs Vue, etc.
5. **Iterate** - Generated code is a starting point, refine based on feedback