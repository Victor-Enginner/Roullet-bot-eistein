# ⚠️ EXPERIMENTAL - Scripts de Auto-Aposta

## AVISO CRÍTICO

Esta pasta contém scripts que realizam **apostas automáticas com dinheiro real**. 

**NÃO EXECUTE ESTES SCRIPTS EM PRODUÇÃO SEM:**
1. Completar o mapeamento de coordenadas para todos os 37 números
2. Testar extensivamente em ambiente sandbox/simulação
3. Validar que o seletor de UI corresponde ao site atual

## Arquivos

- `skynet_bot.py` - Entry-point alternativo que aposta automaticamente
- `bet_executor.py` - Classe que executa cliques programáticos (coordenadas incompletas)
- `skynet_capture.py` - Captura de números via MutationObserver

## Status

- **Coordenadas mapeadas:** 6 de 37 números (0, 1, 2, 3, 4, 5)
- **Data de movimentação:** 2026-07-01
- **Motivo:** SPRINT 0 - Eliminar risco de execução acidental

## Próximos Passos (se quiser ativar)

1. Completar `number_map` em `bet_executor.py` com todos os 37 números
2. Validar seletores de UI para o site específico
3. Adicionar validações de segurança (limite de perda, confirmação manual)
4. Testar em sandbox antes de produção

## Histórico

Estes scripts foram identificados durante auditoria de código (SPRINT 0) como código órfão não documentado que poderia causar perda financeira se executado acidentalmente. Foram movidos para esta pasta com avisos explícitos.
