"""
Code Assistant MCP Server
Automated code analysis, bug detection, and fixing
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from servers.skills.skill_loader import SkillLoader

import inspect
import json
import logging

# Import the actual implementation from tools directory
from tools.code_assistant.tool import (
    analyze_code_file_impl,
    fix_code_file_impl,
    suggest_improvements_impl,
    explain_code_impl,
    generate_tests_impl,
    refactor_code_impl
)

# Import tool control if available (optional)
try:
    from tools.tool_control import check_tool_enabled
except ImportError:
    # Fallback if tool_control not available
    def check_tool_enabled(category=None):
        def decorator(func):
            return func
        return decorator

from mcp.server.fastmcp import FastMCP

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Setup logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

file_handler = logging.FileHandler(LOG_DIR / "mcp-server.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("mcp_code_assistant").setLevel(logging.INFO)

logger = logging.getLogger("mcp_code_assistant")
logger.info("🚀 Code Assistant server logging initialized")

mcp = FastMCP("code-assistant-server")


@mcp.tool()
@check_tool_enabled(category="code")
def analyze_code_file(file_path: str, language: str = "auto", deep_analysis: bool = True) -> str:
    """
    Analyze a code file for bugs, anti-patterns, and issues.

    Supports Python (AST-based deep analysis), JavaScript, TypeScript, Rust, and Go.

    Args:
        file_path (str): Path to the code file to analyze
        language (str): Language override ("auto", "python", "javascript", etc.)
        deep_analysis (bool): Use deep AST analysis for Python (default: True)

    Returns:
        JSON with:
        - language: Detected language
        - total_issues: Number of issues found
        - errors: Count of error-severity issues
        - warnings: Count of warning-severity issues
        - issues: List of issues with:
          - severity: "error", "warning", or "info"
          - type: Issue type (e.g., "MutableDefault", "BareExcept")
          - line: Line number
          - message: Description of the issue
          - suggestion: How to fix it
          - fix: (optional) Automatic fix description
        - fixable: Number of issues that can be auto-fixed

    Example:
        analyze_code_file("myapp/server.py")
        analyze_code_file("src/utils.js", language="javascript")

    Use cases:
        - Pre-commit checks
        - Code review assistance
        - Learning tool (understand why something is wrong)
        - Migration prep (find issues before refactoring)
    """
    logger.info(f"🔍 [TOOL] analyze_code_file called: {file_path}")
    return analyze_code_file_impl(file_path, language, deep_analysis)


@mcp.tool()
@check_tool_enabled(category="code")
def fix_code_file(file_path: str, auto_fix: bool = True, backup: bool = True, dry_run: bool = False) -> str:
    """
    Automatically fix detected issues in a code file.

    Creates backup, applies fixes, runs formatter.

    Args:
        file_path (str): Path to the code file
        auto_fix (bool): Apply automatic fixes (True) or just show suggestions (False)
        backup (bool): Create backup before fixing (default: True, recommended)
        dry_run (bool): Show what would be fixed without actually modifying (default: False)

    Returns:
        JSON with:
        - fixes_applied: Number of fixes applied
        - details: List of what was fixed
        - backup_path: Path to backup file if created
        - formatted: Whether code was formatted after fixing
        - original_content: Original code (if dry_run=True)
        - new_content: Fixed code (if dry_run=True)

    Example:
        fix_code_file("buggy.py")                          # Fix with backup
        fix_code_file("test.py", auto_fix=False)          # Just show suggestions
        fix_code_file("script.py", dry_run=True)          # Preview changes

    Safety features:
        - Always creates backup by default
        - Validates fixes don't break syntax
        - Logs all changes
        - Can be reverted using backup
    """
    logger.info(f"🔧 [TOOL] fix_code_file called: {file_path} (auto_fix={auto_fix}, backup={backup})")
    return fix_code_file_impl(file_path, auto_fix, backup, dry_run)


@mcp.tool()
@check_tool_enabled(category="code")
def suggest_improvements(file_path: str, context: str = "", focus: str = "all") -> str:
    """
    Suggest code improvements and best practices.

    Args:
        file_path (str): Path to code file
        context (str): Additional context about what you're building
        focus (str): What to focus on: "all", "performance", "readability", "security"

    Returns:
        JSON with:
        - suggestions: List of improvement suggestions
          - type: "best_practice", "performance", "security", "documentation"
          - message: What to improve
          - reason: Why it matters
          - suggestion: How to implement it
          - priority: "high", "medium", "low"
        - language: Detected language
        - focus_area: What was analyzed

    Example:
        suggest_improvements("api.py", context="REST API server")
        suggest_improvements("utils.js", focus="performance")

    Types of suggestions:
        - Best practices (logging vs print, type hints, etc.)
        - Performance opportunities (list comprehensions, caching)
        - Security issues (SQL injection, XSS, etc.)
        - Documentation gaps (missing docstrings)
        - Code organization (function length, complexity)
    """
    logger.info(f"💡 [TOOL] suggest_improvements called: {file_path}")
    return suggest_improvements_impl(file_path, context, focus)


@mcp.tool()
@check_tool_enabled(category="code")
def explain_code(file_path: str, line_start: int = None, line_end: int = None, detail_level: str = "medium") -> str:
    """
    Explain what code does in natural language.

    Args:
        file_path (str): Path to code file
        line_start (int): Start line (optional, explain specific section)
        line_end (int): End line (optional)
        detail_level (str): "brief", "medium", or "detailed"

    Returns:
        JSON with:
        - explanation: Plain English explanation
        - key_concepts: List of important concepts used
        - complexity: Estimated complexity
        - dependencies: External dependencies used

    Example:
        explain_code("algorithm.py")
        explain_code("utils.py", line_start=45, line_end=67)
        explain_code("complex.py", detail_level="detailed")

    Use cases:
        - Understanding unfamiliar code
        - Onboarding new developers
        - Code review explanations
        - Documentation generation
    """
    logger.info(f"📖 [TOOL] explain_code called: {file_path}")
    return explain_code_impl(file_path, line_start, line_end, detail_level)


@mcp.tool()
@check_tool_enabled(category="code")
def generate_tests(file_path: str, test_framework: str = "auto", coverage_target: str = "functions") -> str:
    """
    Generate unit tests for code.

    Args:
        file_path (str): Path to source file to test
        test_framework (str): "auto", "pytest", "unittest", "jest", etc.
        coverage_target (str): "functions", "classes", "all"

    Returns:
        JSON with:
        - test_file_path: Path where tests were/should be saved
        - test_code: Generated test code
        - functions_covered: List of functions with tests
        - framework_used: Test framework chosen
        - coverage_estimate: Estimated code coverage %

    Example:
        generate_tests("myapp/utils.py")
        generate_tests("api.py", test_framework="pytest", coverage_target="all")

    Features:
        - Analyzes function signatures
        - Creates test cases for common scenarios
        - Includes edge case tests
        - Follows framework conventions
        - Generates fixtures and mocks
    """
    logger.info(f"🧪 [TOOL] generate_tests called: {file_path}")
    return generate_tests_impl(file_path, test_framework, coverage_target)


@mcp.tool()
@check_tool_enabled(category="code")
def refactor_code(
    file_path: str,
    refactor_type: str,
    target: str = "",
    preview: bool = True
) -> str:
    """
    Refactor code using common patterns.

    Args:
        file_path (str): Path to code file
        refactor_type (str): Type of refactoring:
            - "extract_function": Extract code block into function
            - "rename": Rename variable/function
            - "simplify": Simplify complex expressions
            - "modernize": Update to modern syntax (f-strings, type hints, etc.)
            - "optimize": Apply performance optimizations
        target (str): What to refactor (function name, line range, etc.)
        preview (bool): Show preview without applying (default: True)

    Returns:
        JSON with:
        - refactor_type: Type of refactoring applied
        - changes: List of changes made
        - preview: Code preview if preview=True
        - applied: Whether changes were applied
        - backup_path: Path to backup if changes applied

    Example:
        refactor_code("app.py", "extract_function", target="lines:45-67")
        refactor_code("legacy.py", "modernize")
        refactor_code("utils.py", "rename", target="old_name:new_name")

    Refactoring types:
        - extract_function: DRY principle, reduce duplication
        - rename: Improve naming clarity
        - simplify: Reduce cognitive complexity
        - modernize: Use latest language features
        - optimize: Performance improvements
    """
    logger.info(f"♻️  [TOOL] refactor_code called: {file_path} ({refactor_type})")
    return refactor_code_impl(file_path, refactor_type, target, preview)


# Skill management tools
skill_registry = None

@mcp.tool()
@check_tool_enabled(category="code")
def list_skills() -> str:
    """List all available skills for code assistant."""
    logger.info("📚 [TOOL] list_skills called")
    if skill_registry is None:
        return json.dumps({
            "server": "code-assistant-server",
            "skills": [],
            "message": "Skills not loaded"
        }, indent=2)

    return json.dumps({
        "server": "code-assistant-server",
        "skills": skill_registry.list()
    }, indent=2)


@mcp.tool()
@check_tool_enabled(category="code")
def read_skill(skill_name: str) -> str:
    """Read the full content of a skill."""
    logger.info(f"📖 [TOOL] read_skill called: {skill_name}")

    if skill_registry is None:
        return json.dumps({"error": "Skills not loaded"}, indent=2)

    content = skill_registry.get_skill_content(skill_name)
    if content:
        return content

    available = [s.name for s in skill_registry.skills.values()]
    return json.dumps({
        "error": f"Skill '{skill_name}' not found",
        "available_skills": available
    }, indent=2)


def get_tool_names_from_module():
    """Auto-discover tools from this module"""
    current_module = sys.modules[__name__]
    tool_names = []

    for name, obj in inspect.getmembers(current_module):
        if inspect.isfunction(obj) and obj.__module__ == __name__:
            if not name.startswith('_') and name != 'get_tool_names_from_module':
                tool_names.append(name)

    return tool_names


if __name__ == "__main__":
    # Auto-discover tools
    server_tools = get_tool_names_from_module()

    # Load skills
    skills_dir = Path(__file__).parent / "skills"
    loader = SkillLoader(server_tools)
    skill_registry = loader.load_all(skills_dir)

    logger.info(f"🛠️  {len(server_tools)} tools: {', '.join(server_tools)}")
    logger.info(f"📚 {len(skill_registry.skills)} skills loaded")

    mcp.run(transport="stdio")