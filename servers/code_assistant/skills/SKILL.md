---
name: code_assistant
description: >
  Automated code analysis, bug detection, fixing, and generation using AST analysis.
  Supports Python (deep analysis), JavaScript, TypeScript, Java, Kotlin, Rust, and Go.
  Detects mutable defaults, bare except clauses, identity comparisons, unused imports.
  Generates code from natural language, creates tests, suggests improvements, and refactors.
tags:
  - code
  - python
  - javascript
  - typescript
  - java
  - kotlin
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
- **Java** - Linter integration (checkstyle, spotbugs)
- **Kotlin** - Linter integration (ktlint, detekt)
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
    language="auto",           # or "python", "javascript", "java", "kotlin", etc.
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

**Mutable Default Arguments** (Python)
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

**Identity Comparison with Literals** (Python)
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

**Null Pointer Dereference** (Java/Kotlin)
```java
// ❌ DANGEROUS - can throw NullPointerException
String result = obj.toString();

// ✅ SAFE - null check
if (obj != null) {
    String result = obj.toString();
}

// ✅ KOTLIN - safe call
val result = obj?.toString()
```

#### ⚠️  WARNINGS (Important)

**Bare Except** (Python)
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

**Missing Override Annotation** (Java)
```java
// ❌ MISSING - can break if parent changes
public String toString() {
    return "MyClass";
}

// ✅ CORRECT
@Override
public String toString() {
    return "MyClass";
}
```

**Inefficient String Concatenation** (Java)
```java
// ❌ INEFFICIENT - creates many String objects
String result = "";
for (String s : list) {
    result += s;
}

// ✅ EFFICIENT
StringBuilder result = new StringBuilder();
for (String s : list) {
    result.append(s);
}
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

---

## 🧪 Part 5: Test Generation

### Tool: `generate_tests`

```python
generate_tests(
    file_path="utils.py",
    test_framework="auto",        # or "pytest", "unittest", "jest", "junit", "kotest"
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

---

## ✨ Part 7: Code Generation

### Tool: `generate_code`

```python
generate_code(
    description="Calculate factorial recursively with error handling",
    language="python",         # "javascript", "typescript", "java", "kotlin", "rust", "go"
    style="function",          # "class", "module", "script", "api_endpoint"
    include_tests=False,
    include_docstrings=True,
    framework="",              # "fastapi", "flask", "react", "spring", "ktor"
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

### Language-Specific Examples

#### Java
```java
// Generate Spring Boot REST endpoint
generate_code(
    "REST endpoint to create user with email validation",
    language="java",
    style="api_endpoint",
    framework="spring"
)

// Output:
@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @PostMapping
    public ResponseEntity<User> createUser(@Valid @RequestBody UserRequest request) {
        // Email validation
        if (!isValidEmail(request.getEmail())) {
            throw new IllegalArgumentException("Invalid email format");
        }
        
        User user = userService.createUser(request);
        return ResponseEntity.ok(user);
    }
    
    private boolean isValidEmail(String email) {
        return email != null && email.matches("^[A-Za-z0-9+_.-]+@(.+)$");
    }
}
```

#### Kotlin
```kotlin
// Generate data class with validation
generate_code(
    "User data class with email validation and builder",
    language="kotlin",
    style="class"
)

// Output:
data class User(
    val id: Long,
    val email: String,
    val name: String
) {
    init {
        require(email.isNotBlank()) { "Email cannot be blank" }
        require(email.matches(Regex("^[A-Za-z0-9+_.-]+@(.+)$"))) { "Invalid email format" }
    }
    
    companion object {
        fun builder() = UserBuilder()
    }
    
    class UserBuilder {
        private var id: Long = 0
        private var email: String = ""
        private var name: String = ""
        
        fun id(id: Long) = apply { this.id = id }
        fun email(email: String) = apply { this.email = email }
        fun name(name: String) = apply { this.name = name }
        
        fun build() = User(id, email, name)
    }
}
```

---

## 🛠️  Tool Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `analyze_code_file` | Find bugs | `file_path`, `deep_analysis`, `language` |
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
- **Python**: Full AST analysis (deepest)
- **JavaScript/TypeScript**: Linter integration (ESLint)
- **Java**: Linter integration (Checkstyle, SpotBugs)
- **Kotlin**: Linter integration (ktlint, detekt)
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
analyze_code_file("src/UserService.java")
analyze_code_file("app/User.kt")
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

generate_code(
    "Spring Boot REST controller for user management",
    language="java",
    style="api_endpoint",
    framework="spring"
)

generate_code(
    "Ktor REST endpoint with coroutines",
    language="kotlin",
    style="api_endpoint",
    framework="ktor"
)
```

**Test:**
```python
generate_tests("utils.py", test_framework="pytest")
generate_tests("UserService.java", test_framework="junit")
generate_tests("UserRepository.kt", test_framework="kotest")
```

**Refactor:**
```python
refactor_code("legacy.py", "modernize", preview=True)
```