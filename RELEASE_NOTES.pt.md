# NaviXav 1.5.0

Publicado em 2026-08-28.

## Novidades

- Clicar na fotografia de uma aeronave abre agora uma pré-visualização ampliada no NaviXav; fecha-se com o botão, um clique no exterior ou a tecla Escape.
- O cartão e o inventário Aircraft mostram agora uma fotografia real com licença livre ao lado do nome de cada família de aeronaves suportada; os aviões adicionais instalados em Community usam automaticamente a respetiva miniatura local quando disponível.
- Quando uma carta ChartFox não pode ser integrada, o NaviXav passa a propor o catálogo nacional oficial no mesmo cartão quando o aeródromo é abrangido.
- O acompanhamento do voo estima agora o Top of Climb a partir do nível de cruzeiro, da velocidade vertical e da velocidade no solo; os pontos calculados TOC e TOD aparecem no mapa como pontos distintos.
- O ChartFox pode agora ser ligado nas Definições com uma conta VATSIM; as suas cartas a pedido estão disponíveis como fonte opcional para os aeródromos de partida e chegada.
- O menu Charts indica agora que é necessária uma conta ChartFox/VATSIM para aceder às cartas AIRAC do ChartFox e disponibiliza uma ligação direta às Definições.

## Correções

- As fotografias das aeronaves deixam de ficar ocultas atrás do cartão do tipo ICAO no cartão e no inventário Aircraft.
- Abrir o PDF de um aeródromo em Charts deixa de empurrar o outro aeródromo para baixo do documento: Partida e Chegada permanecem lado a lado em ecrãs largos, e o cartão não aberto fica em primeiro lugar nas janelas compactas.
- A indicação «apenas simulação» do ChartFox nas Definições passa a seguir o idioma da interface.
- As cartas ChartFox cuja fonte proíbe a integração deixam de mostrar uma área em branco: o NaviXav explica a restrição e permite abri-las diretamente no ChartFox.
- Os pontos calculados TOC e TOD usam agora cores próprias magenta e vermelha, distintas de todos os pontos da rota.
- Os fundos cartográficos CartoDB Positron e Dark Matter foram removidos: o seu serviço gratuito passou a marcar cada mosaico com a menção «API key required». A escolha é entre OpenStreetMap Standard e OpenTopoMap, e uma definição que deixou de ser válida volta automaticamente a OpenStreetMap.
- O briefing meteorológico deixa de aparecer parcialmente em francês quando a interface está noutro idioma: as notas operacionais e os fenómenos METAR seguem agora o idioma selecionado.
- As trovoadas sem precipitação observada passam a ser assinaladas: os grupos TS, VCTS e VCSH eram ignorados na descodificação do METAR. Além disso, o «PO» de «TEMPO» deixa de ser lido como remoinhos de poeira.
- As SID aparecem finalmente no mapa: o seu traçado, os seus pontos e as suas restrições publicadas faltavam assim que um mesmo procedimento servia duas cabeceiras, o que acontece em quase todos os grandes aeródromos. A partida ficava reduzida a uma linha reta até ao primeiro ponto em rota. As STAR recuperam também a sua parte final, própria da pista de aterragem. A base de navegação é reimportada automaticamente do simulador no arranque seguinte.

## Alterações

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática.
