"""
LLM Backend Manager
Supports both Ollama and GGUF with unified model registry
"""

import os
import json
from typing import Optional, Dict, List
from pathlib import Path
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

GGUF_MODELS_FILE = "gguf_models.json"


class LLMBackendManager:
    """Factory for creating LLM instances"""

    @staticmethod
    def get_backend_type() -> str:
        """Get current backend from environment"""
        return os.getenv("LLM_BACKEND", "ollama").lower()

    @staticmethod
    def create_llm(model_name: str, temperature: float = 0, **kwargs) -> BaseChatModel:
        """
        Create LLM instance - auto-detects backend

        Args:
            model_name: Model name (Ollama) or alias (GGUF)
            temperature: Sampling temperature
        """
        backend = LLMBackendManager.get_backend_type()

        if backend == "ollama":
            return ChatOllama(model=model_name, temperature=temperature, **kwargs)

        elif backend == "gguf":
            try:
                from langchain_community.chat_models import ChatLlamaCpp
            except ImportError:
                raise ImportError("Install llama-cpp-python: pip install llama-cpp-python")

            # Get model path from registry
            models = GGUFModelRegistry.load_models()
            if model_name not in models:
                raise ValueError(f"GGUF model '{model_name}' not in registry")

            model_path = models[model_name]["path"]
            if not Path(model_path).exists():
                raise FileNotFoundError(f"GGUF file not found: {model_path}")

            n_gpu_layers = int(os.getenv("GGUF_GPU_LAYERS", "-1"))
            n_ctx = int(os.getenv("GGUF_CONTEXT_SIZE", "4096"))

            print(f"🔧 Loading GGUF: {Path(model_path).name}")
            print(f"   GPU layers: {n_gpu_layers}, Context: {n_ctx}")

            return ChatLlamaCpp(
                model_path=model_path,
                temperature=temperature,
                n_gpu_layers=n_gpu_layers,
                n_ctx=n_ctx,
                verbose=False
            )

        else:
            raise ValueError(f"Unknown backend: {backend}")


class GGUFModelRegistry:
    """Manages GGUF model registry"""

    @staticmethod
    def load_models() -> Dict[str, dict]:
        if not os.path.exists(GGUF_MODELS_FILE):
            return {}
        try:
            with open(GGUF_MODELS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}

    @staticmethod
    def save_models(models: Dict[str, dict]):
        with open(GGUF_MODELS_FILE, 'w') as f:
            json.dump(models, f, indent=2)

    @staticmethod
    def add_model(alias: str, path: str, description: str = ""):
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if path_obj.suffix != ".gguf":
            raise ValueError("File must have .gguf extension")

        models = GGUFModelRegistry.load_models()
        models[alias] = {
            "path": str(path_obj.absolute()),
            "description": description,
            "size_mb": round(path_obj.stat().st_size / (1024 * 1024), 1)
        }
        GGUFModelRegistry.save_models(models)
        print(f"✅ Added GGUF model: {alias} ({models[alias]['size_mb']} MB)")

    @staticmethod
    def remove_model(alias: str):
        models = GGUFModelRegistry.load_models()
        if alias in models:
            del models[alias]
            GGUFModelRegistry.save_models(models)
            print(f"✅ Removed: {alias}")
        else:
            print(f"❌ Model not found: {alias}")

    @staticmethod
    def list_models() -> List[str]:
        return list(GGUFModelRegistry.load_models().keys())

    @staticmethod
    def get_model_info(alias: str) -> Optional[dict]:
        return GGUFModelRegistry.load_models().get(alias)