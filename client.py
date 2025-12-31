import asyncio
import os
import logging

from langchain_openai import ChatOpenAI
from mcp_use.client.client import MCPClient
from mcp_use.agents.mcpagent import MCPAgent
from pathlib import Path

async def main():
    # 1️⃣ LangChain Chat Model (OpenAI)
    llm = ChatOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ.get("OPENAI_MODEL", "llama-3.1-8b-instant"),
        temperature=0
    )

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
                "command": str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
                "args": [str(PROJECT_ROOT / "server.py")],
                "cwd": str(PROJECT_ROOT),
                "env": {
                    "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
                    "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
                }
            }
        }
    })

    # 3️⃣ MCP Agent
    agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=10
    )

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

            result = await agent.run(query)
            print("\n" + result + "\n")

        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break

        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
