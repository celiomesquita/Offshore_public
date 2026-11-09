# MR03/MR07 — protocolo da primeira comparação de prioridades

Registrado antes da execução desta rodada. É avaliação retrospectiva exploratória, não teste confirmatório nem reconstrução comprovada do sistema de informação disponível em cada data.

## Unidade e consequências

Cada remoção mecânica rastreada é um evento. Repartir igualmente o trabalho de uma ordem entre suas remoções mecânicas rastreadas, conservando o total por ordem; isso equivale à alocação proporcional às contagens ATA. A ligação não prova que todo trabalho da ordem foi causado por essas remoções. Não remover tarefas por repetição de código: a fonte contém linhas distintas de execução.

Preservar ausências ao ler os arquivos brutos. Trabalho completo requer vínculo com tarefas, todas as horas e datas preenchidas, valores não negativos e ordem fora da classe ALHWO cuja semântica de zeros é problemática. Manter o total parcial conhecido em campo distinto, sem convertê-lo em consequência completa. Outras ordens com zero explicitamente registrado são mantidas e sua quantidade reportada.

O campo Std Cost representa valor padrão de peça associado à remoção; não comprova desembolso, consumo integral da peça ou custo de reparo. Nesta rodada, C é explicitamente **valor padrão de peças**, sem AOG nem trabalho monetizado. Valores ausentes/negativos não viram zero. Não interpretar cobertura desse valor como economia financeira.

Disponibilidade temporal aproximada do trabalho: máximo entre datas de remoção da ordem e datas de assinatura das tarefas. Uma ordem incompleta não tem data de completude utilizável. A fonte não contém histórico de lançamento/revisão nem fechamento formal das ordens. As datas são proxies retrospectivos de disponibilidade; uma análise com elas não comprova ausência de vazamento informacional operacional. Custos são tratados como atributos da remoção, sem prova de vigência histórica dos valores padrão.

## População e avaliação

Origens dezembro/2024 a dezembro/2025, horizonte três meses, 13 origens. Aplicar 500 horas acumuladas de treinamento para elegibilidade e usar apenas aeronave-mês com exposição registrada positiva, como na comparação de contagens. Consequências de treinamento só entram quando sua data aproximada de disponibilidade não exceder a origem. As remoções de teste devem estar nos três meses seguintes e seu trabalho disponível até o fim desse horizonte. Publicar cobertura: essa regra pode excluir consequências tardias e não mede carga eventual completa.

Calcular frequência em todas as remoções elegíveis de treinamento. Médias condicionais de trabalho usam apenas consequências completas disponíveis; médias de valor padrão usam valores válidos. Exigir médias finitas dos dois tipos e frequência positiva para todos os métodos comparados; o universo comum é definido apenas no treinamento. Reportar a carga de teste fora desse universo e cobertura por ATA, sem esconder exclusões.

Escalas por origem: médias por evento da frota no treinamento para cada consequência, sem observar teste. São referências de análise, não preferências elicitadas. Métodos: frequência; trabalho esperado por exposição (w=1); valor padrão esperado por exposição (w=0); três cenários interiores w=0,25/0,50/0,75. Não seleccionar o peso de melhor desempenho para recomendação. A descrição explícita das escalas é indispensável; pesos iguais não são neutros.

Selecionar k=3 ATA, fixado antes da execução como análise de concentração, não como política operacional óptima. Em empates no limiar, usar inclusão fracionária igual para todos os empatados, de modo que a soma das inclusões seja k, evitando desempate arbitrário por código ATA. Se houver menos de k capítulos, registrar o número efetivo.

Desfechos separados: proporção do trabalho completo observado de teste e proporção do valor padrão de peças de teste cobertos pelo conjunto selecionado, no mesmo universo comum para todos os métodos. Registrar também denominadores, perdas fora do universo, qM/qC por origem e previsões/prioridades. Sem denominador positivo, cobertura é ausente, não zero.

Não executar teste de significância ingênuo entre origens sobrepostas. Resultado inicial será descritivo, preservando diferenças por origem. Uma vantagem em um desfecho e desvantagem no outro é compensação, não dominância. Não incluir S não validado nem A sem política e cobertura adequada. Comparação com escore histórico de cinco pilares fica adiada: seus agregados de janela completa não são comparador temporal sem vazamento.
