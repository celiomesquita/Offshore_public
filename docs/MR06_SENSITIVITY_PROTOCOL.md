# MR06 — sensibilidade estrutural e económica

Definido antes da execução desta rodada. O resultado do cenário base é conhecido. Trata-se de exploração de condições de ganho/perda em modelo sintético, não validação externa.

## Cenários

Alterar um fator por vez a partir de JointInputs; não inferir interações de uma análise unifatorial. Usar cenário base e onze perturbações:

- forma Weibull 0,7; 1; 3, mantendo a **mesma média de vida** do cenário base (forma 2, escala 180) por ajuste da escala com a função gama;
- lead time de compra de 0, 5 e 60 dias, contra 20 no cenário base;
- custo de parada de USD 0, 200 e 20.000 por dia-ativo, contra 2.000;
- preço da peça USD 100 e 10.000, contra 1.000, com encargo de capital de 20% aplicado ao novo preço.

Nenhuma alteração introduz reparo recuperável: reposição continua sendo compra de consumível com prazo determinístico. Esta sensibilidade não representa oficina, reparo imperfeito ou variabilidade de lead time. O relógio continua em dias em operação e para durante indisponibilidade. Tarifas zero/altas são cenários de identificação de mecanismo, não estimativas do operador.

## Seleção e avaliação

Em cada cenário, seleccionar novamente corretiva com estoque e política conjunta na grade de dez idades × 15 estoques, com sementes de treinamento 0–7, conforme MR06_EXPANDED_PROTOCOL. Congelar candidatos de todos os cenários antes de executar a avaliação. Registrar limites da grade e política sem idade preventiva quando seleccionada.

Avaliar três políticas com 50 sementes novas 2000–2049 por cenário: corretiva adaptada; conjunta adaptada; transferência sem adaptação do candidato base (T=150,s=6). O cenário base é repetido com essas sementes para comparação na mesma rodada, não como terceira descoberta independente. Aquecimento 365 e mensuração 3.650 dias. As configurações compartilham sementes; não tratar cenários como amostras independentes de frotas.

Contrastes: conjunta adaptada menos corretiva adaptada; candidato base transferido menos corretiva adaptada. Reportar média, intervalo t pareado Monte Carlo de 95%, disponibilidade e dias-ativo parados, compras e eventos anualizados. Empates de política são resultados estruturais, não testes estatísticos. Os intervalos são individuais, sem correção de multiplicidade, e não fundamentam uma alegação confirmatória conjunta em 12 cenários.

Interpretação: manter ganho, ausência de ganho e perda. Custo menor acompanhado de menor disponibilidade deve ser explicitado, particularmente quando não se atribui custo à parada. Não escolher pesos ou cenários para recuperar superioridade. Se o mínimo estiver na fronteira de grade, restringir a conclusão ao candidato avaliado; não expandir usando os resultados de teste.

O contraste adaptado é condicionado a seleção no treinamento e à grade, não garantia de óptimo verdadeiro. O contraste transferido verifica fragilidade de reutilizar parâmetros do cenário base. Resultados com compra não resolvem a discrepância entre consumíveis e reparáveis na aplicação empírica.
