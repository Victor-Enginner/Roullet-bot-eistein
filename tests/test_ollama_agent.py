"""
Teste de smoke do agente Ollama.
Roda um caso simulado e valida que o JSON de resposta é parseável.
"""

import sys
import os
import logging

# Permite rodar do diretório raiz do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_ai")

from ai.ollama_agent import OllamaAnalyst, get_analyst


def test_disabled_returns_none():
    """Se desabilitado, sempre retorna None."""
    analyst = OllamaAnalyst(enabled=False)
    result = analyst.analyze(
        history=[23, 7, 0, 12, 35, 23, 14, 2, 31, 0],
        base=23,
        strategy={"leitura": "teste", "entrada": "T2 e T3 com 1 vizinho", "cobertura": "T1"},
        stats={"directGreen": 3, "protectionGreen": 1, "loss": 2},
        analysis={
            "hot_numbers": [(23, 5), (7, 4), (0, 3)],
            "cold_numbers": [(15, 0), (16, 0)],
            "terminal_dominance": {2: 4, 3: 3, 0: 3},
            "frequency": {},
        },
    )
    assert result is None, "Desabilitado deveria retornar None"
    print("✅ test_disabled_returns_none: OK")


def test_is_available():
    """Verifica se Ollama está respondendo (ou não)."""
    analyst = OllamaAnalyst()
    available = analyst.is_available()
    print(f"{'✅' if available else '⚠️ '} Ollama disponível: {available}")
    if not available:
        print("   (Isso é OK se você ainda não iniciou o Ollama)")


def test_real_consultation():
    """Consulta real ao Ollama com dados fictícios."""
    analyst = OllamaAnalyst(enabled=True, timeout=30.0)

    if not analyst.is_available():
        print("⏭️  test_real_consultation: PULADO (Ollama indisponível)")
        return

    # Histórico fictício de 50 giros
    fake_history = [23, 7, 0, 12, 35, 23, 14, 2, 31, 0,
                    18, 29, 7, 28, 32, 15, 3, 24, 36, 11,
                    23, 5, 16, 27, 33, 1, 20, 8, 30, 22,
                    17, 4, 19, 9, 6, 34, 13, 21, 25, 10,
                    23, 7, 0, 12, 35, 23, 14, 2, 31, 0]

    print("\n🤖 Consultando Ollama (pode levar alguns segundos)...")
    result = analyst.analyze(
        history=fake_history,
        base=23,
        strategy={
            "leitura": "Terminal 3 ativo com conexão ao zero.",
            "entrada": "T2 e T3 com 1 vizinho",
            "cobertura": "T1 / T5",
        },
        stats={"directGreen": 3, "protectionGreen": 1, "loss": 2},
        analysis={
            "hot_numbers": [(23, 5), (7, 4), (0, 4), (2, 3), (12, 2)],
            "cold_numbers": [(15, 0), (16, 0), (25, 0)],
            "terminal_dominance": {2: 5, 3: 6, 0: 4, 7: 4},
            "frequency": {n: fake_history.count(n) for n in range(37)},
        },
    )

    if result is None:
        print("⚠️  Ollama retornou None (erro ou timeout)")
        return

    print("\n📊 Resposta da IA:")
    print(f"   should_enter: {result.should_enter}")
    print(f"   confidence:   {result.confidence}%")
    print(f"   risk_level:   {result.risk_level}")
    print(f"   reasoning:    {result.reasoning}")
    print(f"   alt_targets:  {result.alternative_targets}")
    assert 0 <= result.confidence <= 100, "Confiança fora do range 0-100"
    assert result.risk_level in ("low", "medium", "high"), "Risk level inválido"
    print("\n✅ test_real_consultation: OK")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DO AGENTE OLLAMA")
    print("=" * 60)
    test_disabled_returns_none()
    test_is_available()
    test_real_consultation()
    print("\n" + "=" * 60)
    print("Concluído.")
