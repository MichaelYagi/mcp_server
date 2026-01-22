"""
Code Review MCP Server
Runs over stdio transport
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
import sys
from typing import Optional
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from tools.code_review.scan_directory import scan_directory
from tools.code_review.summarize_codebase import summarize_codebase
from tools.code_review.fix_bug import fix_bug
from tools.code_review.search_code import search_code

load_dotenv(PROJECT_ROOT / ".env", override=True)

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers (in case something already configured it)
root_logger.handlers.clear()

# Create formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Create file handler
file_handler = logging.FileHandler(LOG_DIR / "mcp_code_review_server.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Disable propagation to avoid duplicate logs
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("mcp_code_review_server").setLevel(logging.INFO)

logger = logging.getLogger("mcp_code_review_server")
logger.info("🚀 Server logging initialized - writing to logs/mcp_code_review_server.log")

mcp = FastMCP("code-review-server")

@mcp.tool()
def summarize_code_file(path: str, max_bytes: int = 200_000) -> str:
    """
    Read a code file and return a structured summary.

    Args:
        path (str, required): Absolute or relative file path
        max_bytes (int, optional): Maximum file size to read (default: 200,000)

    Returns:
        JSON string with:
        - path: File path
        - size: File size in bytes
        - num_lines: Total line count
        - imports: List of import statements
        - classes: List of class names
        - functions: List of function names
        - preview: First 20 lines of code
        - error: Error message if file cannot be read

    Works across Windows, Linux, and macOS.

    Use when user wants to summarize or review a specific code file.
    """
    logger.info(f"🛠 [server] summarize_code_file called with path: {path}, max_bytes: {max_bytes}")
    from pathlib import Path
    import json

    p = Path(path)

    if not p.exists():
        return json.dumps({"error": f"File not found: {path}"})

    if not p.is_file():
        return json.dumps({"error": f"Not a file: {path}"})

    try:
        data = p.read_bytes()

        if len(data) > max_bytes:
            return json.dumps({
                "error": "File too large",
                "path": path,
                "size": len(data),
                "max_bytes": max_bytes
            })

        text = data.decode("utf-8", errors="replace")

        import re

        lines = text.splitlines()
        num_lines = len(lines)

        imports = [l.strip() for l in lines if l.strip().startswith("import") or l.strip().startswith("from")]
        classes = re.findall(r"class\s+([A-Za-z0-9_]+)", text)
        functions = re.findall(r"def\s+([A-Za-z0-9_]+)", text)

        summary = {
            "path": path,
            "size": len(data),
            "num_lines": num_lines,
            "imports": imports,
            "classes": classes,
            "functions": functions,
            "preview": "\n".join(lines[:20])
        }

        return json.dumps(summary, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to read or summarize file: {str(e)}",
            "path": path
        })


@mcp.tool()
def search_code_in_directory(
        query: str,
        extension: Optional[str] = None,
        directory: Optional[str] = "."
) -> str:
    """
    Search source code for text or regex patterns across multiple files.

    Args:
        query (str, required): Text or regex pattern to find (e.g., 'class Weather', 'to-do')
        extension (str, optional): Filter by file type (e.g., 'py', 'js', 'java')
        directory (str, optional): Starting folder path (default: current directory)

    Returns:
        JSON string with:
        - matches: Array of results, each containing:
          - file: File path
          - line_number: Line where match was found
          - line_text: The matching line content
          - context: Surrounding lines (if available)
        - total_matches: Number of matches found
        - files_searched: Number of files searched

    Use when user wants to locate code, patterns, class definitions, function calls, or text references.
    """
    logger.info(
        f"🛠 [server] search_code_in_directory called with query: {query}, extension: {extension}, directory: {directory}")
    result = search_code(query, extension, directory)
    return json.dumps(result, indent=2)


@mcp.tool()
def scan_code_directory(path: str) -> str:
    """
    Recursively scan a directory and summarize its code structure.

    Args:
        path (str, required): Directory path to scan

    Returns:
        JSON string with:
        - directory: Scanned path
        - total_files: Number of code files found
        - total_size_bytes: Total size of all files
        - languages: {language: file_count} breakdown
        - files: Array of file details:
          - path: File path
          - size: File size in bytes
          - language: Detected language
          - lines: Line count (if analyzed)

    Use when user wants an overview of a codebase or project folder.
    """
    logger.info(f"🛠 [server] scan_code_directory called with path: {path}")
    result = scan_directory(path)
    return json.dumps(result, indent=2)


@mcp.tool()
def summarize_code() -> str:
    """
    Generate a high-level summary of the entire codebase.

    Args:
        None (scans current project directory)

    Returns:
        JSON string with:
        - project_structure: Directory tree
        - language_breakdown: File counts by language
        - key_files: Important files identified
        - architecture_notes: High-level design observations
        - entry_points: Main/startup files
        - dependencies: External libraries detected

    Use when user wants a broad overview for onboarding, documentation, or quick understanding.
    """
    logger.info(f"🛠 [server] summarize_code called")
    result = summarize_codebase()
    return json.dumps(result, indent=2)


@mcp.tool()
def debug_fix(error_message: str,
              stack_trace: Optional[str] = None,
              code_snippet: Optional[str] = None,
              environment: Optional[str] = None) -> str:
    """
    Analyze a bug and propose fixes with root cause analysis.

    Args:
        error_message (str, required): The error message or exception text
        stack_trace (str, optional): Full stack trace if available
        code_snippet (str, optional): Relevant code that caused the error
        environment (str, optional): Environment details (OS, language version, etc.)

    Returns:
        JSON string with:
        - error_type: Classified error category
        - likely_causes: Array of potential root causes
        - suggested_fixes: Array of fix recommendations with code examples
        - references: Links to documentation or similar issues
        - severity: Estimated severity (low/medium/high/critical)

    Use when user wants help diagnosing, debugging, or fixing code issues.
    """
    logger.info(
        f"🛠 [server] debug_fix called with error_message: {error_message}, stack_trace: {stack_trace}, code_snippet: {code_snippet}, environment: {environment}")
    result = fix_bug(
        error_message=error_message,
        stack_trace=stack_trace,
        code_snippet=code_snippet,
        environment=environment
    )
    return json.dumps(result, indent=2)

skill_registry = None

@mcp.tool()
def list_skills() -> str:
    """List all available skills for this server."""
    logger.info(f"🛠  list_skills called")
    if skill_registry is None:
        return json.dumps({
            "server": "code-review-server",
            "skills": [],
            "message": "Skills not loaded"
        }, indent=2)

    return json.dumps({
        "server": "code-review-server",
        "skills": skill_registry.list()
    }, indent=2)


@mcp.tool()
def read_skill(skill_name: str) -> str:
    """Read the full content of a skill."""
    logger.info(f"🛠  read_skill called")

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
    """Extract all function names from current module (auto-discovers tools)"""
    current_module = sys.modules[__name__]
    tool_names = []

    for name, obj in inspect.getmembers(current_module):
        if inspect.isfunction(obj) and obj.__module__ == __name__:
            if not name.startswith('_') and name != 'get_tool_names_from_module':
                tool_names.append(name)

    return tool_names

if __name__ == "__main__":
    # Auto-extract tool names - NO manual list needed!
    server_tools = get_tool_names_from_module()

    # Load skills
    skills_dir = Path(__file__).parent / "skills"
    loader = SkillLoader(server_tools)
    skill_registry = loader.load_all(skills_dir)

    logger.info(f"🛠  {len(server_tools)} tools: {', '.join(server_tools)}")
    logger.info(f"🛠  {len(skill_registry.skills)} skills loaded")
    mcp.run(transport="stdio")