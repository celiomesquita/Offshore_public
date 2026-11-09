# Protocolo MR06 — acoplamento substituição–estoque

Estado: proposta metodológica para RV01, antes de executar novos experimentos de políticas. A evidência empírica de sobrevivência ainda depende de MR05.

## Especificação executável e piloto — 8/11/2026

Implementação: `ramsc/joint_policy.py`. O piloto abaixo é verificação exploratória, não experimento principal liberado por RV01. Nenhum parâmetro é estimativa da frota. Sistema sintético com oito ativos, uma posição essencial por ativo e estoque compartilhado. Vida Weibull com forma 2 e escala 180 dias **em operação**; o relógio para durante indisponibilidade. Esse tempo não é o campo calendário Days On A/c da base empírica. Troca renova perfeitamente; não há redundância nem restrição de equipe. Intervenções simultâneas são permitidas em ativos distintos, sem somar duas indisponibilidades do mesmo ativo.

Reposição por **compra de consumível**, não reparo: cada demanda corretiva/preventiva dispara uma compra que chega após 20 dias, independentemente de haver estoque. Backorders FIFO. Entrega serve primeiro demanda pendente; caso contrário aumenta saldo disponível. A posição de estoque satisfaz saldo+pipeline−backlog=s em todo evento. Estoque inicial s, todos os ativos novos e operacionais; intervenção corretiva de dois dias e preventiva de meio dia. Estoque pode evitar espera, não a intervenção. Com s=0 e lead time zero, a fila é atendida no mesmo instante: atraso zero não implica peça disponível imediatamente antes da demanda.

Custos hipotéticos: USD 1.000 por peça consumida, USD 500 por intervenção corretiva, USD 150 por preventiva, USD 2.000 por dia-ativo indisponível; encargo anual de capital de 20% do investimento s×1.000. Investimento inicial reportado separadamente, sem somá-lo novamente ao custo anual. O encargo usa estoque-base comprometido, não saldo médio disponível. Peças inicialmente instaladas são condição comum e não entram como compra inicial diferencial. Custos de peça/trabalho são reconhecidos no instante da demanda; downtime é integrado no tempo. Não incluir um dia AOG fixo adicional.

Aquecimento de 365 dias e mensuração de 3.650 dias; horizonte finito pós-aquecimento, sem alegar regime estacionário demonstrado. Empates de relógio: entregas, conclusões de intervenção, demandas; ativos em FIFO segundo a ordem dos eventos. Eventos no limite final não geram custos da janela encerrada. Cada ativo tem fluxo aleatório próprio, pareado por ciclo entre políticas; calendários divergentes não garantem redução de variância.

Piloto: oito sementes 0–7; enumerar idades 60, 120, 180, 360 e infinito, e estoques 0, 1, 2, 4 e 8 (25 políticas, 200 execuções). Comparadores: corretiva s=0; corretiva com melhor s da grade; idade com s=0; melhor par da grade. São mínimos de médias do piloto, sujeitos a seleção otimista, não soluções operacionais nem ótimo contínuo/global. Preservar todos os resultados, inclusive perda de benefício.

Planeamento de precisão: calcular desvio-padrão das diferenças pareadas entre o candidato do piloto e cada comparador. Dimensionar amostra indicativa por N=ceil[(1,96 sd/ε)²], ε=1% da média anual de custo da corretiva sem estoque, mínimo 30 repetições. É aproximação normal com variância de piloto pequeno, não garantia. O experimento principal exigirá sementes novas, revisão dos mecanismos e sensibilidade a aquecimento/horizonte e distribuição de vida antes de recomendações.

## Problema

Comparar manutenção corretiva, substituição por idade, estoque e decisão conjunta sob um mesmo processo de degradação, lead time e custo. Não somar indisponibilidade por evento fixada em um dia ao atraso logístico produzido pelo estoque. Separar tempo de intervenção, espera administrativa e espera por peça; considerar sobreposição quando houver eventos simultâneos.

## Definição da política e do sistema

Unidade de decisão: peça/posição e estoque compartilhado pela frota. T é idade de substituição e s é estoque-base. O cenário inicial admite renovação perfeita após troca, durações de vida independentes, demanda unitária e reposição por compra ou reparo em prazo explicitado. Reposição não pode ser tratada simultaneamente como compra e recuperação gratuita.

No simulador de avaliação, o relógio de idade avança na escala em que a distribuição de vida foi definida: calendário, horas de voo ou ciclos. Falha ou idade T gera demanda; a ausência de peça produz espera até reposição. A substituição preventiva também consome peça e capacidade. O processo de demanda deve ser gerado pela política, não mantido igual ao observado sob outra política.

Custos: aquisição/uso de peças, reparo, trabalho e parada programada/corretiva, perdas por indisponibilidade e manutenção de estoque com unidade temporal comum. Apresentar investimentos iniciais separadamente do custo recorrente; declarar a anualização/horizonte antes de comparar. Tarifa AOG e custo de capital sem fonte são cenários, não valores observados.

## Comparações

Corretiva sem estoque; corretiva com estoque otimizado; idade com estoque fixo; decisão conjunta T,s. Incluir política real somente se conhecida. Usar igual horizonte, custos, utilização e restrições de atendimento. Instâncias demonstrativas devem permitir enumeração da grade de T,s e checagem do mínimo; comparar o procedimento eficiente contra essa referência.

Teste do mecanismo: a redução da espera por estoque pode aumentar T ótimo quando a penalidade corretiva diminui, mas não se pressupõe que isso sempre ocorra. Relatar todas as condições em que o sentido muda. O estoque não elimina trabalho nem toda indisponibilidade.

## Verificação e incerteza

Casos-limite: falhas nulas, lead time zero, custo de indisponibilidade zero, estoque suficiente, T tendendo ao infinito e ausência de substituição preventiva. Conservação de peças e eventos; fluxo em trânsito consistente com demandas; nenhum custo em moeda/hora somado diretamente a investimento em moeda.

Simulação com fluxos aleatórios pareados entre políticas e sementes registradas. Separar aquecimento do horizonte de mensuração quando se estimar regime estacionário. Dimensionar repetições pela precisão da diferença de custo/indisponibilidade após piloto, antes da comparação principal. Reportar custo por ano, dias-aeronave indisponíveis por ano, atendimento, número de intervenções e investimento, com intervalos.

Sem base instalada/censura suficiente, utilizar cenários de vida gerados por distribuições conhecidas para verificar implementação e consequências das premissas. Não calibrar uma recomendação operacional de T com pseudocensura inventada. Os intervalos históricos de 81 dias e semelhantes continuam referências da versão submetida, não alvos a reproduzir.

## Critério de avanço

Formulação e protocolo precisam da revisão RV01 antes dos experimentos principais dependentes. Evidência em cenário sintético confirma comportamento sob hipóteses declaradas; benefício na frota requer validação com dados operacionais ou avaliação prospectiva apropriada.
