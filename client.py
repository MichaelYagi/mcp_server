import asyncio
import os
import logging
import requests

from mcp_use.client.client import MCPClient
from mcp_use.agents.mcpagent import MCPAgent
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except:
        return None


async def main():
    load_dotenv()

    PROJECT_ROOT = Path(__file__).resolve().parent
    LOG_DIR = Path(str(PROJECT_ROOT / "logs"))
    LOG_DIR.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "mcp-client.log", encoding="utf-8"),
            logging.StreamHandler()
        ],
    )

    # 2️⃣ MCP Server config
    client = MCPClient.from_dict({
        "mcpServers": {
            "local": {
                "command": get_venv_python(PROJECT_ROOT),
                "args": [str(PROJECT_ROOT / "server.py")],
                "cwd": str(PROJECT_ROOT),
                "env": {
                    "CLIENT_IP": get_public_ip()
                }
            }
        }
    })

    # 3️⃣ MCP Agent
    SYSTEM_PROMPT = Path(str(PROJECT_ROOT / "prompts/tool_usage_guide.md")).read_text()
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    llm = ChatOllama(
        model=model_name,
        temperature=0
    )

    agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=10,
        system_prompt=SYSTEM_PROMPT
    )

    agent.debug = True

    await agent.initialize()

    tools = agent._tools

    print("\n🛠 MCP tools visible to client:")
    for t in tools:
        print(f"- {t.name}: {t.description}")

    print("\n✅ MCP Agent ready. Type a prompt (Ctrl+C to exit).\n")

    while True:
        try:
            query = input("> ").strip()
            if not query:
                continue

            # result = await agent.run(query)
            result = await agent.run(query)
            print("\n" + result + "\n")

        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break

        except Exception as e:
            print(f"\n❌ Error: {e}\n")

def get_venv_python(project_root: Path) -> str:
    """Return the correct Python executable path by checking known locations."""

    # Linux/macOS first (WSL uses this)
    candidates = [
        project_root / ".venv" / "bin" / "python",          # WSL/Linux/macOS
        project_root / ".venv-wsl" / "bin" / "python",      # Legacy WSL
        project_root / ".venv" / "Scripts" / "python.exe",  # Windows
        project_root / ".venv" / "Scripts" / "python",      # Windows alt
    ]

    for path in candidates:
        if path.exists():
            return str(path)

    raise FileNotFoundError("No valid Python executable found in expected venv locations.")

if __name__ == "__main__":
    asyncio.run(main())
