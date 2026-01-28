---
name: code_assistant
description: >
  Automated code analysis, bug detection, fixing, and generation using AST analysis.
  Supports Python (deep analysis), JavaScript, TypeScript, Rust, and Go.
  Detects mutable defaults, bare except clauses, identity comparisons, unused imports.
  Generates code from natural language, creates tests, suggests improvements, and refactors.
tags:
  - code
  - python
  - javascript
  - typescript
  - debugging
  - fixing
  - analysis
  - generation
  - testing
  - refactoring
tools:
  - analyze_code_file
  - fix_code_file
  - suggest_improvements
  - explain_code
  - generate_tests
  - refactor_code
  - generate_code
  - list_skills
  - read_skill
---

# Code Assistant Skill

## 🎯 Overview

Complete code analysis, bug fixing, and generation toolkit powered by AST analysis and AI.

**Core Capabilities:**
1. **Bug Detection** - Find issues via deep AST analysis
2. **Auto-Fixing** - Automatically fix common bugs
3. **Code Generation** - Create code from natural language
4. **Testing** - Generate unit tests automatically
5. **Refactoring** - Modernize and optimize code
6. **Explanations** - Understand complex code

**Supported Languages:**
- **Python** - Deep AST analysis (mutable defaults, bare except, etc.)
- **JavaScript/TypeScript** - Linter integration
- **Rust** - Basic analysis
- **Go** - Basic analysis

---

## 📋 Part 1: Code Analysis

### When to Use

User asks to:
- "analyze my code for bugs"
- "check this Python file"
- "review my code"
- "find issues in X"
- "what's wrong with this code"

### Tool: `analyze_code_file`

```python
analyze_code_file(
    file_path="path/to/file.py",
    language="auto",           # or "python", "javascript", etc.
    deep_analysis=True         # Use AST for Python
)
```

**Returns:**
```json
{
  "language": "python",
  "total_issues": 3,
  "errors": 1,
  "warnings": 2,
  "fixable": 2,
  "issues": [
    {
      "severity": "error",
      "type": "MutableDefault",
      "line": 45,
      "message": "Function has mutable default argument",
      "suggestion": "Use items=None, then if items is None: items = []",
      "fix": "auto-fixable"
    }
  ]
}
```

### Workflow

**STEP 1: Analyze**
```
User: "analyze my server.py for bugs"

Agent: analyze_code_file("server.py")

Result shows 3 issues...
```

**STEP 2: Present Findings**
```
Agent: "I found 3 issues in server.py:

❌ ERRORS (must fix):
• Line 45: Mutable default argument
  Function process() has items=[] - shared between calls!
  Fix: Use items=None, then if items is None: items = []

⚠️  WARNINGS (should fix):
• Line 78: Bare except catches ALL exceptions
  This catches SystemExit and KeyboardInterrupt
  Fix: Use except Exception as e:

• Line 120: Identity comparison with literal
  Using 'is' instead of '==' for value comparison
  Fix: Change to x == 5

2 of these can be auto-fixed. Would you like me to fix them?"
```

**STEP 3: Fix (if approved)**
```
User: "yes fix them"

Agent: fix_code_file("server.py", backup=True)
```

### Issues Detected

#### 🔴 ERRORS (Critical)

**Mutable Default Arguments**
```python
# ❌ DANGEROUS - shared between calls
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
# ❌ WRONG - checks object identity
if x is 5:
    pass

# ✅ CORRECT - checks value equality
if x == 5:
    pass

# ✅ USE is FOR SINGLETONS
if x is None:
if x is True:
```

#### ⚠️  WARNINGS (Important)

**Bare Except**
```python
# ❌ TOO BROAD - catches SystemExit, KeyboardInterrupt
try:
    risky()
except:
    pass

# ✅ CORRECT
try:
    risky()
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

## 🔧 Part 2: Auto-Fixing

### Tool: `fix_code_file`

```python
fix_code_file(
    file_path="buggy.py",
    auto_fix=True,        # Apply fixes (False = just show)
    backup=True,          # Create backup (RECOMMENDED)
    dry_run=False         # Preview without applying
)
```

**Returns:**
```json
{
  "fixes_applied": 2,
  "details": [
    "Line 45: Fixed mutable default argument",
    "Line 78: Changed bare except to 'except Exception'"
  ],
  "backup_path": "buggy.py.backup",
  "formatted": true
}
```

### Safety Features

- ✅ **Automatic backups** by default
- ✅ **Validates syntax** after fixing
- ✅ **Logs all changes**
- ✅ **Dry-run mode** to preview
- ✅ **Can be reverted** using backup

### Workflow

```
User: "fix the bugs in api.py"

Agent: "Let me analyze first..."
analyze_code_file("api.py")

Agent: "Found 3 fixable issues. Creating backup and fixing..."
fix_code_file("api.py", backup=True)

Agent: "✅ Fixed 3 issues:
• Line 45: Fixed mutable default
• Line 78: Changed to 'except Exception as e:'
• Line 120: Changed 'is' to '=='

📋 Backup saved: api.py.backup
✨ Code formatted with Black"
```

---

## 💡 Part 3: Suggestions & Improvements

### Tool: `suggest_improvements`

```python
suggest_improvements(
    file_path="api.py",
    context="REST API server",    # What you're building
    focus="all"                   # or "performance", "security", "readability"
)
```

**Returns:**
```json
{
  "suggestions": [
    {
      "type": "best_practice",
      "message": "Use logging instead of print statements",
      "reason": "Logging provides better control and production debugging",
      "suggestion": "Replace print() with logger.info()",
      "priority": "medium"
    },
    {
      "type": "security",
      "message": "SQL query vulnerable to injection",
      "reason": "String concatenation creates SQL injection risk",
      "suggestion": "Use parameterized queries",
      "priority": "high"
    }
  ],
  "language": "python",
  "focus_area": "all"
}
```

### Types of Suggestions

- **Best Practices** - Logging, type hints, error handling
- **Performance** - List comprehensions, caching, optimization
- **Security** - SQL injection, XSS, hardcoded secrets
- **Documentation** - Missing docstrings, unclear names
- **Organization** - Function length, complexity, modularity

### Example

```
User: "suggest improvements for my FastAPI server"

Agent: suggest_improvements("server.py", context="FastAPI REST API", focus="all")

Agent: "I have 5 suggestions:

🔴 HIGH PRIORITY (Security):
• Line 67: SQL query vulnerable to injection
  Use parameterized queries instead of f-strings

🟡 MEDIUM PRIORITY (Best Practice):
• Line 23: Using print instead of logging
  Replace with logger.info() for production
  
• Missing type hints on function parameters
  Add type hints for better IDE support

🟢 LOW PRIORITY (Performance):
• Line 145: List comprehension would be faster
• Consider caching database queries

Would you like me to show examples of how to implement these?"
```

---

## 📖 Part 4: Code Explanation

### Tool: `explain_code`

```python
explain_code(
    file_path="algorithm.py",
    line_start=45,              # Optional: specific section
    line_end=67,                # Optional: specific section
    detail_level="medium"       # "brief", "medium", or "detailed"
)
```

**Returns:**
```json
{
  "explanation": "This function implements a binary search...",
  "key_concepts": ["recursion", "divide-and-conquer", "O(log n)"],
  "complexity": "logarithmic",
  "dependencies": ["typing"]
}
```

### Use Cases

- Understanding unfamiliar code
- Onboarding new developers
- Code review explanations
- Documentation generation

### Example

```
User: "explain what this code does" [uploads algorithm.py]

Agent: explain_code("algorithm.py", detail_level="detailed")

Agent: "This code implements a binary search algorithm using recursion.

**What it does:**
Searches for a target value in a sorted array by repeatedly dividing 
the search space in half.

**Key concepts:**
- Recursion: Function calls itself
- Divide-and-conquer: Splits problem into smaller pieces
- Base case: Returns when array is empty or target found

**Complexity:** O(log n) - very efficient for large datasets

**How it works:**
1. Finds middle element
2. If target equals middle, return index
3. If target < middle, search left half
4. If target > middle, search right half
5. Repeat until found or array exhausted

**Dependencies:** Uses typing module for type hints"
```

---

## 🧪 Part 5: Test Generation

### Tool: `generate_tests`

```python
generate_tests(
    file_path="utils.py",
    test_framework="auto",        # or "pytest", "unittest", "jest"
    coverage_target="functions"   # or "classes", "all"
)
```

**Returns:**
```json
{
  "test_file_path": "test_utils.py",
  "test_code": "import pytest...",
  "functions_covered": ["validate_email", "parse_date"],
  "framework_used": "pytest",
  "coverage_estimate": 85
}
```

### Features

- Analyzes function signatures
- Creates common scenarios
- Includes edge cases
- Follows framework conventions
- Generates fixtures and mocks

### Example

```
User: "generate tests for my email validator"

Agent: generate_tests("validator.py", test_framework="pytest")

Agent: "Generated comprehensive test suite:

```python
import pytest
from validator import validate_email

def test_valid_email():
    assert validate_email("user@example.com") == True
    
def test_valid_with_plus():
    assert validate_email("user+tag@example.com") == True
    
def test_missing_at_symbol():
    assert validate_email("invalid.com") == False
    
def test_missing_domain():
    assert validate_email("user@") == False
    
def test_missing_local_part():
    assert validate_email("@example.com") == False
    
def test_no_domain_dot():
    assert validate_email("user@localhost") == False
```

Coverage: ~85% of function logic
Framework: pytest

Would you like me to save this to test_validator.py?"
```

---

## ♻️  Part 6: Refactoring

### Tool: `refactor_code`

```python
refactor_code(
    file_path="legacy.py",
    refactor_type="modernize",    # See types below
    target="",                    # Optional: specific target
    preview=True                  # Show preview first
)
```

**Refactor Types:**

| Type | Description | Example |
|------|-------------|---------|
| `extract_function` | Extract code into reusable function | DRY principle |
| `rename` | Improve variable/function names | Clarity |
| `simplify` | Reduce complexity | Nested ifs → early returns |
| `modernize` | Use latest syntax | f-strings, type hints |
| `optimize` | Performance improvements | List comp, generators |

**Returns:**
```json
{
  "refactor_type": "modernize",
  "changes": [
    "Converted % formatting to f-strings",
    "Added type hints to 5 functions",
    "Replaced dict.has_key() with 'in' operator"
  ],
  "preview": "def process(data: List[str]) -> int:...",
  "applied": false,
  "backup_path": null
}
```

### Examples

**Modernize Legacy Code**
```
User: "modernize my old Python 2 code"

Agent: refactor_code("legacy.py", "modernize", preview=True)

Agent: "Preview of changes:

BEFORE:
```python
def process(data):
    return "Result: %s" % data
```

AFTER:
```python
def process(data: List[str]) -> str:
    return f"Result: {data}"
```

Changes:
• Converted % formatting to f-strings
• Added type hints
• Used modern string formatting

Apply these changes?"

User: "yes"

Agent: refactor_code("legacy.py", "modernize", preview=False)
```

**Extract Function**
```
User: "this function is too long, extract lines 45-67"

Agent: refactor_code("app.py", "extract_function", target="lines:45-67")

Agent: "Extracted complex logic into new function:

```python
def validate_and_process_user(user_data: dict) -> bool:
    '''Validate user data and process registration'''
    # Lines 45-67 moved here
    ...
    return True

def register_user(request):
    user_data = request.json
    if validate_and_process_user(user_data):
        ...
```

This improves:
• Readability - Single responsibility
• Testability - Can unit test separately
• Reusability - Can use elsewhere

Apply changes?"
```

---

## ✨ Part 7: Code Generation

### Tool: `generate_code`

```python
generate_code(
    description="Calculate factorial recursively with error handling",
    language="python",         # "javascript", "typescript", "rust", "go"
    style="function",          # "class", "module", "script", "api_endpoint"
    include_tests=False,
    include_docstrings=True,
    framework="",              # "fastapi", "flask", "react", "express"
    output_file=""             # Optional: save to file
)
```

**Returns:**
```json
{
  "generated_code": "def factorial(n: int) -> int:...",
  "language": "python",
  "style": "function",
  "framework": null,
  "includes_tests": false,
  "includes_docs": true,
  "saved_to": null,
  "prompt_used": "Generate a Python function..."
}
```

### When to Use

User says:
- "**use the generate_code tool** to X"
- "generate code for X"
- "create a function that Y"
- "write a class that Z"
- "calculate X recursively"
- "implement Y algorithm"

### Description Tips

**Good descriptions are:**
- ✅ Specific about inputs/outputs
- ✅ Mention edge cases
- ✅ Include constraints
- ✅ Provide examples

**Examples:**

✅ **GOOD:**
```
"Create a function that validates email addresses. 
Returns True/False. Handles edge cases like missing @ or domain. 
Allows + in local part. Raises ValueError for None input."
```

❌ **BAD:**
```
"email validator"
```

### Workflow

**STEP 1: Get Requirements**
```
User: "Use the generate_code tool to calculate factorial recursively"

Agent: "I'll generate that. Should I:
1. Include error handling for negative numbers?
2. Add type hints?
3. Include unit tests?
4. Add memoization for performance?"
```

**STEP 2: Generate**
```
Agent: generate_code(
    description="Calculate factorial recursively. Handle n=0 returns 1, 
                 negative n raises ValueError. Include type hints and docstring.",
    language="python",
    style="function",
    include_tests=True,
    include_docstrings=True
)
```

**STEP 3: Review & Iterate**
```
Agent: "Generated factorial function with tests:

```python
def factorial(n: int) -> int:
    """
    Calculate factorial recursively.
    
    Args:
        n: Non-negative integer
        
    Returns:
        Factorial of n (n!)
        
    Raises:
        ValueError: If n is negative
        
    Examples:
        >>> factorial(5)
        120
        >>> factorial(0)
        1
    """
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0:
        return 1
    return n * factorial(n - 1)


# Unit Tests
import pytest

def test_factorial_positive():
    assert factorial(5) == 120
    assert factorial(3) == 6
    
def test_factorial_zero():
    assert factorial(0) == 1
    
def test_factorial_negative():
    with pytest.raises(ValueError):
        factorial(-1)
```

Would you like me to:
1. Add iterative version for comparison?
2. Add memoization (caching)?
3. Save to a file?
4. Make any changes?"
```

### Examples by Style

#### Function
```python
generate_code(
    "Validate phone number in (XXX) XXX-XXXX format",
    language="python",
    style="function"
)
```

#### Class
```python
generate_code(
    "User authentication manager with login, logout, password hashing",
    language="python",
    style="class",
    include_tests=True
)
```

#### API Endpoint
```python
generate_code(
    "FastAPI POST endpoint to create user with email, password. 
     Hash password with bcrypt, return user_id",
    language="python",
    style="api_endpoint",
    framework="fastapi"
)
```

#### React Component
```python
generate_code(
    "Counter component with increment/decrement buttons",
    language="javascript",
    style="module",
    framework="react"
)
```

---

## 📚 Complete Workflow Examples

### Example 1: Fix Bugs Pipeline

```
User: "analyze api.py and fix any bugs"

Agent: 
STEP 1: analyze_code_file("api.py")

Found 4 issues:
- 2 errors (fixable)
- 2 warnings

STEP 2: Present findings and get approval

Agent: "Found 4 issues, 2 are auto-fixable. Fix them?"

User: "yes"

STEP 3: fix_code_file("api.py", backup=True)

Agent: "✅ Fixed 2 issues, backup saved"
```

### Example 2: Generate & Test Pipeline

```
User: "Generate an email validator and create tests for it"

Agent:
STEP 1: generate_code(
    "Email validator with comprehensive checks",
    style="function",
    include_tests=False  # We'll generate separately
)

STEP 2: Save generated code
Agent: "Saved to validator.py"

STEP 3: generate_tests("validator.py")

Agent: "Generated 8 test cases covering edge cases"

STEP 4: analyze_code_file("validator.py")

Agent: "Code looks good! No issues found."
```

### Example 3: Legacy Code Modernization

```
User: "Modernize my old Python 2 code and fix any bugs"

Agent:
STEP 1: analyze_code_file("legacy.py")

Agent: "Found 12 issues including:
- Outdated string formatting
- Missing type hints
- Bare except clauses"

STEP 2: refactor_code("legacy.py", "modernize", preview=True)

Agent: "Preview shows updates to f-strings, type hints, etc."

User: "looks good"

STEP 3: refactor_code("legacy.py", "modernize", preview=False)

Agent: "✅ Modernized code"

STEP 4: fix_code_file("legacy.py", backup=True)

Agent: "✅ Fixed remaining bugs"

STEP 5: generate_tests("legacy.py")

Agent: "✅ Generated test suite"
```

---

## 🎓 Best Practices

### For Analysis:
1. ✅ Always analyze before fixing
2. ✅ Present findings grouped by severity
3. ✅ Explain WHY something is wrong
4. ✅ Get user approval before modifying

### For Fixing:
1. ✅ Always create backups (unless user says no)
2. ✅ Validate syntax after fixes
3. ✅ Show what was changed
4. ✅ Keep original for reference

### For Generation:
1. ✅ Ask clarifying questions first
2. ✅ Be specific in descriptions
3. ✅ Show generated code before saving
4. ✅ Offer tests and improvements
5. ✅ Iterate based on feedback

### For Refactoring:
1. ✅ Always preview first (default)
2. ✅ Explain what will change and why
3. ✅ Get approval before applying
4. ✅ Create backup when applying

---

## 🛠️  Tool Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `analyze_code_file` | Find bugs | `file_path`, `deep_analysis` |
| `fix_code_file` | Auto-fix bugs | `file_path`, `backup`, `dry_run` |
| `suggest_improvements` | Get recommendations | `file_path`, `focus` |
| `explain_code` | Understand code | `file_path`, `detail_level` |
| `generate_tests` | Create unit tests | `file_path`, `test_framework` |
| `refactor_code` | Modernize/optimize | `refactor_type`, `preview` |
| `generate_code` | Create new code | `description`, `style`, `framework` |

---

## ⚠️  Important Notes

**Safety:**
- Backups created automatically by default
- Validates fixes don't break syntax
- All changes are logged
- Can be reverted using backups

**Language Support:**
- **Python**: Full AST analysis (deep bug detection)
- **JavaScript/TypeScript**: Linter integration
- **Rust/Go**: Basic analysis

**Limitations:**
- AST analysis is Python-only (deepest)
- Other languages use linter-based checks
- Generated code may need refinement
- Always review AI-generated code

**Performance:**
- Analysis: Fast (<1s for most files)
- Fixing: Fast (<1s)
- Generation: Depends on complexity (2-10s)
- Testing: Moderate (5-15s)

---

## 🚀 Quick Start Commands

**Analyze:**
```python
analyze_code_file("myapp/server.py")
```

**Fix:**
```python
fix_code_file("buggy.py", backup=True)
```

**Generate:**
```python
generate_code(
    "Calculate factorial recursively",
    language="python",
    style="function",
    include_tests=True
)
```

**Test:**
```python
generate_tests("utils.py", test_framework="pytest")
```

**Refactor:**
```python
refactor_code("legacy.py", "modernize", preview=True)
```