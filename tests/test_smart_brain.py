import sys
import os
sys.path.append(os.getcwd())
import unittest
import shutil
import json
from ai.smart_brain import CroupierSignatureTracker, MesaQLearning, SessionMemoryRAG, SmartBrain, WHEEL_LAYOUT


class TestSmartBrain(unittest.TestCase):
    def setUp(self):
        # Cria diretório de testes temporário se necessário
        os.makedirs("data/test_runs", exist_ok=True)
        self.q_path = "data/test_runs/q_learning_weights.json"
        self.rag_path = "data/test_runs/session_memory_rag.json"

    def tearDown(self):
        # Remove arquivos de teste
        if os.path.exists("data/test_runs"):
            shutil.rmtree("data/test_runs")

    def test_croupier_tracker_no_data(self):
        tracker = CroupierSignatureTracker()
        mean, std = tracker.get_croupier_signature()
        self.assertIsNone(mean)
        self.assertIsNone(std)
        self.assertEqual(tracker.predict_target_sector(0), [])

    def test_croupier_tracker_consistent_throws(self):
        # Simula lançamentos com espaçamento exatamente constante de 5 posições no cilindro
        tracker = CroupierSignatureTracker()
        
        # Sequência no cilindro: WHEEL_LAYOUT[0], WHEEL_LAYOUT[5], WHEEL_LAYOUT[10]...
        # Índices: 0, 5, 10, 15, 20, 25, 30, 35, 3 (40%37), 8 (45%37), 13 (50%37)
        spins = [0, 21, 6, 30, 24, 14, 29, 3, 19, 17, 36]
        for spin in spins:
            tracker.add_spin(spin)

        mean_dist, std_dev = tracker.get_croupier_signature()
        self.assertIsNotNone(mean_dist)
        self.assertIsNotNone(std_dev)
        # O desvio padrão deve ser extremamente baixo (próximo de zero)
        self.assertTrue(std_dev < 1.0)
        
        # Previsão a partir do último número (36) - posição do 36 no cilindro é 13.
        # Próximo projetado é 13 + 5 = 18. WHEEL_LAYOUT[18] é 10.
        targets = tracker.predict_target_sector(36, radius=1)
        self.assertEqual(len(targets), 3) # radius 1 -> 3 números
        self.assertIn(10, targets)

    def test_q_learning_weights(self):
        q = MesaQLearning(file_path=self.q_path)
        strategy_id = 999
        
        # Peso inicial padrão deve ser 1.0
        self.assertEqual(q.get_weight(strategy_id), 1.0)
        
        # Registra acerto
        q.register_outcome(strategy_id, "green")
        self.assertEqual(q.get_weight(strategy_id), 1.05)
        
        # Registra mais acertos até o limite de 1.5
        for _ in range(20):
            q.register_outcome(strategy_id, "green")
        self.assertEqual(q.get_weight(strategy_id), 1.5)
        
        # Registra erro (penalidade de 0.15)
        q.register_outcome(strategy_id, "loss")
        self.assertEqual(q.get_weight(strategy_id), 1.35)

    def test_session_memory_rag_no_mock_data(self):
        # SPRINT 4: o RAG NÃO deve mais criar perfis inventados (mock) na
        # inicialização. Banco novo/vazio deve permanecer vazio até que
        # sessões reais sejam registradas — nunca misturar dado fake com
        # dado real no cálculo de confiança.
        rag = SessionMemoryRAG(file_path=self.rag_path)
        self.assertEqual(rag.sessions, [])

        # Sem nenhuma sessão real registrada, a consulta deve retornar a
        # assertividade neutra padrão (0.80), não um perfil inventado.
        history = [0, 1, 4, 10, 11, 14, 20, 21, 24, 30, 31, 34, 0, 1, 4]
        winrate = rag.query_similar_session_winrate(history)
        self.assertEqual(winrate, 0.80)

    def test_session_memory_rag_real_session_roundtrip(self):
        # Sem Ollama rodando neste ambiente de teste, a geração de embedding
        # deve falhar silenciosamente e cair no fallback heurístico
        # (vetor de 10 terminais + cosseno) SEM lançar exceção.
        rag = SessionMemoryRAG(file_path=self.rag_path)

        # Sessão real 1: dominância forte de terminais 0/1/4 (T0, T1, T4),
        # win rate real observado alto.
        history_a = [0, 1, 4, 10, 11, 14, 20, 21, 24, 30, 31, 34, 0, 1, 4]
        rag.save_current_session_profile(
            session_id="real_session_a",
            history=history_a,
            win_rate=0.90,
            strategies_used=["T0 e T1 com 1 vizinho"],
        )

        # Sessão real 2: distribuição uniforme (alta entropia), win rate
        # real observado baixo.
        history_b = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        rag.save_current_session_profile(
            session_id="real_session_b",
            history=history_b,
            win_rate=0.50,
            strategies_used=["T2 e T3"],
        )

        # Só dados reais persistidos, nada de mock misturado.
        self.assertEqual(len(rag.sessions), 2)
        for sess in rag.sessions:
            self.assertIn("session_text", sess)
            self.assertIn("embedding", sess)  # None aqui (sem Ollama local)

        # Consulta com histórico parecido com a sessão A (terminais 0/1/4
        # dominantes) deve recuperar o win rate real da sessão A (0.90),
        # não um valor inventado.
        query_history = [0, 1, 4, 0, 1, 4, 10, 11, 14, 20, 21, 24, 30, 31, 34]
        winrate, context_text = rag.query_similar_session_context(query_history)
        self.assertEqual(winrate, 0.90)
        # O texto retornado deve ser o contexto real da sessão (não um escalar)
        self.assertIsInstance(context_text, str)
        self.assertIn("giros", context_text)
        self.assertIn("Win rate real observado", context_text)

        # query_similar_session_winrate (compat) deve retornar o mesmo escalar
        winrate_only = rag.query_similar_session_winrate(query_history)
        self.assertEqual(winrate_only, 0.90)

    def test_session_memory_rag_persists_to_disk(self):
        rag = SessionMemoryRAG(file_path=self.rag_path)
        rag.save_current_session_profile(
            session_id="persisted_session",
            history=[0, 1, 4, 10, 11, 14, 20, 21, 24, 30, 31, 34, 0, 1, 4],
            win_rate=0.75,
        )

        self.assertTrue(os.path.exists(self.rag_path))
        with open(self.rag_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["session_id"], "persisted_session")
        self.assertIn("session_text", data[0])
        # Nenhum perfil mockado deve ter sido reintroduzido no arquivo.
        mock_ids = {
            "profile_stable_low_terminals",
            "profile_high_entropy_messy",
            "profile_cluster_geometric",
        }
        self.assertFalse(any(s["session_id"] in mock_ids for s in data))

    def test_smart_brain_singleton(self):
        sb1 = SmartBrain(profiles_path="data/test_runs/croupier_profiles.json")
        sb2 = SmartBrain(profiles_path="data/test_runs/croupier_profiles.json")
        self.assertIs(sb1, sb2)

    def test_kelly_fraction(self):
        sb = SmartBrain(profiles_path="data/test_runs/croupier_profiles.json")
        # 0% confiança -> Mínimo de 0.5%
        self.assertEqual(sb.calculate_kelly_fraction(0), 0.5)
        # 10% confiança -> Mínimo de 0.5%
        self.assertEqual(sb.calculate_kelly_fraction(10), 0.5)
        # 85% confiança -> Kelly proporcional (0.10 * f_star)
        k_85 = sb.calculate_kelly_fraction(85)
        self.assertTrue(0.5 <= k_85 <= 3.0)

    def test_multiple_croupier_tracking(self):
        sb = SmartBrain(profiles_path="data/test_runs/croupier_profiles.json")
        # Tracker do João
        t_joao = sb.get_croupier_tracker("Joao")
        t_joao.add_spin(36)
        
        # Tracker da Maria
        t_maria = sb.get_croupier_tracker("Maria")
        t_maria.add_spin(0)
        
        # Verifica independência do histórico
        self.assertEqual(t_joao.history, [36])
        self.assertEqual(t_maria.history, [0])
        
        # Salva perfis e verifica persistência
        sb.save_croupier_profiles()
        self.assertTrue(os.path.exists("data/test_runs/croupier_profiles.json"))


if __name__ == "__main__":
    unittest.main()
