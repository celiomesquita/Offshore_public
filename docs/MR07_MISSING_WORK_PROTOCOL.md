# MR07 — sensibilidade da comparação ao trabalho não observado

Registrado antes da execução. Os resultados de casos completos e a seleção desigual por ATA já são conhecidos. Esta é análise exploratória de sensibilidade, não confirmação independente.

## Pergunta e desenho

A diferença de cobertura de trabalho entre uma prioridade já calculada e frequência conserva seu sinal quando se admite trabalho nos eventos excluídos do desfecho observado?

Congelar as prioridades, inclusões fracionárias, 13 origens e universo comum da avaliação anterior. Não reestimar médias nem escolher pesos para melhorar resultados. O alvo passa a ser o trabalho eventual associado aos eventos do horizonte de teste, incluindo consequências sem completude/data adequada. Isso difere do trabalho completo disponível até o fim do horizonte usado na avaliação inicial; a distinção deve acompanhar o resultado.

Para ATA a, sejam O_a o trabalho completo observado, n_a os eventos sem trabalho completo disponível até o corte e z_a a inclusão fracionária entre os três selecionados. O cenário atribui trabalho adicional x_a em [0,n_a U] a esses eventos. Não sobrescrever O_a nem os arquivos por evento. U é um teto hipotético, não limite empiricamente demonstrado.

Usar U = multiplicador × média de trabalho completo da frota no treinamento, com multiplicadores 0, 0,5, 1, 2, 5 e 10. Essa grade é uma referência de escala, não intervalo de confiança ou distribuição de imputação. Incluir diagnóstico sem teto finito: se eventos não observados pertencem a sistemas favorecidos por métodos diferentes, a ordenação pode não ser identificada com os dados disponíveis.

Os totais parciais conhecidos nos registros excluídos não serão tratados como nulos observados nem como dados disponíveis na origem. Como pertencem ao extrato retrospectivo, calcular separadamente o menor teto compatível com o trabalho parcial conhecido por evento no teste. Cenários que permitem menos trabalho que esse parcial são identificados como incompatíveis com o extrato, sem ajustar o teto após observar vantagens. O envelope principal [0,n_a U] é deliberadamente amplo e não aproveita pisos parciais; por isso, seus extremos são possibilidades matemáticas, não estimativas de carga real.

Como segunda variante, quando U for compatível com todos os parciais, impor os pisos conhecidos L_a, substituindo O_a por O_a+L_a e o intervalo adicional por [0,n_a U−L_a]. Se o teto for incompatível, não produzir limites dessa variante. Os pisos usam alocação igual por evento da ordem e o extrato completo apenas para avaliar consequências, nunca para reconstruir prioridades do passado. Ignorar acoplamento de eventos da mesma ordem amplia a caixa, tornando o envelope conservador; não alegar que todo extremo é uma imputação válida em nível de ordem.

## Medida e limites

Para método P e frequência F, a diferença de cobertura é

Δ(x) = Σ_a (zPa−zFa)(O_a+x_a) / Σ_a (O_a+x_a).

Calcular mínimo e máximo dessa razão sobre o mesmo vetor x para os dois métodos; não comparar extremos de cenários incompatíveis entre si. Usar a monotonicidade da função residual de programação linear-fracionária para obter limites determinísticos, verificando em casos pequenos por enumeração dos vértices da caixa. Denominador observado precisa ser positivo. Com U=0, recuperar exatamente o resultado anterior.

Apresentar por método e teto: intervalo entre médias dos mínimos e dos máximos por origem, número de origens que admitem reversão do sinal e empates estruturais (mesma seleção). Cada origem pode ter seu cenário extremo próprio; eventos reaparecem em horizontes sobrepostos. Portanto, médias dos extremos por origem são envelopes conservadores, não os extremos de uma única imputação coerente no tempo, e não têm interpretação probabilística.

Valor padrão de peças permanece observado e inalterado; não concluir dominância nos dois desfechos se apenas a cobertura de trabalho puder mudar. Esta análise não mede incerteza de estimação dos próprios rankings, nem resolve ausência de suporte nos ATA fora do universo comum.
