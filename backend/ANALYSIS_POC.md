# Análise de cláusulas na POC

A resposta do modelo deve fornecer, para cada cláusula, conteúdo textual não vazio (`content`, `excerpt` ou `trecho`) e classificação de risco (`risk_level` ou `risk`) em `low`, `medium`, `high` ou `critical`. Valores ausentes ou inválidos fazem a análise falhar; não são classificados automaticamente como risco baixo. Essa regra também limita análises de extração que retornem cláusulas sem risco. Representar risco não avaliado exigirá decisão e alteração futura de contrato.

O serviço normaliza os aliases antes de calcular o resumo. API síncrona e worker usam a mesma validação e construção das cláusulas. Em erro de processamento ou persistência, a análise é marcada como falha e as cláusulas da tentativa não são confirmadas parcialmente. Dados anteriormente gravados não são corrigidos automaticamente.

No GET de resultado, o nível geral é uma heurística: a maior classificação entre as cláusulas persistidas (critical > high > medium > low). A resposta identifica a fonte em `overall_risk_level_source` como `highest_clause_risk`, ou null se não houver nível. Sem cláusulas classificadas, é null, inclusive quando o modelo informa um nível geral. Em conflito, prevalece a heurística das cláusulas, não a classificação geral do modelo, que permanece no resultado bruto. Essa heurística não é uma avaliação jurídica. O score geral vem exclusivamente do valor numérico finito fornecido pelo modelo: ausente, nulo ou inválido retorna null; zero explícito permanece zero. O nível e o score podem assim divergir, pois têm fontes diferentes. Consumidores devem tratar os dois campos como anuláveis.

A busca textual de análises não tem implementação no backend e seu campo foi retirado da interface. O filtro de status usa o parâmetro existente `status_filter`.
