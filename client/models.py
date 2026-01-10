"""
Models Module
Handles Ollama model listing, switching, and persistence
"""

import os
import subprocess

MODEL_STATE_FILE = "last_model.txt"


def get_available_models():
    """Get list of available Ollama models"""
    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
        lines = out.strip().split("\n")

        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])

        return models

    except Exception as e:
        print(f"❌ Could not list models: {e}")
        return []


def load_last_model():
    """Load the last used model from file"""
    if os.path.exists(MODEL_STATE_FILE):
        return open(MODEL_STATE_FILE).read().strip()
    return None


def save_last_model(model_name):
    """Save the current model to file"""
    with open(MODEL_STATE_FILE, "w") as f:
        f.write(model_name)


async def switch_model(model_name, tools, logger, create_agent_fn):
    """Switch to a different Ollama model"""
    from langchain_ollama import ChatOllama

    available = get_available_models()

    if model_name not in available:
        print(f"❌ Model '{model_name}' is not installed.")
        print("📦 Available models:")
        for m in available:
            print(f" - {m}")
        print()
        return None

    logger.info(f"🔄 Switching model to: {model_name}")

    new_llm = ChatOllama(model=model_name, temperature=0)
    llm_with_tools = new_llm.bind_tools(tools)

    agent = create_agent_fn(llm_with_tools, tools)

    save_last_model(model_name)

    logger.info(f"✅ Model switched to {model_name}")
    return agent


def list_models_formatted():
    """Print formatted list of available models"""
    import json

    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
        lines = out.strip().split("\n")
        rows = lines[1:]

        parsed = []
        for line in rows:
            line_parts = line.split()
            if len(line_parts) < 4:
                continue

            name = line_parts[0]
            model_id = line_parts[1]
            size = line_parts[2]
            modified = " ".join(line_parts[3:])

            parsed.append({
                "name": name,
                "id": model_id,
                "size": size,
                "modified": modified
            })

        json_str = json.dumps(parsed)
        models = json.loads(json_str)

        print("\n📦 Available models:")
        for m in models:
            print(f" - {m['name']}")
        print()

    except Exception as e:
        print(f"❌ Could not list models: {e}")