# MR06 — ampliação e avaliação com sementes independentes

Especificação anterior à execução desta rodada, em 8/11/2026. O piloto anterior é conhecido. A avaliação abaixo é confirmação numérica condicionada ao cenário sintético, não validação da frota.

## Revisão técnica do módulo

O modelo separa dias em operação de calendário, suspende o envelhecimento durante parada, gera demanda endógena às trocas e inclui intervenção além da espera. Estoque e pipeline conservam peças; compra é cobrada uma vez por demanda, encargo de capital por ano e perda por dia-ativo. Quatro testes determinísticos verificam esses mecanismos, inclusive corte de aquecimento. Isso permite prosseguir com a avaliação numérica limitada a este módulo. RV01 global permanece aberta: não se aprova com isso inferência empírica de sobrevivência, segurança, disponibilidade ou a formulação completa do artigo. Revisão realizada pelo agente executor, sem alegar parecer independente de outro modelo.

## Seleção ampliada

Manter parâmetros e sementes 0–7 do piloto, aquecimento 365 dias e mensuração 3.650 dias. Ampliar idades para 60, 90, 120, 150, 180, 210, 240, 300, 360 e infinito; estoques 0–12, 16 e 24. Enumerar 150 políticas, oito sementes, 1.200 execuções. Fixar quatro comparadores após essa rodada: corretiva sem estoque; melhor corretiva na grade ampliada; melhor idade com estoque zero; melhor par da grade. Preservar empates e registrar se o melhor par está na borda. Resultado continua óptimo apenas da média amostral na grade.

Congelar candidatos em manifesto antes de gerar resultados de sementes novas. Não reoptimizar durante a avaliação. Se a grade revelar nova borda, declarar a limitação; não expandir novamente com base nos resultados independentes.

## Avaliação independente e sensibilidade de inicialização

Usar 50 sementes novas, 1000–1049, excedendo as 47 indicadas pelo piloto. Contraste primário: custo anual do candidato conjunto menos o da corretiva com estoque escolhida no treinamento. Comparações adicionais: corretiva sem estoque e idade com estoque zero. Mesmas sementes entre políticas e cenários de inicialização, mantendo fluxos por ativo.

Configurações pré-fixadas (aquecimento, mensuração em dias): (365,3650), (0,3650), (1095,3650) e (365,7300). A primeira é primária. As demais verificam sensibilidade, sem escolher a configuração mais favorável nem provar estacionariedade. Reportar médias anuais, disponibilidade, dias-ativo parados, compras e componentes de custo; contagens totais de eventos não são directamente comparáveis entre horizontes, devendo ser anualizadas.

Diferenças de custo pareadas por semente: média, desvio-padrão e intervalo t de 95% com 49 graus de liberdade. Sementes são réplicas independentes do simulador; esse intervalo representa erro Monte Carlo sob parâmetros fixos, não incerteza de modelo ou dos dados reais. Contrastes adicionais são descritivos, sem afirmar controlo simultâneo de múltiplas comparações. Não reabrir a selecção com essas sementes.

Interpretação: ganho condicionado ao cenário se o contraste primário favorecer o candidato e a magnitude for reportada com incerteza; resultado misto entre horizontes limita robustez; ausência de ganho fica preservada. Nenhum resultado autoriza recomendar T ou s ao operador. Distribuição de vida, reposição recuperável, preços, duração/custo de parada e utilização ainda exigem sensibilidade própria.
