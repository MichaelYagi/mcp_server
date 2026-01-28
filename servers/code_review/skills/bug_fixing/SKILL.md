---
name: python_bug_fixing_and_code_generation
description: >
  Automatically detect and fix common Python bugs and anti-patterns using AST
  analysis. Generate new code from natural language descriptions. Identifies 
  mutable defaults, bare except clauses, identity comparisons, and unused imports.
  Creates backups before applying fixes.
tags:
  - code
  - python
  - debugging
  - fixing
  - analysis
  - quality
  - generation
  - ai-assisted
tools:
  - analyze_code_file
  - fix_code_file
  - suggest_improvements
  - generate_code
---

# Python Bug Fixing & Code Generation Skill

## 🎯 Overview

This skill provides two main capabilities:
1. **Bug Detection & Fixing**: Analyze Python code for common bugs and anti-patterns
2. **Code Generation**: Create new code from natural language descriptions

---

## 📋 Part 1: Bug Detection & Fixing

### When to Use

Use this when the user asks:
- "analyze my code for bugs"
- "check this Python file"
- "fix bugs in my script"
- "review my code quality"
- "find issues in this file"
- "what's wrong with this code"

### Workflow

#### STEP 1: Always Analyze First

**NEVER fix without analyzing first!**

```
analyze_code_file("path/to/file.py")
```

Returns issues with:
- `severity`: error/warning/info
- `line`: Line number
- `message`: What's wrong
- `suggestion`: How to fix
- `fix_type`: (if auto-fixable)

#### STEP 2: Review with User

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

#### STEP 3: Fix (if User Approves)

```
fix_code_file("path/to/file.py", backup=True)
```

**ALWAYS create backup unless user explicitly says no.**

### Python Issues Detected

#### 🔴 ERRORS (Critical - Must Fix)

**Mutable Default Arguments**

```python
# ❌ DANGEROUS
def add_item(items=[]):
    items.append(1)
    return items

# ✅ CORRECT
def add_item(items=None):
    if items is None:
        items = []
    items.append(1)
    return items
```

**Identity Comparison with Literals**

```python
# ❌ WRONG
if x is 5:
    pass

# ✅ CORRECT  
if x == 5:
    pass

# ✅ WHEN TO USE is:
if x is None:  # Checking singleton
if x is True:  # Checking boolean
```

#### ⚠️  WARNINGS (Should Fix)

**Bare Except**

```python
# ❌ TOO BROAD
try:
    risky_operation()
except:  # Catches EVERYTHING
    pass

# ✅ CORRECT
try:
    risky_operation()
except Exception as e:
    logger.error(f"Failed: {e}")
```

#### ℹ️  INFO (Nice to Have)

**Unused Imports**

```python
# ❌ CLUTTER
import json  # Not used
import sys

sys.exit(0)

# ✅ CLEAN
import sys

sys.exit(0)
```

---

## 🤖 Part 2: Code Generation

### When to Use

User asks to:
- "**use the generate_code tool**"
- "generate code for..."
- "create a function that..."
- "write a class that..."
- "make an API endpoint for..."
- "build a component that..."
- "calculate X recursively"
- "implement Y algorithm"

### Tool: `generate_code(description, language, style, ...)`

Generate new code from natural language descriptions.

### Workflow

#### STEP 1: Get Clear Requirements

Ask clarifying questions:
- What are the inputs?
- What should it return?
- Any edge cases to handle?
- Any specific frameworks?
- What language/style?

#### STEP 2: Generate Code

```python
generate_code(
    description="Calculate factorial recursively with error handling",
    language="python",
    style="function",
    include_tests=True,
    include_docstrings=True
)
```

**Parameters:**
- `description` (required): Natural language description of what to generate
- `language` (optional): "python", "javascript", "typescript", "rust", "go"
- `style` (optional): "function", "class", "module", "script"
- `include_tests` (optional): Generate unit tests
- `include_docstrings` (optional): Add documentation
- `framework` (optional): "fastapi", "flask", "react", "express"

#### STEP 3: Review and Refine

Show generated code and ask:
- Does this match what you wanted?
- Any changes needed?
- Should I save this to a file?
- Want me to add tests?

### Examples

#### Example 1: Simple Function

```
User: "Use the generate_code tool to calculate factorial recursively"

Agent: generate_code(
    description="Calculate factorial of a number recursively. 
                 Handle edge cases: n=0 returns 1, negative n raises ValueError",
    language="python",
    style="function",
    include_docstrings=True
)

Generated:
```python
def factorial(n: int) -> int:
    """
    Calculate factorial recursively.
    
    Args:
        n: Non-negative integer
        
    Returns:
        Factorial of n
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0:
        return 1
    return n * factorial(n - 1)
```

Agent: "Here's the recursive factorial function. Would you like me to:
1. Add unit tests?
2. Save to a file?
3. Add iterative version for comparison?"
```

#### Example 2: Email Validator

```
User: "create a function to validate email addresses"

Agent: "I'll create an email validator. Should it:
- Return True/False or raise exceptions?
- Allow plus signs in the local part?
- Require specific domains?"

User: "return true/false and allow plus signs"

Agent: generate_code(
    description="Validate email addresses. Returns True if valid, False otherwise.
                 Allows + sign in local part. Checks for @ symbol and domain with dot.",
    language="python",
    style="function",
    include_docstrings=True,
    include_tests=True
)

Generated:
```python
def validate_email(email: str) -> bool:
    """
    Validate an email address.
    
    Allows + sign in local part.
    Returns True if valid, False otherwise.
    
    Args:
        email: Email string to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    if '@' not in email:
        return False
    
    local, domain = email.split('@', 1)
    if not local or not domain:
        return False
    
    if '.' not in domain:
        return False
    
    return True


# Unit Tests
def test_validate_email():
    assert validate_email("user@example.com") == True
    assert validate_email("user+tag@example.com") == True
    assert validate_email("invalid") == False
    assert validate_email("@example.com") == False
    assert validate_email("user@") == False
```

Agent: "Here's the email validator with tests. Would you like me to:
1. Add more comprehensive validation (TLD checks, length limits)?
2. Save to a file?
3. Make any changes?"
```

#### Example 3: API Endpoint

```
User: "generate a FastAPI endpoint that creates a user"

Agent: "I'll create a FastAPI user creation endpoint. Should it:
- Use a database (SQLAlchemy, MongoDB)?
- Hash passwords?
- Return what on success?
- What fields should User have?"

User: "SQLAlchemy, hash passwords with bcrypt, return user ID"

Agent: generate_code(
    description="FastAPI POST endpoint that creates a new user.
                 Uses SQLAlchemy User model, hashes password with bcrypt.
                 Returns user_id on success, 400 on validation errors.",
    language="python",
    framework="fastapi",
    style="function",
    include_docstrings=True
)

Generated:
```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

@router.post("/users", status_code=201)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    
    Args:
        user: User creation data
        db: Database session
        
    Returns:
        dict: Created user ID
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    # Check if user exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    
    # Create user
    new_user = User(
        email=user.email,
        password_hash=hashed.decode(),
        name=user.name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"user_id": new_user.id}
```

Agent: "Here's the FastAPI endpoint. Should I also generate:
1. The SQLAlchemy User model?
2. Password validation (min length, complexity)?
3. Authentication/login endpoint?"
```

### Supported Languages & Styles

| Language | Styles | Frameworks |
|----------|--------|------------|
| Python | function, class, module, script | FastAPI, Flask, Django |
| JavaScript | function, class, module | Express, React (JSX) |
| TypeScript | function, class, module | Express, React (TSX) |
| Rust | function, struct, trait | Actix-web, Rocket |
| Go | function, struct, interface | Gin, Echo |

### Best Practices

1. **Get specifics** - Don't generate from vague descriptions
2. **Ask questions** - Clarify requirements before generating
3. **Show before saving** - Let user review first
4. **Offer tests** - Ask if they want unit tests included
5. **Ask about framework** - FastAPI vs Flask, React vs Vue, etc.
6. **Iterate** - Generated code is a starting point, refine based on feedback
7. **Explain choices** - Tell user why you structured code a certain way

### Common Patterns

**Pattern 1: "Use the X tool"**
```
User: "Use the generate_code tool to calculate fibonacci"
→ IMMEDIATELY call generate_code with clear description
```

**Pattern 2: Algorithm requests**
```
User: "Calculate factorial recursively"
→ Recognize this as code generation request
→ Call generate_code with algorithm details
```

**Pattern 3: Task-based**
```
User: "Create a function that validates phone numbers"
→ Ask clarifying questions
→ Call generate_code with requirements
```

**Pattern 4: Component/Class**
```
User: "Build a User class with authentication"
→ Ask about auth method (JWT, session, etc.)
→ Call generate_code with specifications
```

---

## 🔄 Combined Workflow Example

```
User: "Generate a function to parse CSV files, then analyze it for bugs"

Agent: [STEP 1: Generate]
generate_code(
    description="Parse CSV file into list of dicts. 
                 Handle missing columns, empty rows.",
    language="python",
    style="function",
    include_docstrings=True
)

Generated code shown to user...

User: "Looks good, save it as parser.py"

Agent: [Saves to parser.py]

Agent: [STEP 2: Analyze]
analyze_code_file("parser.py")

Found issues:
• Line 12: Bare except clause
• Line 45: Unused import 'sys'

Agent: "Found 2 issues. Should I fix them?"

User: "yes"

Agent: [STEP 3: Fix]
fix_code_file("parser.py", backup=True)

Agent: "✅ Fixed 2 issues. Backup saved as parser.py.backup"
```

---

## ⚠️ Important Notes

### For Bug Fixing:
- Always analyze before fixing
- Always create backups (unless user says no)
- Explain WHY something is a bug
- Get approval before modifying code

### For Code Generation:
- Ask clarifying questions
- Show generated code before saving
- Offer to add tests/docs
- Iterate based on feedback
- Explain your design choices

### Safety:
- Backups created automatically
- Validates syntax before saving
- Logs all changes
- Can be reverted using backup

---

## 🎓 Quick Reference

**Bug Fixing Commands:**
```
analyze_code_file("path/file.py")       # Check for issues
fix_code_file("path/file.py")           # Auto-fix issues
suggest_improvements("path/file.py")     # Get recommendations
```

**Code Generation Commands:**
```
generate_code(
    description="...",    # What to build
    language="python",    # Programming language
    style="function",     # Code structure
    include_tests=True,   # Add unit tests
    framework="fastapi"   # Optional framework
)
```

**Triggers:**
- Bug fixing: "analyze", "fix", "check", "review" + "code"
- Code gen: "generate", "create", "write", "build" + code construct
- Explicit: "use the generate_code tool"