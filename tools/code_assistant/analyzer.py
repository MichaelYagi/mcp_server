"""
Code Analysis Core Logic
========================
Located at: tools/code_assistant/analyzer.py

This module contains the actual implementation of code analysis.
The MCP server (servers/code_assistant/server.py) calls these functions.
"""

import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# LANGUAGE CONFIGURATION
# ============================================================================

@dataclass
class LanguageConfig:
    """Configuration for a programming language"""
    name: str
    extensions: List[str]
    comment_single: str
    comment_multi_start: Optional[str]
    comment_multi_end: Optional[str]
    linter_command: Optional[List[str]]
    formatter_command: Optional[List[str]]


SUPPORTED_LANGUAGES = {
    "python": LanguageConfig(
        name="python",
        extensions=[".py"],
        comment_single="#",
        comment_multi_start='"""',
        comment_multi_end='"""',
        linter_command=["ruff", "check", "{file}"],
        formatter_command=["black", "{file}"]
    ),
    "javascript": LanguageConfig(
        name="javascript",
        extensions=[".js", ".jsx"],
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        linter_command=["eslint", "{file}"],
        formatter_command=["prettier", "--write", "{file}"]
    ),
    "typescript": LanguageConfig(
        name="typescript",
        extensions=[".ts", ".tsx"],
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        linter_command=["eslint", "{file}"],
        formatter_command=["prettier", "--write", "{file}"]
    ),
}


def detect_language(file_path: str) -> Optional[LanguageConfig]:
    """Detect programming language from file extension"""
    ext = Path(file_path).suffix.lower()
    for lang_config in SUPPORTED_LANGUAGES.values():
        if ext in lang_config.extensions:
            return lang_config
    return None


# ============================================================================
# PYTHON ANALYZER
# ============================================================================

class PythonBugDetector:
    """Detect common Python bugs using AST analysis"""

    @staticmethod
    def analyze_file(file_path: str) -> List[Dict[str, Any]]:
        """Analyze Python file for common bugs"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            tree = ast.parse(code, filename=file_path)

            # Run various checks
            issues.extend(PythonBugDetector._check_mutable_defaults(tree))
            issues.extend(PythonBugDetector._check_bare_except(tree))
            issues.extend(PythonBugDetector._check_comparisons(tree))
            issues.extend(PythonBugDetector._check_unused_imports(tree, code))

        except SyntaxError as e:
            issues.append({
                "severity": "error",
                "type": "SyntaxError",
                "line": e.lineno or 0,
                "column": e.offset or 0,
                "message": str(e.msg),
                "suggestion": "Fix syntax error before proceeding"
            })
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            issues.append({
                "severity": "error",
                "type": "AnalysisError",
                "line": 0,
                "message": f"Failed to analyze: {str(e)}"
            })

        return issues

    @staticmethod
    def _check_mutable_defaults(tree: ast.AST) -> List[Dict]:
        """Check for mutable default arguments (dangerous!)"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for i, default in enumerate(node.args.defaults):
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        arg_name = node.args.args[-(len(node.args.defaults) - i)].arg
                        issues.append({
                            "severity": "error",
                            "type": "MutableDefault",
                            "line": node.lineno,
                            "column": node.col_offset,
                            "message": f"Function '{node.name}' has mutable default argument '{arg_name}'",
                            "suggestion": f"Use None as default: {arg_name}=None, then inside: if {arg_name} is None: {arg_name} = []",
                            "fix_type": "mutable_default",
                            "function_name": node.name,
                            "arg_name": arg_name
                        })

        return issues

    @staticmethod
    def _check_bare_except(tree: ast.AST) -> List[Dict]:
        """Check for bare except clauses"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append({
                        "severity": "warning",
                        "type": "BareExcept",
                        "line": node.lineno,
                        "column": node.col_offset,
                        "message": "Bare 'except:' catches all exceptions (including SystemExit, KeyboardInterrupt)",
                        "suggestion": "Use 'except Exception as e:' to catch only Exception and its subclasses",
                        "fix_type": "bare_except"
                    })

        return issues

    @staticmethod
    def _check_comparisons(tree: ast.AST) -> List[Dict]:
        """Check for problematic comparisons"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Check for 'is' with literals
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.Is, ast.IsNot)):
                        if isinstance(comparator, (ast.Constant, ast.Num, ast.Str)):
                            literal_value = getattr(comparator, 'value',
                                                    getattr(comparator, 'n', getattr(comparator, 's', '?')))
                            issues.append({
                                "severity": "error",
                                "type": "IdentityComparison",
                                "line": node.lineno,
                                "column": node.col_offset,
                                "message": f"Using 'is' to compare with literal ({literal_value})",
                                "suggestion": "Use '==' for value comparison, 'is' for identity (None, True, False)",
                                "fix_type": "identity_comparison"
                            })

        return issues

    @staticmethod
    def _check_unused_imports(tree: ast.AST, code: str) -> List[Dict]:
        """Check for unused imports (simplified)"""
        issues = []
        imports = {}
        used_names = set()

        # Collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_name = alias.asname or alias.name.split('.')[0]
                    imports[import_name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    import_name = alias.asname or alias.name
                    imports[import_name] = node.lineno

        # Collect used names
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Check first part of attribute access
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Find unused
        for import_name, lineno in imports.items():
            if import_name not in used_names:
                # Double-check it's not in a string or comment
                if import_name in code:
                    # It's mentioned somewhere, might be intentional
                    continue

                issues.append({
                    "severity": "info",
                    "type": "UnusedImport",
                    "line": lineno,
                    "message": f"Import '{import_name}' appears unused",
                    "suggestion": f"Remove unused import or use it",
                    "fix_type": "unused_import",
                    "import_name": import_name
                })

        return issues


# ============================================================================
# GENERIC ANALYZER (for non-Python)
# ============================================================================

def run_linter(file_path: str, lang_config: LanguageConfig) -> Dict[str, Any]:
    """Run external linter and parse results"""
    if not lang_config.linter_command:
        return {"status": "no_linter", "issues": []}

    try:
        cmd = [arg.format(file=file_path) for arg in lang_config.linter_command]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(file_path).parent
        )

        return {
            "status": "success" if result.returncode == 0 else "issues_found",
            "output": result.stdout,
            "errors": result.stderr,
            "return_code": result.returncode
        }

    except FileNotFoundError:
        return {
            "status": "linter_not_installed",
            "tool": lang_config.linter_command[0],
            "message": f"Linter '{lang_config.linter_command[0]}' not found. Install it first."
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Linter timed out after 30 seconds"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_code_file(file_path: str, language: str = "auto") -> Dict[str, Any]:
    """
    Analyze a code file for bugs and issues.

    Args:
        file_path: Path to code file
        language: Language override or "auto"

    Returns:
        Dict with issues, stats, and metadata
    """
    logger.info(f"🔍 Analyzing: {file_path}")

    # Validate file exists
    if not Path(file_path).exists():
        return {
            "error": f"File not found: {file_path}",
            "status": "file_not_found"
        }

    # Detect language
    if language == "auto":
        lang_config = detect_language(file_path)
        if not lang_config:
            return {
                "error": f"Could not detect language for {file_path}",
                "supported_extensions": [ext for cfg in SUPPORTED_LANGUAGES.values() for ext in cfg.extensions],
                "status": "unknown_language"
            }
    else:
        lang_config = SUPPORTED_LANGUAGES.get(language.lower())
        if not lang_config:
            return {
                "error": f"Language '{language}' not supported",
                "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
                "status": "unsupported_language"
            }

    # Run analysis
    try:
        if lang_config.name == "python":
            issues = PythonBugDetector.analyze_file(file_path)
        else:
            # Use external linter
            linter_result = run_linter(file_path, lang_config)
            if linter_result['status'] == 'linter_not_installed':
                return {
                    "error": linter_result['message'],
                    "status": "linter_not_available",
                    "language": lang_config.name
                }
            issues = _parse_linter_output(linter_result, lang_config)

        # Categorize
        errors = [i for i in issues if i.get('severity') == 'error']
        warnings = [i for i in issues if i.get('severity') == 'warning']
        info = [i for i in issues if i.get('severity') == 'info']

        return {
            "file": file_path,
            "language": lang_config.name,
            "status": "success",
            "total_issues": len(issues),
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(info),
            "fixable": len([i for i in issues if 'fix_type' in i]),
            "issues": issues,
            "summary": f"Found {len(errors)} errors, {len(warnings)} warnings, {len(info)} info"
        }

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return {
            "error": str(e),
            "status": "analysis_failed",
            "file": file_path
        }


def _parse_linter_output(linter_result: Dict, lang_config: LanguageConfig) -> List[Dict]:
    """Parse linter output into standardized format"""
    # TODO: Implement language-specific parsing
    # For now, return empty list
    return []