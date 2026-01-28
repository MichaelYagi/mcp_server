"""
Code Assistant Tool Implementation
===================================
Location: tools/code_assistant/tool.py

This is the actual implementation called by servers/code_assistant/server.py
"""

import ast
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)


# ===========================================================================
# LANGUAGE CONFIGURATION
# ===========================================================================

@dataclass
class LanguageConfig:
    name: str
    extensions: List[str]
    comment_single: str
    linter_command: Optional[List[str]] = None
    formatter_command: Optional[List[str]] = None


SUPPORTED_LANGUAGES = {
    "python": LanguageConfig(
        name="python",
        extensions=[".py"],
        comment_single="#",
        linter_command=["ruff", "check", "{file}"],
        formatter_command=["black", "--quiet", "{file}"]
    ),
    "javascript": LanguageConfig(
        name="javascript",
        extensions=[".js", ".jsx"],
        comment_single="//",
        linter_command=["eslint", "{file}"],
        formatter_command=["prettier", "--write", "{file}"]
    ),
    "typescript": LanguageConfig(
        name="typescript",
        extensions=[".ts", ".tsx"],
        comment_single="//",
        linter_command=["eslint", "{file}"],
        formatter_command=["prettier", "--write", "{file}"]
    ),
}


def detect_language(file_path: str) -> Optional[LanguageConfig]:
    """Detect language from file extension"""
    ext = Path(file_path).suffix.lower()
    for lang in SUPPORTED_LANGUAGES.values():
        if ext in lang.extensions:
            return lang
    return None


# ===========================================================================
# PYTHON BUG DETECTOR
# ===========================================================================

class PythonBugDetector:
    @staticmethod
    def analyze(file_path: str) -> List[Dict[str, Any]]:
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code, filename=file_path)

            issues.extend(PythonBugDetector._check_mutable_defaults(tree))
            issues.extend(PythonBugDetector._check_bare_except(tree))
            issues.extend(PythonBugDetector._check_comparisons(tree))
            issues.extend(PythonBugDetector._check_unused_imports(tree, code))

        except SyntaxError as e:
            issues.append({
                "severity": "error",
                "type": "SyntaxError",
                "line": e.lineno or 0,
                "message": f"Syntax error: {e.msg}",
                "suggestion": "Fix syntax error before proceeding"
            })
        return issues

    @staticmethod
    def _check_mutable_defaults(tree) -> List[Dict]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for i, default in enumerate(node.args.defaults):
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        arg_idx = len(node.args.args) - len(node.args.defaults) + i
                        arg_name = node.args.args[arg_idx].arg
                        issues.append({
                            "severity": "error",
                            "type": "MutableDefault",
                            "line": node.lineno,
                            "message": f"Function '{node.name}' has mutable default argument '{arg_name}='",
                            "suggestion": f"Use None as default, then: if {arg_name} is None: {arg_name} = []",
                            "fix_type": "mutable_default"
                        })
        return issues

    @staticmethod
    def _check_bare_except(tree) -> List[Dict]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "severity": "warning",
                    "type": "BareExcept",
                    "line": node.lineno,
                    "message": "Bare 'except:' catches all exceptions including SystemExit",
                    "suggestion": "Use 'except Exception as e:' instead",
                    "fix_type": "bare_except"
                })
        return issues

    @staticmethod
    def _check_comparisons(tree) -> List[Dict]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for op, comp in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.Is, ast.IsNot)):
                        if isinstance(comp, (ast.Constant, ast.Num, ast.Str)):
                            issues.append({
                                "severity": "error",
                                "type": "IdentityComparison",
                                "line": node.lineno,
                                "message": "Using 'is' to compare with literal",
                                "suggestion": "Use '==' for value comparison",
                                "fix_type": "identity_comparison"
                            })
        return issues

    @staticmethod
    def _check_unused_imports(tree, code) -> List[Dict]:
        issues = []
        imports = {}
        used_names = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports[name] = node.lineno
            elif isinstance(node, ast.Name):
                used_names.add(node.id)

        for imp_name, lineno in imports.items():
            if imp_name not in used_names and imp_name in code:
                issues.append({
                    "severity": "info",
                    "type": "UnusedImport",
                    "line": lineno,
                    "message": f"Import '{imp_name}' appears unused",
                    "suggestion": "Remove or comment out",
                    "fix_type": "unused_import"
                })
        return issues


# ===========================================================================
# MAIN IMPLEMENTATION FUNCTIONS
# ===========================================================================

def analyze_code_file_impl(file_path: str, language: str, deep_analysis: bool) -> str:
    """Implementation of analyze_code_file"""
    if not Path(file_path).exists():
        return json.dumps({"error": f"File not found: {file_path}"}, indent=2)

    lang = detect_language(file_path) if language == "auto" else SUPPORTED_LANGUAGES.get(language.lower())
    if not lang:
        return json.dumps({"error": "Could not detect language"}, indent=2)

    if lang.name == "python" and deep_analysis:
        issues = PythonBugDetector.analyze(file_path)
    else:
        issues = []

    errors = [i for i in issues if i.get('severity') == 'error']
    warnings = [i for i in issues if i.get('severity') == 'warning']
    info = [i for i in issues if i.get('severity') == 'info']

    return json.dumps({
        "file": file_path,
        "language": lang.name,
        "total_issues": len(issues),
        "errors": len(errors),
        "warnings": len(warnings),
        "info": len(info),
        "fixable": len([i for i in issues if 'fix_type' in i]),
        "issues": issues
    }, indent=2)


def fix_code_file_impl(file_path: str, auto_fix: bool, backup: bool, dry_run: bool) -> str:
    """Implementation of fix_code_file"""
    if not Path(file_path).exists():
        return json.dumps({"error": "File not found"}, indent=2)

    backup_path = None
    if backup and not dry_run:
        backup_path = f"{file_path}.backup"
        shutil.copy2(file_path, backup_path)

    lang = detect_language(file_path)
    if not lang:
        return json.dumps({"error": "Could not detect language"}, indent=2)

    fixes_applied = []

    if lang.name == "python":
        issues = PythonBugDetector.analyze(file_path)
        fixable = [i for i in issues if 'fix_type' in i]

        if not auto_fix:
            return json.dumps({
                "suggestions": [f"Line {i['line']}: {i['suggestion']}" for i in fixable]
            }, indent=2)

        with open(file_path, 'r') as f:
            lines = f.readlines()

        for issue in sorted(fixable, key=lambda x: x['line'], reverse=True):
            idx = issue['line'] - 1
            if 0 <= idx < len(lines):
                orig = lines[idx]

                if issue['fix_type'] == 'bare_except':
                    lines[idx] = orig.replace('except:', 'except Exception as e:')
                    fixes_applied.append(f"Line {issue['line']}: Fixed bare except")

                elif issue['fix_type'] == 'identity_comparison':
                    lines[idx] = orig.replace(' is ', ' == ').replace(' is not ', ' != ')
                    fixes_applied.append(f"Line {issue['line']}: Fixed identity comparison")

        if fixes_applied and not dry_run:
            with open(file_path, 'w') as f:
                f.writelines(lines)

    # Run formatter
    formatted = False
    if lang.formatter_command and not dry_run and fixes_applied:
        try:
            cmd = [arg.format(file=file_path) for arg in lang.formatter_command]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            formatted = result.returncode == 0
        except:
            pass

    return json.dumps({
        "fixes_applied": len(fixes_applied),
        "details": fixes_applied,
        "backup_path": backup_path,
        "formatted": formatted,
        "dry_run": dry_run
    }, indent=2)


def suggest_improvements_impl(file_path: str, context: str, focus: str) -> str:
    """Implementation of suggest_improvements"""
    if not Path(file_path).exists():
        return json.dumps({"error": "File not found"}, indent=2)

    lang = detect_language(file_path)
    if not lang:
        return json.dumps({"error": "Could not detect language"}, indent=2)

    with open(file_path, 'r') as f:
        code = f.read()

    suggestions = []

    if lang.name == "python":
        if 'print(' in code:
            suggestions.append({
                "type": "best_practice",
                "message": "Use logging instead of print()",
                "reason": "Logging is more flexible for production",
                "priority": "medium"
            })

        if 'import *' in code:
            suggestions.append({
                "type": "best_practice",
                "message": "Avoid wildcard imports",
                "reason": "Makes code unclear and causes naming conflicts",
                "priority": "high"
            })

    return json.dumps({
        "file": file_path,
        "language": lang.name,
        "focus": focus,
        "suggestions": suggestions
    }, indent=2)


def explain_code_impl(file_path: str, line_start: Optional[int], line_end: Optional[int], detail_level: str) -> str:
    """Implementation of explain_code"""
    return json.dumps({"message": "Feature coming soon"}, indent=2)


def generate_tests_impl(file_path: str, test_framework: str, coverage_target: str) -> str:
    """Implementation of generate_tests"""
    return json.dumps({"message": "Feature coming soon"}, indent=2)


def refactor_code_impl(file_path: str, refactor_type: str, target: str, preview: bool) -> str:
    """Implementation of refactor_code"""
    return json.dumps({"message": "Feature coming soon"}, indent=2)