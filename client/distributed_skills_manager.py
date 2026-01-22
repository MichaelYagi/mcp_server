"""
Distributed Skills Manager for MCP Client
Discovers and aggregates skills from all connected MCP servers
NOW USING SHARED QUERY PATTERNS
"""

import json
import logging
from typing import Dict, List, Optional
from mcp_use.client.client import MCPClient

# Import shared patterns
from client.query_patterns import needs_tools, is_general_knowledge


class DistributedSkillsManager:
    """
    Manages skills distributed across multiple MCP servers.
    Each server advertises its own skills via list_skills/read_skill tools.
    """

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger("distributed_skills")
        self.skills_by_server: Dict[str, List[dict]] = {}
        self.all_skills: Dict[str, dict] = {}  # skill_name -> {server, metadata}

    async def discover_all_skills(self):
        """
        Discover skills from all connected MCP servers.
        Calls list_skills() on each server that has it.
        """
        self.logger.info("🔍 Discovering skills from all servers...")

        # Get all available tools across all servers
        all_tools = []
        for server_name, session in self.mcp_client.sessions.items():
            try:
                tools = await session.list_tools()
                for tool in tools:
                    all_tools.append({
                        "server": server_name,
                        "name": tool.name,
                        "description": tool.description
                    })
            except Exception as e:
                self.logger.error(f"❌ Failed to list tools from {server_name}: {e}")

        # Find servers that have list_skills tool
        servers_with_skills = [
            t["server"] for t in all_tools
            if t["name"] == "list_skills"
        ]

        if not servers_with_skills:
            self.logger.warning("⚠️  No servers with skills support found")
            return

        self.logger.info(f"📚 Found {len(servers_with_skills)} server(s) with skills support")

        # Discover skills from each server
        for server_name in servers_with_skills:
            try:
                await self._discover_server_skills(server_name)
            except Exception as e:
                self.logger.error(f"❌ Failed to discover skills from {server_name}: {e}")

        # Log summary
        total_skills = sum(len(skills) for skills in self.skills_by_server.values())
        self.logger.info(f"✓ Discovered {total_skills} skill(s) across {len(self.skills_by_server)} server(s)")

        for server_name, skills in self.skills_by_server.items():
            self.logger.info(f"   {server_name}: {len(skills)} skill(s)")
            for skill in skills:
                self.logger.info(f"      - {skill['name']}: {skill['description'][:60]}...")

    async def _discover_server_skills(self, server_name: str):
        """Discover skills from a specific server"""
        session = self.mcp_client.sessions.get(server_name)
        if not session:
            return

        try:
            # Call list_skills on the server
            result = await session.call_tool("list_skills", {})

            # Parse the response
            data = json.loads(result.content[0].text)
            skills = data.get("skills", [])

            self.skills_by_server[server_name] = skills

            # Index skills by name for quick lookup
            for skill in skills:
                skill_name = skill["name"]
                self.all_skills[skill_name] = {
                    "server": server_name,
                    **skill
                }

        except Exception as e:
            self.logger.error(f"Failed to get skills from {server_name}: {e}")

    async def read_skill(self, skill_name: str) -> Optional[str]:
        """
        Read full skill content from the appropriate server.

        Args:
            skill_name: Name of the skill to read

        Returns:
            Skill content as JSON string, or None if not found
        """
        skill_info = self.all_skills.get(skill_name)
        if not skill_info:
            self.logger.warning(f"⚠️  Skill '{skill_name}' not found")
            return None

        server_name = skill_info["server"]
        session = self.mcp_client.sessions.get(server_name)

        if not session:
            self.logger.error(f"❌ Server '{server_name}' not connected")
            return None

        try:
            result = await session.call_tool("read_skill", {"skill_name": skill_name})
            return result.content[0].text
        except Exception as e:
            self.logger.error(f"❌ Failed to read skill '{skill_name}': {e}")
            return None

    def get_skills_summary(self) -> str:
        """
        Get a summary of all available skills for system prompt injection.
        """
        if not self.all_skills:
            return ""

        summary = "\n# AVAILABLE SKILLS\n\n"
        summary += "Skills are distributed across your MCP servers. "
        summary += "Use list_skills() to see all, or read_skill('name') for details.\n\n"

        # Group by server
        for server_name, skills in self.skills_by_server.items():
            summary += f"## {server_name}\n\n"
            for skill in skills:
                summary += f"- **{skill['name']}**: {skill['description']}\n"
                if skill.get('tools'):
                    summary += f"  - Tools: {', '.join(skill['tools'])}\n"
            summary += "\n"

        return summary

    def find_relevant_skills(self, user_query: str, max_skills: int = 3) -> List[dict]:
        """
        Find skills relevant to user query using keyword matching.

        Args:
            user_query: User's query text
            max_skills: Maximum number of skills to return

        Returns:
            List of skill metadata dicts with 'name', 'server', 'description'
        """
        query_lower = user_query.lower()
        query_words = set(query_lower.split())

        scores = []
        for skill_name, skill_info in self.all_skills.items():
            # Score based on keyword matches
            desc_lower = skill_info['description'].lower()
            desc_words = set(desc_lower.split())

            # Count matches (require at least 2 word matches to avoid noise)
            matches = len(query_words & desc_words)

            # Boost if skill name appears in query
            if skill_name.lower() in query_lower:
                matches += 5

            # Boost if tool names match
            for tool in skill_info.get('tools', []):
                if tool.lower() in query_lower:
                    matches += 3

            # Only include skills with meaningful matches (threshold of 2)
            if matches >= 2:
                scores.append((matches, skill_info))

        # Sort by score and return top results
        scores.sort(key=lambda x: x[0], reverse=True)
        return [info for score, info in scores[:max_skills]]

    def list_all_skills(self) -> List[dict]:
        """Get list of all skills with metadata"""
        return list(self.all_skills.values())


async def inject_relevant_skills_into_messages(
        skills_manager: DistributedSkillsManager,
        user_query: str,
        messages: list,
        logger: logging.Logger
) -> list:
    """
    Inject relevant skills into the message history.
    NOW USING SHARED REGEX PATTERNS FOR INTELLIGENCE

    Args:
        skills_manager: The distributed skills manager
        user_query: Current user query
        messages: Current message history
        logger: Logger instance

    Returns:
        Modified message list with skills injected into system message
    """

    # ═══════════════════════════════════════════════════════════
    # USE SHARED PATTERN MATCHING (same as LangGraph)
    # ═══════════════════════════════════════════════════════════

    # Check if this is a general knowledge query (no tools needed)
    if is_general_knowledge(user_query):
        logger.info("📚 General knowledge query detected - skipping skill injection")
        return messages

    # Check if query needs tools at all
    if not needs_tools(user_query):
        logger.info("📚 Query doesn't need tools - skipping skill injection")
        return messages

    # ═══════════════════════════════════════════════════════════
    # Query needs tools - find relevant skills
    # ═══════════════════════════════════════════════════════════

    relevant = skills_manager.find_relevant_skills(user_query, max_skills=2)

    if not relevant:
        logger.info("📚 No relevant skills found for this query")
        return messages

    logger.info(f"📚 Found {len(relevant)} relevant skill(s) for query")

    # Read full content of relevant skills
    skills_content = "\n\n# RELEVANT SKILLS FOR THIS QUERY\n\n"

    for skill_info in relevant:
        skill_name = skill_info['name']
        logger.info(f"   - Loading: {skill_name} (from {skill_info['server']})")

        try:
            content = await skills_manager.read_skill(skill_name)
            if content:
                data = json.loads(content)
                skills_content += f"## {skill_name}\n\n"
                skills_content += f"{data['content']}\n\n"
        except Exception as e:
            logger.error(f"❌ Failed to load skill '{skill_name}': {e}")

    # Inject into system message
    if messages and hasattr(messages[0], 'type') and messages[0].type == "system":
        # Append to existing system message
        messages[0].content = messages[0].content + skills_content
    else:
        # Create new system message
        from langchain_core.messages import SystemMessage
        messages.insert(0, SystemMessage(content=skills_content))

    return messages