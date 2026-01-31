"""
Context Tracker - Extracts context from session history for follow-up queries
"""

import re
from typing import Dict, Optional, List, Any
from langchain_core.messages import SystemMessage


class ContextTracker:
    """Tracks and injects context from session database"""

    def __init__(self, session_manager):
        self.session_manager = session_manager

        self.context_patterns = {
            "project": {
                "trigger_phrases": [
                    r"tech stack", r"project at", r"analyze.*project",
                    r"/mnt/c/", r"code", r"dependencies", r"node", r"packages"
                ],
                "extract_pattern": r"(/mnt/c/[^\s\"']+|/[a-z/]+/[^\s\"']+)",
                "key": "project_path"
            }
        }

    def extract_context_from_session(self, session_id: int, current_prompt: str) -> Dict[str, Any]:
        """Extract relevant context from session history"""
        if not session_id or not self.session_manager:
            return {}

        messages = self.session_manager.get_session_messages(session_id)
        if not messages:
            return {}

        recent_messages = messages[-20:]
        context = {}

        for context_type, config in self.context_patterns.items():
            is_relevant = any(
                re.search(pattern, current_prompt.lower())
                for pattern in config["trigger_phrases"]
            )

            if not is_relevant:
                continue

            for msg in reversed(recent_messages):
                text = msg.get("text", "")

                if any(re.search(p, text.lower()) for p in config["trigger_phrases"]):
                    match = re.search(config["extract_pattern"], text)
                    if match:
                        extracted_value = match.group(1)
                        # Remove trailing backticks, quotes, etc.
                        extracted_value = extracted_value.rstrip('`"\' ')
                        context[config["key"]] = extracted_value
                        context[f"{config['key']}_source"] = text
                        break

        return context

    def should_inject_context(self, prompt: str, context: Dict) -> bool:
        """Determine if context should be injected"""
        followup_patterns = [
            r'\b(those|that|them|it)\b',
            r'\bthe (project|code|packages?|dependencies)\b',
            r'\bwhat about\b',
            r'\btell me (more )?about\b',
            r'\bgo into (depth|detail)\b',
            r'\bwhat (do|are|is|does) (they|it|that|those)\b',
        ]

        has_followup = any(re.search(p, prompt.lower()) for p in followup_patterns)
        is_short_question = len(prompt.split()) <= 15 and '?' in prompt

        return (has_followup or is_short_question) and len(context) > 0

    def create_context_message(self, context: Dict) -> Optional[SystemMessage]:
        """Create system message with context"""
        if not context:
            return None

        if "project_path" in context:
            content = f"""⚠️ CONVERSATION CONTEXT ⚠️

📂 PROJECT: {context['project_path']}

When calling code analysis tools, use THIS EXACT PATH:
- get_project_dependencies(project_root="{context['project_path']}", ecosystem="node")

❌ WRONG: project_root="."
✅ CORRECT: project_root="{context['project_path']}"
"""
            return SystemMessage(content=content)

        return None


def integrate_context_tracking(session_manager, session_id, prompt, conversation_state, logger):
    """Main integration - call before running agent"""
    if not session_manager or not session_id:
        return False

    tracker = ContextTracker(session_manager)
    context = tracker.extract_context_from_session(session_id, prompt)

    if not context:
        return False

    logger.info(f"📚 Extracted context: {list(context.keys())}")

    if not tracker.should_inject_context(prompt, context):
        return False

    context_msg = tracker.create_context_message(context)
    if context_msg:
        conversation_state["messages"].append(context_msg)
        logger.info(f"✅ Context injected: project_path={context.get('project_path')}")
        return True

    return False