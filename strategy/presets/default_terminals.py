# Preset de Estratégias: Terminais Tradicionais
# Este arquivo serve como o "Cérebro" do Bot 1

ESTRATEGIAS = {
    0: {
        "leitura": "Zona do zero conexão de vizinhos.",
        "entrada": "8 vizinhos do número 26",
        "cobertura": "33, 5, 10, 14, 13, 8",
    },
    1: {
        "leitura": "Terminal dominante com continuidade.",
        "entrada": "T1 e T3 com 1 vizinho",
        "cobertura": "T4 / T7",
    },
    2: {
        "leitura": "Cluster técnico em terminal baixo.",
        "entrada": "T4 e T6 com 1 vizinho",
        "cobertura": "T5 / T2",
    },
    3: {
        "leitura": "Fluxo claro em terminais médios.",
        "entrada": "T3 e T6 com 1 vizinho",
        "cobertura": "T7 / T4",
    },
    4: {
        "leitura": "Terminal repetindo padrão anterior.",
        "entrada": "T4 e T1 com 1 vizinho",
        "cobertura": "T6 / T8",
    },
    5: {
        "leitura": "Terminal 5 puxando vizinhança.",
        "entrada": "T5 com 2 vizinhos",
        "cobertura": "T4 / T7",
    },
    6: {
        "leitura": "Cluster 6 3 9  ativo.",
        "entrada": "T4 e T3 com 1 vizinho",
        "cobertura": "T2 / T6 / T9",
    },
    7: {},
    8: {
        "leitura": "Região Tier com extensão lateral.",
        "entrada": "Cobrir Tier (7 vizinhos) e 32 (3 vizinhos)",
        "cobertura": "T1",
    },
    9: {},
    10: {
        "leitura": "Zero conectando terminais ativos.",
        "entrada": "T5 e T2 com 1 vizinho",
        "cobertura": "T0 / T7",
    },
    11: {},
    12: {
        "leitura": "Terminal 2.",
        "entrada": "T2 e T4 com 1 vizinho",
        "cobertura": "T1 / T5",
    },
    13: {
        "leitura": "Terminal dominante em repetição.",
        "entrada": "T1 e T3 com 1 vizinho",
        "cobertura": "T2 / T6",
    },
    14: {
        "leitura": "Terminal 4.",
        "entrada": "T4 e T1 com 1 vizinho",
        "cobertura": "T2 / T5",
    },
    15: {
        "leitura": "Terminal 5 conectado ao zero.",
        "entrada": "T5 e T0 com 1 vizinho",
        "cobertura": "T6 / T4",
    },
    16: {
        "leitura": "Terminal 6.",
        "entrada": "T3 e T9 com 1 vizinho",
        "cobertura": "T6 / T8",
    },
    17: {},
    18: {
        "leitura": "Terminal 8.",
        "entrada": "T8 e T5 com 1 vizinho",
        "cobertura": "T4 / T9",
    },
    19: {
        "leitura": "Terminal 9 puxando sequência.",
        "entrada": "T9 e T6 com 1 vizinho",
        "cobertura": "T8 / T3",
    },
    20: {
        "leitura": "Zero conectando terminais altos.",
        "entrada": "T0 e T5 com 1 vizinho",
        "cobertura": "T2 / T4",
    },
    21: {
        "leitura": "Espelhos em continuidade.",
        "entrada": "T2 e T3 com 1 vizinho",
        "cobertura": "12, 21, 13, 31, 23, 32",
    },
    22: {},
    23: {
        "leitura": "Zero conectado ao terminal 5.",
        "entrada": "T3 e T6 com 1 vizinho",
        "cobertura": "T2 / T4",
    },
    24: {
        "leitura": "CAVALO 47.",
        "entrada": "T4 e T1 com 1 vizinho",
        "cobertura": "T2 / T5",
    },
    25: {
        "leitura": "Terminal 5 isolado com vizinhança.",
        "entrada": "T5 e T0 com 1 vizinho",
        "cobertura": "T1 / T4",
    },
    26: {
        "leitura": "Terminal 6.",
        "entrada": "T6 e T3 com 1 vizinho",
        "cobertura": "T2 / T9",
    },
    27: {},
    28: {
        "leitura": "Sequência técnica ativa.",
        "entrada": "28 e 13 com 5 vizinhos",
        "cobertura": "T1 / T6",
    },
    29: {
        "leitura": "Terminal 9 conexão com o zero.",
        "entrada": "T9 e T0 com 1 vizinho",
        "cobertura": "T6 / T1",
    },
    30: {
        "leitura": "Terminal 0 fluxo lateral.",
        "entrada": "T3 e T6 com 1 vizinho",
        "cobertura": "T4 / T9",
    },
    31: {
        "leitura": "Continuidade de espelhos.",
        "entrada": "T1 e T3 com 1 vizinho",
        "cobertura": "T2 / T4",
    },
    32: {
        "leitura": "Continuidade de espelhos.",
        "entrada": "T1 e T3 com 1 vizinho",
        "cobertura": "T2 / T5",
    },
    33: {
        "leitura": "Gêmeos ativos.",
        "entrada": "11 / 22 / 33 / 0 com 3 vizinhos",
        "cobertura": "17 / 27",  #
    },
    34: {
        "leitura": "Terminal 4 .",
        "entrada": "T4 e T2 com 1 vizinho",
        "cobertura": "T1 / T6",
    },
    35: {
        "leitura": "Terminal 5.",
        "entrada": "T6 e T3 com 1 vizinho",
        "cobertura": "T2 / T9",
    },
    36: {
        "leitura": "Terminal 6.",
        "entrada": "T6 e T8 com 1 vizinho",
        "cobertura": "T5 / T9",
    },
}
