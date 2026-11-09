# Protocolo MR07 — comparação temporal de previsão e priorização

Estado: especificado antes das novas comparações, em 7 de novembro de 2026. Os resultados da divisão original já são conhecidos; as novas avaliações são retrospectivas.

## Previsão de demanda

Origens mensais após pelo menos 12 meses completos de histórico; horizonte primário de três meses, com seis meses como sensibilidade. Janela observacional: janeiro/2024–março/2026. Origens com horizontes sobrepostos não são réplicas independentes.

Comparadores: taxa acumulada por exposição; taxa dos seis meses anteriores; Poisson/NB por ATA com exposição e tendência extrapolável, ajustados apenas ao passado. A complexidade adicional deve melhorar contagem/calibração para ser recomendada. Não incluir efeito fixo de mês futuro. Separar os resultados condicionados às horas de voo realizadas de uma previsão operacional com horas planejadas, indisponíveis até comprovação.

Painel: usar a reconstrução com datas verificadas. Para cada origem, calcular exposição acumulada por aeronave e aplicar o limiar de 500 horas usando apenas o passado. Avaliar aeronaves elegíveis nessa origem, mesmo que a composição mude posteriormente; explicitar regra para aeronaves sem histórico. Nenhum custo, normalizador, seleção de peças ou peso é estimado no futuro.

Métricas: MAE, RMSE e viés por origem e ATA; cobertura e amplitude de intervalos quando o método os fornecer; Spearman e retenção do conjunto prioritário apenas como métricas secundárias. Reportar totais e erros por ATA para evitar que a dominância de poucos sistemas oculte falhas.

Incerteza: preservar resultados por origem. Avaliar diferenças pareadas com reamostragem temporal por blocos, com tamanho de bloco e sementes definidos antes da inferência. Reportar também todas as diferenças observadas; não usar o número de células ATA como tamanho amostral independente.

## Priorização

Comparar frequência, custo direto, R+C e formulação revisada aprovada em RV01 sob igual número de ATA selecionados e, se a ação tiver custos observáveis, igual orçamento. Critério primário de valor decisório: cobertura de consequências futuras observadas e independente do escore avaliado. Não escolher o critério que favorecer o método depois de ver resultados.

Segurança depende dos rótulos da MR04. Sem rótulos independentes, só avaliar estabilidade do sinal textual e não benefício de segurança. Cobertura de custo/trabalho é capacidade de identificar carga futura, não economia causada pela intervenção. Políticas de manutenção/estoque são avaliadas separadamente pela MR06.

## Regras de interpretação

Resultado favorável: melhora prática consistente com incerteza compatível e custo de aplicação justificável. Nulo: manter o comparador mais simples e reconhecer ausência de benefício demonstrado. Misto: descrever as condições em que a integração agrega valor. Contrário: retirar a superioridade alegada. Inconclusivo: explicitar pequena amostra temporal ou informação insuficiente.

As taxas acumulada e recente já foram executadas para três meses. Ajustes posteriores devem registrar data, justificativa e resultados já conhecidos no registro técnico.

## Especificação da rodada Poisson/NB — 7/11/2026

Antes de executar os modelos: agregar contagens por ATA–mês na frota elegível em cada origem, com offset log das horas de voo mensais dessa mesma frota. Usar intercepto por ATA e uma tendência linear comum, em anos, centrada na origem. Comparar Poisson e NB2 com dispersão comum estimada apenas no treinamento. Esta especificação parcimoniosa não é o antigo modelo com efeitos fixos de meses futuros. Sistemas sem evento no treinamento recebem previsão zero e são identificados no manifesto; não há evidência para estimar sua tendência individual.

Estimar NB2 por máxima verossimilhança, com ponto inicial Poisson. Registrar convergência e advertências; ajuste não convergente não pode ser silenciosamente substituído por resultado NB válido. Os 27 capítulos ATA são o universo retrospectivo fixado do estudo, não uma seleção de variáveis otimizada por desempenho futuro.

Horizontes de três e seis meses; origens mensais iniciadas em dezembro/2024 e terminadas quando ainda houver horizonte completo até março/2026. Taxas acumulada e recente são recalculadas sobre a mesma população para cada comparação. Os resultados são condicionados à exposição futura realizada e excluem células com exposição registrada não positiva; não validam previsão de utilização, tratamento de horas ausentes ou eventos em solo.

Esta rodada avalia previsões pontuais e convergência. Intervalos preditivos com incerteza paramétrica, cobertura, sensibilidade à incompletude e inferência temporal ficam explicitamente pendentes. Não interpretar dispersão NB de contagens mensais como dispersão de demanda durante lead time sem um modelo de agregação temporal.
