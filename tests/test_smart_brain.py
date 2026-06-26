import sys
import os
sys.path.append(os.getcwd())
import unittest
import shutil
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

    def test_session_memory_rag(self):
        rag = SessionMemoryRAG(file_path=self.rag_path)
        
        # Banco padrão criado na inicialização
        self.assertTrue(len(rag.sessions) > 0)
        
        # Testa consulta com histórico fictício de terminais baixos
        # Histórico com muitos números terminados em 0, 1 e 4 (T0, T1, T4)
        history = [0, 1, 4, 10, 11, 14, 20, 21, 24, 30, 31, 34, 0, 1, 4]
        winrate = rag.query_similar_session_winrate(history)
        
        # Deve casar com o perfil "profile_stable_low_terminals"
        self.assertTrue(winrate > 0.80)

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
