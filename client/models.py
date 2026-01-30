"""
Unified Model Management
Handles both Ollama and GGUF models with automatic backend switching
"""

import os
import subprocess
import logging
from client.llm_backend import LLMBackendManager, GGUFModelRegistry

logger = logging.getLogger(__name__)

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
            "size_mb": info.get("size_mb", 0) if info else 0,
            "path": info.get("path", "") if info else ""
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

    Returns:
        New agent instance, or None if switch failed
    """
    # Detect which backend this model needs
    target_backend = detect_backend(model_name)

    if not target_backend:
        logger.error(f"❌ Model '{model_name}' not found")
        print(f"\n❌ Model '{model_name}' not found in any backend\n")
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
                logger.error("❌ Ollama not running")
                print("\n❌ Ollama not running")
                print("   Start with: ollama serve\n")
                os.environ["LLM_BACKEND"] = current_backend  # Revert
                return None

    # Create new LLM with proper error handling
    logger.info(f"🔄 Switching to {target_backend}/{model_name}")

    try:
        # This will raise specific errors for invalid models
        new_llm = LLMBackendManager.create_llm(model_name, temperature=0)

    except ValueError as e:
        # Model not found or invalid configuration
        logger.error(f"❌ Configuration error: {e}")
        print(f"\n❌ {e}\n")
        os.environ["LLM_BACKEND"] = current_backend  # Revert
        return None

    except FileNotFoundError as e:
        # GGUF file missing
        logger.error(f"❌ File not found: {e}")
        print(f"\n❌ {e}\n")
        os.environ["LLM_BACKEND"] = current_backend  # Revert
        return None

    except RuntimeError as e:
        # GGUF file corrupted or invalid format
        logger.error(f"❌ Invalid model: {e}")
        print(f"\n❌ INVALID MODEL")
        print("=" * 70)
        print(str(e))
        print("=" * 70 + "\n")
        os.environ["LLM_BACKEND"] = current_backend  # Revert
        return None

    except Exception as e:
        # Unexpected error
        logger.error(f"❌ Unexpected error: {e}")
        print(f"\n❌ Failed to load model: {e}\n")
        os.environ["LLM_BACKEND"] = current_backend  # Revert
        return None

    # Bind tools and create agent
    try:
        llm_with_tools = new_llm.bind_tools(tools)
        agent = create_agent_fn(llm_with_tools, tools)
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}")
        print(f"\n❌ Failed to create agent: {e}\n")
        os.environ["LLM_BACKEND"] = current_backend  # Revert
        return None

    # Re-register A2A tools if needed
    if a2a_state and hasattr(a2a_state, "register_a2a_tools"):
        try:
            logger.info("🔌 Re-registering A2A tools")
            await a2a_state.register_a2a_tools(agent)
        except Exception as e:
            logger.warning(f"⚠️ Failed to re-register A2A tools: {e}")
            # Don't fail the switch, just warn

    # Success!
    save_last_model(model_name)
    logger.info(f"✅ Switched to {target_backend}/{model_name}")
    print(f"✅ Now using: {target_backend}/{model_name}")

    return agent


def print_all_models():
    """Print unified list of all available models"""
    all_models = get_all_models()

    if not all_models:
        print("\n📦 No models available")
        print("   Ollama: ollama pull <model>")
        print("   GGUF: :gguf add <alias> <path>")
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


async def reload_current_model(tools, logger, create_agent_fn, a2a_state=None):
    """
    Reload agent based on last_model.txt

    This ensures CLI and Web UI stay in sync by reading the authoritative state file.

    Returns:
        (agent, model_name) tuple, or (None, None) if failed
    """
    from client.llm_backend import LLMBackendManager

    model_name = load_last_model()

    if not model_name:
        logger.warning("⚠️ No last_model.txt found")
        return None, None

    backend = detect_backend(model_name)

    if not backend:
        logger.error(f"❌ Model '{model_name}' in last_model.txt not found")
        return None, None

    # Set backend
    os.environ["LLM_BACKEND"] = backend

    try:
        logger.info(f"🔄 Reloading model from last_model.txt: {backend}/{model_name}")

        # Create LLM
        llm = LLMBackendManager.create_llm(model_name, temperature=0)

        # Bind tools and create agent
        llm_with_tools = llm.bind_tools(tools)
        agent = create_agent_fn(llm_with_tools, tools)

        # Re-register A2A tools if needed
        if a2a_state and hasattr(a2a_state, "register_a2a_tools"):
            try:
                await a2a_state.register_a2a_tools(agent)
            except Exception as e:
                logger.warning(f"⚠️ Failed to re-register A2A tools: {e}")

        logger.info(f"✅ Reloaded: {backend}/{model_name}")
        return agent, model_name

    except Exception as e:
        logger.error(f"❌ Failed to reload model: {e}")
        return None, None