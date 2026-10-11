# NaviXav 1.7.4

Publicado em 2026-10-11.

## Novidades

- O tráfego da VATSIM, IVAO e OpenSky antecipa as curvas: um avião que estava a curvar na última leitura continua a curvar, cada vez mais suavemente, no mapa e no simulador, em vez de seguir a direito até à leitura seguinte.
- Análise da aterragem: no toque, o NaviXav mostra a velocidade vertical registada pelo MSFS, a atitude e a inclinação, a distância após a soleira e o desvio do eixo da pista efetivamente utilizada, o vento de frente e cruzado, os ressaltos e a estabilidade da final, com uma pontuação em 100. A análise fica associada ao voo no diário de bordo e pode copiar-se ou guardar-se uma imagem pronta a partilhar.
- O diário de bordo é agora guardado na pasta de dados do NaviXav em vez de na janela: sobrevive a uma reinstalação ou a uma reposição do WebView2, e um tablet ligado pela rede local mostra o mesmo diário, só de leitura. Os voos já registados são recuperados automaticamente no primeiro arranque.
- Estatísticas do diário de bordo: número de voos, horas de voo e distância totais, toque e pontuação médios, melhor aterragem, aviões mais pilotados e aeródromos mais frequentados. O diário completo pode ser exportado em CSV para uma folha de cálculo.

## Correções

- O tráfego do OpenSky continua agora a mover-se de forma fluida no mapa e no simulador entre duas leituras, em vez de ficar parado e depois saltar várias milhas náuticas.
- O OpenSky é consultado com muito mais frequência no início de um voo, cerca de 30 em 30 segundos: a quota pública é distribuída pela duração de um voo em vez de um dia inteiro.
- O primeiro carregamento de um aeródromo já não demora quase um minuto: o NaviXav procura agora o ILS e os pontos na região do aeródromo em vez de percorrer as de todos os aeródromos já conhecidos, e recupera as frequências ILS que dava erradamente como inexistentes, como a da pista 23R de EGCC.

## Alterações

- Correction bug et ajout logbook.

O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática.
