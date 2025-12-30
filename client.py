import os
from openai import OpenAI
import asyncio
from mcp_use import MCPClient, MCPAgent

# 1. Groq (OpenAI-compatible) LLM client
llm = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],   # e.g., https://api.groq.com/openai/v1
)

# 2. Configure your MCP server (stdio)
client_config = {
    "mcpServers": {
        "local": {
            "command": "python",
            "args": ["server.py"],
            "env": {}
        }
    }
}

# 3. Create MCPClient from config
client = MCPClient.from_dict(client_config)

# 4. Create agent
agent = MCPAgent(
    llm=llm,
    client=client,
    max_steps=10
)

async def main():
    print("Agent ready. Type a prompt (or Ctrl+C to exit).")
    while True:
        query = input("\n> ")
        if not query.strip():
            continue
        # Run agent
        result = await agent.run(query, server_name="local")
        print("\n" + result)

if __name__ == "__main__":
    asyncio.run(main())
