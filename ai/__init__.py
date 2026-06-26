"""
Módulo de IA local usando Ollama.
Fornece análise de padrões de roleta com LLM (llama3.1:8b por padrão).
"""

from .ollama_agent import OllamaAnalyst, AIResponse

__all__ = ["OllamaAnalyst", "AIResponse"]
