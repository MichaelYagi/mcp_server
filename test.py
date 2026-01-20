"""
SIMPLE TEST - See what llama3.2:3b actually outputs for intent detection
Run this standalone to diagnose the issue
"""

import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage


async def test_intent_detection():
    # Your intent LLM
    intent_llm = ChatOllama(
        model="llama3.2:3b",
        temperature=0,
        num_predict=100
    )

    # Simulated tools (just names and descriptions)
    tools = [
        {"name": "get_location_tool", "desc": "Get user's current location from IP address"},
        {"name": "get_weather_tool", "desc": "Get weather for a location"},
        {"name": "add_todo_item", "desc": "Add item to todo list"},
        {"name": "list_todo_items", "desc": "List all todo items"},
    ]

    tools_text = "\n".join([f"- {t['name']}: {t['desc']}" for t in tools])

    test_queries = [
        "what's my location",
        "where am I",
        "what's the weather",
        "add milk to my list",
    ]

    for query in test_queries:
        print(f"\n{'=' * 70}")
        print(f"QUERY: {query}")
        print(f"{'=' * 70}")

        prompt = f"""Which tools would help with this request?

TOOLS:
{tools_text}

REQUEST: "{query}"

Return ONLY a JSON array like ["tool1", "tool2"] or []:
"""

        try:
            response = await intent_llm.ainvoke([
                SystemMessage(content="Return ONLY JSON arrays."),
                HumanMessage(content=prompt)
            ])

            print(f"RAW OUTPUT: '{response.content}'")
            print(f"LENGTH: {len(response.content)} chars")

            # Try to parse
            import json
            cleaned = response.content.strip().replace("```json", "").replace("```", "")

            if "[" in cleaned:
                start = cleaned.find("[")
                end = cleaned.rfind("]") + 1
                json_str = cleaned[start:end]
                print(f"EXTRACTED: '{json_str}'")

                try:
                    parsed = json.loads(json_str)
                    print(f"✅ SUCCESS: {parsed}")
                except json.JSONDecodeError as e:
                    print(f"❌ PARSE ERROR: {e}")
            else:
                print(f"❌ NO ARRAY FOUND")

        except Exception as e:
            print(f"❌ ERROR: {e}")

    print(f"\n{'=' * 70}")
    print("DIAGNOSIS:")
    print("If you see JSON arrays → llama3.2:3b is working")
    print("If you see explanations → Model is ignoring instructions")
    print("If you see errors → Need to upgrade model or fix prompt")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(test_intent_detection())