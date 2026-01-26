"""
Unified Model Management
Handles both Ollama and GGUF models with automatic backend switching
"""

import os
import subprocess
from client.llm_backend import LLMBackendManager, GGUFModelRegistry

MODEL_STATE_FILE = "last_model.txt"


def get_ollama_models():
    """Get list of Ollama models"""
    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
        lines = out.strip().split("\n")
        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except:
        return []


def get_available_models():
    """Get list of available Ollama models (legacy - for backwards compatibility)"""
    return get_ollama_models()


def list_models_formatted():
    """Print formatted list of available models (legacy - now shows all models)"""
    print_all_models()


def get_all_models():
    """
    Get ALL available models from both backends

    Returns list of dicts with keys: name, backend, size_mb (for GGUF)
    """
    all_models = []

    # Ollama models
    for model in get_ollama_models():
        all_models.append({
            "name": model,
            "backend": "ollama"
        })

    # GGUF models
    for model in GGUFModelRegistry.list_models():
        info = GGUFModelRegistry.get_model_info(model)
        all_models.append({
            "name": model,
            "backend": "gguf",
            "size_mb": info.get("size_mb", 0) if info else 0
        })

    return all_models


def detect_backend(model_name: str) -> str:
    """
    Detect which backend a model belongs to

    Returns: "ollama", "gguf", or None
    """
    if model_name in get_ollama_models():
        return "ollama"
    if model_name in GGUFModelRegistry.list_models():
        return "gguf"
    return None


def load_last_model():
    """Load last used model from file"""
    if os.path.exists(MODEL_STATE_FILE):
        return open(MODEL_STATE_FILE).read().strip()
    return None


def get_initial_backend():
    """
    Determine initial backend based on last used model

    Returns: "ollama" (default) or "gguf" based on last model
    """
    last_model = load_last_model()

    if last_model:
        backend = detect_backend(last_model)
        if backend:
            return backend

    # Default to ollama if no last model or model not found
    return "ollama"


def save_last_model(model_name):
    """Save current model to file"""
    with open(MODEL_STATE_FILE, "w") as f:
        f.write(model_name)


async def switch_model(model_name, tools, logger, create_agent_fn, a2a_state=None):
    """
    Switch to any model - automatically switches backend if needed

    This is the main entry point for model switching from CLI/WebUI
    """
    # Detect which backend this model needs
    target_backend = detect_backend(model_name)

    if not target_backend:
        print(f"❌ Model '{model_name}' not found")
        print_all_models()
        return None

    current_backend = LLMBackendManager.get_backend_type()

    # Switch backend if needed
    if target_backend != current_backend:
        logger.info(f"🔄 Switching backend: {current_backend} → {target_backend}")
        os.environ["LLM_BACKEND"] = target_backend

        # Check Ollama is running if switching to it
        if target_backend == "ollama":
            try:
                import httpx
                async with httpx.AsyncClient(timeout=1.0) as client:
                    await client.get("http://127.0.0.1:11434/api/tags")
            except:
                print("❌ Ollama not running. Start with: ollama serve")
                os.environ["LLM_BACKEND"] = current_backend  # Revert
                return None

    # Create new LLM
    logger.info(f"🔄 Switching to {target_backend}/{model_name}")

    try:
        new_llm = LLMBackendManager.create_llm(model_name, temperature=0)
        llm_with_tools = new_llm.bind_tools(tools)
        agent = create_agent_fn(llm_with_tools, tools)

        # Re-register A2A tools if needed
        if a2a_state and hasattr(a2a_state, "register_a2a_tools"):
            logger.info("🔌 Re-registering A2A tools")
            await a2a_state.register_a2a_tools(agent)

        save_last_model(model_name)
        logger.info(f"✅ Switched to {target_backend}/{model_name}")

        return agent

    except Exception as e:
        logger.error(f"❌ Model switch failed: {e}")
        os.environ["LLM_BACKEND"] = current_backend  # Revert backend
        return None


def print_all_models():
    """Print unified list of all available models"""
    all_models = get_all_models()

    if not all_models:
        print("\n📦 No models available")
        print("   Ollama: ollama pull <model>")
        print("   GGUF: :gguf add <path>")
        return

    # Group by backend
    ollama = [m for m in all_models if m["backend"] == "ollama"]
    gguf = [m for m in all_models if m["backend"] == "gguf"]

    current_backend = LLMBackendManager.get_backend_type()
    current_model = load_last_model()

    print("\n📦 Available Models")
    print(f"   Current: {current_backend}/{current_model}\n")

    if ollama:
        print("🔹 Ollama:")
        for m in ollama:
            marker = "→" if m["name"] == current_model else " "
            print(f"   {marker} {m['name']}")
        print()

    if gguf:
        print("🔹 GGUF (Local):")
        for m in gguf:
            marker = "→" if m["name"] == current_model else " "
            size = m.get("size_mb", 0)
            print(f"   {marker} {m['name']} ({size} MB)")
        print()

    print("💡 Switch: :model <name>")
    print("   (Backend switches automatically)\n")