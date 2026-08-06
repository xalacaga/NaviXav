# NaviXav 1.4.10

Publicado em 2026-08-06.

## Novidades

- As definições abrem agora o histórico completo de versões: todas as alterações importantes desde o início do acompanhamento, versão a versão, com a data e uma marca na que está instalada. O histórico é fornecido com a aplicação e lê-se sem ligação. Os textos das alterações continuam em inglês; o enquadramento e as secções seguem o idioma selecionado.
- O acompanhamento de voo distingue agora uma simulação em pausa de uma perdida: o indicador MSFS e a pastilha de acompanhamento mostram «MSFS em pausa» em vez de sugerir uma ligação cortada. Um simulador que não expõe este estado continua a ser acompanhado normalmente.
- Um lápis discreto aparece ao passar sobre a pista, a SID, a STAR, as suas transições e a aproximação: abre a lista dos restantes procedimentos publicados e permite alterar a escolha depois, mesmo quando o motor está seguro. A lista deixa de estar limitada a três entradas, mostra tudo o que é possível voar a partir da pista selecionada, e «Voltar à escolha automática» devolve o comando ao motor. O lápis permanece aceso numa escolha imposta.

## Correções

- Um procedimento ausente deixa de ocupar o lugar de um real. Quando nenhuma STAR está publicada para a pista, o motivo substitui o travessão numa única linha mais apertada, e a linha de transição que apenas repetia a ausência desaparece. O mesmo aperto para uma SID ou uma aproximação sem transição.
- Uma SID ou STAR que não está publicada para a pista selecionada deixa de ser encadeada: parte de outra cabeceira ou leva ao IAF do lado oposto do aeroporto. O NaviXav anuncia agora uma partida com guiamento radar ou uma chegada direta, e o procedimento descartado continua a ser proposto na lista de escolhas. Em Brive-Souillac na pista 29, o plano indica BSC e depois ILS RWY 29 em vez de uma STAR impossível de voar.
- Sem STAR, a aproximação e a sua transição ligam-se agora ao último ponto da rota em vez de ficarem sem ligação. Uma transição publicada nesse mesmo ponto é reconhecida e deixa de ser apresentada como uma escolha incerta.
- Os pontos de aproximação que o SimBrief deixa no registo de navegação sem os marcar, como CF29 ou RW11, deixam de contar como pontos de rota: já não são desenhados na rota nem usados para ligar a chegada.
- Quando uma STAR serve efetivamente a pista de aterragem mas termina num ponto que não inicia nenhuma aproximação, o NaviXav indica-o explicitamente em vez de deixar descobrir a rutura em voo.
- O histórico de versões deixa de ficar permanentemente por cima da interface: só abre ao clicar no seu ícone nas definições e fecha por completo.
- A janela das definições deixa de ter barra de deslocamento horizontal: um campo invisível transbordava em toda a largura da caixa, qualquer que fosse o tamanho da janela.

## Alterações

- Correction bug et améliorations diverses.

O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática.
