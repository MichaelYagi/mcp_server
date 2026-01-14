"""
Multi-Agent Execution System (Updated for LangChain 1.2.0)
Uses LangChain create_agent for tool execution
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.agents import create_agent

# Import stop signal
try:
    from client.stop_signal import is_stop_requested, clear_stop
except ImportError:
    # Fallback if stop_signal not available
    def is_stop_requested():
        return False
    def clear_stop():
        pass


class AgentRole(Enum):
    """Defines different agent specializations"""
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYST = "analyst"
    WRITER = "writer"
    PLANNER = "planner"
    PLEX_INGESTER = "plex_ingester"


@dataclass
class AgentTask:
    """Represents a task for an agent"""
    task_id: str
    role: AgentRole
    description: str
    context: Dict[str, Any]
    dependencies: List[str] = None
    result: Optional[Any] = None
    status: str = "pending"
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents with PROPER tool execution
    Updated for LangChain 1.2.0
    """

    def __init__(self, base_llm, tools, logger: logging.Logger):
        self.base_llm = base_llm

        # Handle tools as either list or dict
        if isinstance(tools, dict):
            self.tools = list(tools.values())
        else:
            self.tools = tools

        self.logger = logger

        # Create specialized agent executors
        self.agent_executors = self._create_agent_executors()

        # Task management
        self.tasks: Dict[str, AgentTask] = {}
        self.task_results: Dict[str, Any] = {}

    def _create_agent_executors(self) -> Dict[AgentRole, Dict]:
        """Create agent executors with proper tool calling"""

        executors = {}

        # System prompts for each role
        system_prompts = {
            AgentRole.ORCHESTRATOR: """You are an Orchestrator Agent coordinating multiple specialized agents.
When given a task, create a detailed execution plan with subtasks.
Respond ONLY with JSON in this format:
{{
  "subtasks": [
    {{
      "id": "task_1",
      "role": "researcher",
      "description": "Detailed task description",
      "dependencies": []
    }}
  ]
}}

Available roles: researcher, coder, analyst, writer, planner, plex_ingester

If this is a simple task that doesn't need multiple agents, respond with:
{{"subtasks": []}}""",

            AgentRole.RESEARCHER: """You are a Researcher Agent focused on gathering accurate information.
ALWAYS use your available tools to search for information.
Never make up information - use tools to find real data.""",

            AgentRole.CODER: """You are a Coder Agent focused on writing quality code.
Use tools when you need to look up code examples or documentation.""",

            AgentRole.ANALYST: """You are an Analyst Agent focused on data analysis and insights.
Use tools to gather data before analyzing.""",

            AgentRole.WRITER: """You are a Writer Agent focused on clear communication.
Use tools to gather information before writing.""",

            AgentRole.PLANNER: """You are a Planner Agent focused on organizing tasks.
Use todo tools to manage and create tasks.""",

            AgentRole.PLEX_INGESTER: """You are a Plex Ingester Agent.
FOR SIMPLE INGESTION (e.g., "Ingest 2 items"):
- Use: plex_ingest_batch(limit=2) - Does everything in one call ✅
FOR COMPLEX WORKFLOWS (e.g., "Find items, then..."):
- Step 1: plex_find_unprocessed(limit=N)
- Step 2: Wait for results
- Step 3: Use real IDs from step 1 in plex_ingest_items
CRITICAL: Never make up item IDs! Only use IDs returned by plex_find_unprocessed."""
        }

        for role in AgentRole:
            # Get tools for this role
            role_tools = self._get_tools_for_role(role)

            if not role_tools and role != AgentRole.ORCHESTRATOR:
                # No tools, store None
                executors[role] = None
                self.logger.info(f"✅ Created {role.value} agent (no tools)")
                continue

            # Create agent with LangChain 1.2.0 API
            try:
                agent = create_agent(
                    self.base_llm,
                    role_tools
                )

                # Store both agent and system prompt
                executors[role] = {
                    "agent": agent,
                    "system_prompt": system_prompts.get(role, "You are a helpful AI assistant."),
                    "tools": role_tools
                }

                self.logger.info(f"✅ Created {role.value} agent with {len(role_tools)} tools")

            except Exception as e:
                self.logger.error(f"❌ Failed to create {role.value} agent: {e}")
                executors[role] = None

        return executors

    def _get_tools_for_role(self, role: AgentRole) -> List:
        """Get appropriate tools for each agent role"""

        role_tools = {
            AgentRole.ORCHESTRATOR: [],

            AgentRole.RESEARCHER: [
                "rag_search_tool", "search_entries", "search_semantic",
                "semantic_media_search_text", "get_weather_tool"
            ],

            AgentRole.CODER: [
                "rag_search_tool",
            ],

            AgentRole.ANALYST: [
                "rag_search_tool", "search_entries",
            ],

            AgentRole.WRITER: [
                "rag_search_tool", "search_entries",
            ],

            AgentRole.PLANNER: [
                "list_todo_items", "add_todo_item",
            ],

            # Plex Ingester with granular tools
            AgentRole.PLEX_INGESTER: [
                # Granular tools for multi-agent orchestration
                "plex_find_unprocessed",  # STEP 1: Find items
                "plex_ingest_items",  # STEP 2: Batch parallel (recommended)
                "plex_ingest_single",  # STEP 3: Single item (max parallelization)
                "plex_get_stats",  # STEP 4: Get statistics

                # Original all-in-one (for simple queries)
                "plex_ingest_batch",  # Original combined tool

                # Supporting tools
                "rag_search_tool",  # Check what's already ingested
            ],
        }

        tool_names = role_tools.get(role, [])

        # Filter available tools
        available_tools = []
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name in tool_names:
                available_tools.append(tool)

        return available_tools

    async def execute(self, user_request: str) -> str:
        """Main entry point for multi-agent execution"""

        self.logger.info(f"🎭 Multi-agent execution started: {user_request}")
        start_time = time.time()

        try:
            # Step 1: Create execution plan
            plan = await self._create_execution_plan(user_request)

            if not plan:
                self.logger.info("📊 Simple query detected, falling back to single agent")
                return await self._fallback_single_agent(user_request)

            # Step 2: Execute tasks
            results = await self._execute_tasks(plan)

            # Step 3: Aggregate results
            final_response = await self._aggregate_results(user_request, results)

            duration = time.time() - start_time
            self.logger.info(f"✅ Multi-agent execution completed in {duration:.2f}s")

            return final_response

        except Exception as e:
            self.logger.error(f"❌ Multi-agent execution failed: {e}, falling back to single agent")
            import traceback
            traceback.print_exc()
            return await self._fallback_single_agent(user_request)

    async def _create_execution_plan(self, user_request: str) -> Optional[List[AgentTask]]:
        """Use orchestrator to create execution plan"""

        self.logger.info("📋 Creating execution plan...")

        # Orchestrator has no tools, use base LLM
        planning_prompt = f"""Given this user request: "{user_request}"

Create an execution plan by breaking it into subtasks.

Respond ONLY with JSON in this format:
{{
  "subtasks": [
    {{
      "id": "task_1",
      "role": "researcher",
      "description": "Detailed task description",
      "dependencies": []
    }}
  ]
}}

Available roles: researcher, coder, analyst, writer, planner, plex_ingester

If this is a simple task that doesn't need multiple agents, respond with:
{{"subtasks": []}}"""

        try:
            response = await self.base_llm.ainvoke([
                SystemMessage(content="You are an Orchestrator Agent coordinating multiple specialized agents."),
                HumanMessage(content=planning_prompt)
            ])

            # Parse JSON response
            import json
            import re

            content = response.content.strip()

            # Extract JSON if wrapped in markdown
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

            plan_data = json.loads(content)
            subtasks = plan_data.get("subtasks", [])

            if not subtasks:
                self.logger.info("📋 Simple task, using single agent")
                return None

            # Convert to AgentTask objects
            tasks = []
            for i, subtask in enumerate(subtasks):
                role_str = subtask.get("role", "researcher")
                try:
                    role = AgentRole(role_str)
                except ValueError:
                    self.logger.warning(f"⚠️  Unknown role '{role_str}', defaulting to researcher")
                    role = AgentRole.RESEARCHER

                task = AgentTask(
                    task_id=subtask.get("id", f"task_{i}"),
                    role=role,
                    description=subtask.get("description", ""),
                    context={"user_request": user_request},
                    dependencies=subtask.get("dependencies", [])
                )
                tasks.append(task)
                self.tasks[task.task_id] = task

            self.logger.info(f"📋 Created plan with {len(tasks)} subtasks")
            for task in tasks:
                self.logger.info(f"  - {task.task_id}: {task.role.value} - {task.description[:50]}...")

            return tasks

        except Exception as e:
            self.logger.error(f"❌ Failed to create plan: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _execute_tasks(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """Execute tasks respecting dependencies"""

        self.logger.info(f"⚙️ Executing {len(tasks)} tasks...")

        completed = set()
        results = {}

        while len(completed) < len(tasks):
            # CHECK STOP SIGNAL
            if is_stop_requested():
                self.logger.warning(f"🛑 Multi-agent execution stopped by user after {len(completed)}/{len(tasks)} tasks")
                results["_stopped"] = True
                results["_stopped_message"] = f"Stopped after completing {len(completed)} of {len(tasks)} tasks"
                break

            ready_tasks = [
                task for task in tasks
                if task.task_id not in completed
                and all(dep in completed for dep in task.dependencies)
            ]

            if not ready_tasks:
                self.logger.error("❌ Dependency deadlock detected")
                break

            self.logger.info(f"⚙️ Executing {len(ready_tasks)} parallel tasks...")

            task_coroutines = [
                self._execute_single_task(task, results)
                for task in ready_tasks
            ]

            task_results = await asyncio.gather(*task_coroutines, return_exceptions=True)

            for task, result in zip(ready_tasks, task_results):
                if isinstance(result, Exception):
                    self.logger.error(f"❌ Task {task.task_id} failed: {result}")
                    results[task.task_id] = f"Error: {str(result)}"
                else:
                    results[task.task_id] = result
                    self.logger.info(f"✅ Task {task.task_id} completed")

                completed.add(task.task_id)

        return results

    async def _execute_single_task(self, task: AgentTask, previous_results: Dict) -> str:
        """Execute a single agent task WITH TOOL EXECUTION"""

        task.status = "running"
        task.start_time = time.time()

        self.logger.info(f"🤖 {task.role.value} executing: {task.description[:50]}...")

        try:
            agent_info = self.agent_executors.get(task.role)

            # Build context from previous results
            context_info = ""
            for dep_id in task.dependencies:
                if dep_id in previous_results:
                    context_info += f"\n\nResult from {dep_id}:\n{previous_results[dep_id]}"

            # Create input for agent
            task_input = f"""Task: {task.description}

User's original request: {task.context.get('user_request', '')}
{context_info}

Complete this task using your available tools."""

            # Execute with tools
            if agent_info:
                agent = agent_info["agent"]
                system_prompt = agent_info["system_prompt"]

                self.logger.info(f"🔧 Running {task.role.value} with tool execution enabled...")

                # Build messages with system prompt
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=task_input)
                ]

                # Invoke agent with messages
                result = await agent.ainvoke({"messages": messages})

                # Extract output from last message
                last_message = result["messages"][-1]
                output = last_message.content if hasattr(last_message, 'content') else str(last_message)

            else:
                # No tools, use base LLM
                self.logger.info(f"💬 Running {task.role.value} without tools...")
                response = await self.base_llm.ainvoke([
                    SystemMessage(content=f"You are a {task.role.value} agent."),
                    HumanMessage(content=task_input)
                ])
                output = response.content

            task.result = output
            task.status = "completed"
            task.end_time = time.time()

            duration = task.end_time - task.start_time
            self.logger.info(f"✅ {task.role.value} completed in {duration:.2f}s")

            return output

        except Exception as e:
            task.status = "failed"
            task.end_time = time.time()
            self.logger.error(f"❌ Task {task.task_id} failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _aggregate_results(self, user_request: str, results: Dict[str, Any]) -> str:
        """Aggregate results from all agents"""

        self.logger.info("📊 Aggregating results...")

        results_summary = ""
        for task_id, result in results.items():
            task = self.tasks.get(task_id)
            if task:
                results_summary += f"\n\n### {task.role.value.title()} ({task_id}):\n{result}"

        aggregation_prompt = f"""User's original request: "{user_request}"

Results from specialized agents:
{results_summary}

Synthesize these results into a coherent, final response that directly answers the user's request.
Focus on clarity and completeness."""

        response = await self.base_llm.ainvoke([
            SystemMessage(content="You are synthesizing results from multiple agents. Create a clear, unified response."),
            HumanMessage(content=aggregation_prompt)
        ])

        return response.content

    async def _fallback_single_agent(self, user_request: str) -> str:
        """Fallback to single agent with tool execution"""

        self.logger.info("🔄 Using single-agent fallback mode")

        # Choose best agent based on keywords
        request_lower = user_request.lower()

        if "plex" in request_lower or "ingest" in request_lower or "subtitle" in request_lower:
            agent_role = AgentRole.PLEX_INGESTER
        elif "code" in request_lower:
            agent_role = AgentRole.CODER
        elif "analyze" in request_lower:
            agent_role = AgentRole.ANALYST
        elif "write" in request_lower:
            agent_role = AgentRole.WRITER
        elif "plan" in request_lower or "todo" in request_lower:
            agent_role = AgentRole.PLANNER
        else:
            agent_role = AgentRole.RESEARCHER

        self.logger.info(f"📌 Selected {agent_role.value} agent for single-agent execution")

        agent_info = self.agent_executors.get(agent_role)

        if agent_info:
            agent = agent_info["agent"]
            system_prompt = agent_info["system_prompt"]

            self.logger.info(f"🔧 Running {agent_role.value} with tool execution enabled...")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_request)
            ]

            result = await agent.ainvoke({"messages": messages})
            last_message = result["messages"][-1]
            return last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            # No tools, use base LLM
            response = await self.base_llm.ainvoke([
                SystemMessage(content=f"You are a {agent_role.value} agent."),
                HumanMessage(content=user_request)
            ])
            return response.content


async def should_use_multi_agent(user_request: str) -> bool:
    """Determine if a request should use multi-agent execution"""

    print(f"DEBUG: Checking multi-agent for: {user_request}")  # Debug output

    import logging
    logger = logging.getLogger("mcp_client")

    request_lower = user_request.lower()
    logger.info(f"🔍 Checking multi-agent for: {request_lower[:100]}")

    multi_step_indicators = [
        " and then ", " then ", " after that ", " next ",
        "first.*then", "research.*analyze", "find.*summarize",
        "gather.*create", "search.*write", "ingest.*and.*",
    ]

    import re
    for indicator in multi_step_indicators:
        if re.search(indicator, request_lower):
            logger.info(f"✅ Multi-agent triggered by: {indicator}")
            print(f"DEBUG: Multi-agent triggered by: {indicator}")
            return True

    complex_keywords = [
        "comprehensive", "detailed analysis", "full report",
        "research and", "analyze and", "compare and"
    ]

    if any(keyword in request_lower for keyword in complex_keywords):
        logger.info(f"✅ Multi-agent triggered by keyword")
        print(f"DEBUG: Multi-agent triggered by keyword")
        return True

    if len(user_request.split()) > 30:
        logger.info(f"✅ Multi-agent triggered by length: {len(user_request.split())} words")
        print(f"DEBUG: Multi-agent triggered by length")
        return True

    logger.info(f"❌ Multi-agent NOT triggered")
    print(f"DEBUG: Multi-agent NOT triggered")
    return False