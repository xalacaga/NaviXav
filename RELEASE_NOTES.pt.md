# NaviXav 1.6.0

Publicado em 2026-08-30.

## Novidades

- Controlos mais claros: o Acompanhamento do voo passa a ter um interruptor visível para desativar ou reativar todos os alarmes NaviXav, incluindo as mensagens MASTER WARNING e MASTER CAUTION, sem parar o acompanhamento; após uma atualização, o histórico de versões abre automaticamente no primeiro reinício e continua depois disponível a pedido.
- Mudança imediata da fonte de tráfego nas barras do Mapa e da Rolagem: os seletores VATSIM, IVAO e OpenSky permanecem sincronizados, reiniciam corretamente a recolha e guardam a escolha localmente.
- Tráfego real OpenSky: o NaviXav pode mostrar vetores de estado ADS-B públicos num raio de 100 NM em redor da aeronave, com atribuição da fonte e cache respeitadora da API; esta vista real permanece rigorosamente separada da injeção no MSFS.
- As definições foram reorganizadas em categorias recolhíveis adequadas a janelas compactas, com caminho FSLTL manual, acesso ao instalador oficial FlyByWire quando faltam modelos e IVAO como segunda fonte pública e gratuita de tráfego de rede além do VATSIM.
- Compatibilidade exclusiva com o MSFS 2024: o NaviXav utiliza agora a API SimConnect AI EX1 nativa do MSFS 2024 e recusa uma DLL antiga do MSFS 2020 no arranque ou na compilação, em vez de prosseguir com uma ligação ou funções inadequadas.
- Injeção de tráfego VATSIM no MSFS: o NaviXav deteta automaticamente o FSLTL Base Models na pasta Community, indexa os ficheiros aircraft.cfg e as regras VMR sem os modificar, escolhe o modelo exato ou genérico mais seguro e cria, atualiza e remove apenas os seus próprios objetos SimConnect numa área limitada em redor do jogador. A opção está desativada por omissão e a interface mostra a versão FSLTL detetada.
- Tráfego circundante: um botão «Tráfego VATSIM» na barra do mapa e «Tráfego do simulador» na da rolagem mostra as outras aeronaves. No mapa cada aeronave da rede é uma silhueta orientada à proa com o indicativo por baixo, e um clique abre a sua ficha: tipo, frequência, piloto, aeródromos de partida e de chegada nomeados a partir da base MSFS, velocidade no solo e altitude. A planta de rolagem mostra o tráfego do simulador, o único exato ao metro. Desligado por omissão, enquanto o estiver não é feita qualquer chamada.
- Perfil vertical: o TOD passa a usar prioritariamente o ponto de desempenho do último OFP SimBrief após validar as respetivas coordenadas na rota ativa; os limites máximos da STAR e da aproximação continuam a ser aplicados e o cálculo geométrico de 3° assume automaticamente quando esse ponto falta ou já não corresponde à rota.
- Posições VATSIM em linha: ativado nas definições, o NaviXav assinala com um ponto as frequências do aeródromo cujo posto está ocupado e mostra ao passar o rato o indicativo do controlador e a sua frequência — a da rede nem sempre é a que o simulador publica. A definição está desativada por omissão e enquanto o estiver não é feita qualquer chamada.
- Frequências do aeródromo: a frequência de partida completa agora a linha e uma função com várias frequências assinala-o com um «+n» em vez de sugerir que só existe uma; o detalhe de cada posto, incluindo as placas de estacionamento, lê-se ao passar o rato.
- Acompanhamento do voo: um segundo indicador anuncia a frequência prevista na fase em curso e assinala-se quando o rádio já está nela. Permanece em silêncio quando o aeródromo publica várias frequências para a mesma função, por não se saber qual serve a pista em serviço.
- Acompanhamento do voo: um indicador de rádio mostra a frequência sintonizada na COM1 e nomeia o posto correspondente do aeródromo, incluindo o ground por pista — para confirmar num relance que se marcou a frequência indicada.
- Diagnóstico: o comando «navixav airport» lista as frequências do aeródromo a par do número com que o simulador designa cada função e assinala uma função que não consegue traduzir em vez de a omitir.
- Frequências do aeródromo: os cartões Partida e Chegada do plano de voo passam a mostrar a cadeia rádio publicada pelo MSFS, pela ordem em que é utilizada — ATIS, DEL, GND, TWR à partida, ATIS, APP, TWR, GND à chegada. Quando um aeródromo publica várias frequências para a mesma função, as restantes surgem ao passar o rato.
- Preparação do TOD: a 50 NM, o sistema de alertas pede a preparação da descida e destaca o cartão TOD; a 10 NM é acionado um alerta TOD iminente separado que permanece ativo até ao início da descida.
- Configuração da aeronave: a interface guiada adota um sinóptico de cockpit mais legível com cartões equilibrados, um ícone por sistema, um indicador de estado e verdadeiras luzes de controlo; a interface clássica mantém o design anterior.
- Nova interface guiada pelo voo: uma faixa persistente destaca a fase, pista ou procedimento, próxima ação e módulo recomendado; as cartas de partida, chegada e aproximação são preparadas num painel e a Rolagem ganha espaço. A Organização da interface repõe imediatamente a interface clássica sem reiniciar.
- Plano de rolagem: a partida de um posto de nariz ao terminal começa por um pushback, traçado a violeta e a tracejado curto no plano e anunciado na faixa com a distância e o rumo depois de alinhado; uma rampa, uma rolagem retomada ou uma chegada não mostram nenhum.
- Preparação do plano: a faixa que anuncia o preenchimento da cache do MSFS mostra agora uma aeronave a atravessar o quadro, com o seu rasto, enquanto durar a leitura. A espera podia chegar a várias dezenas de segundos sem que nada se mexesse.
- Ficha MCDU: o NaviXav passa a obter o ZFWCG do SimBrief e apresenta o centro de gravidade sem combustível juntamente com o número de passageiros na página de pesos; o ZFWCG também aparece no Dispatch.
- Escolher uma fonte de tráfego basta agora para a injetar no MSFS: a injeção está ativa por predefinição e a caixa das definições serve apenas para desativá-la.
- Um indicador «apenas mapa» aparece na barra do mapa quando o tráfego é mostrado sem ser injetado, e a dica indica o motivo: injeção desativada, FSLTL ausente ou fonte real.
- O tráfego real ADS-B entra finalmente no MSFS: o tipo de cada aeronave é resolvido a partir de dois registos públicos complementares, o que permite enfim escolher-lhe um modelo FSLTL. Uma aeronave desconhecida na primeira leitura aparece na seguinte, assim que o seu endereço for resolvido.
- Escolher uma fonte de tráfego basta agora para a injetar no simulador. A caixa «Injetar tráfego de rede no MSFS» desaparece das definições: o botão da camada é o único interruptor, e o que ele mostra é o que voa.

## Correções

- As aeronaves OpenSky estacionadas continuam injetáveis quando o transponder omite altitude barométrica, velocidade ou rumo: o NaviXav usa primeiro a altitude geométrica e depois completa apenas os dados de solo em falta.
- Tráfego real OpenSky no MSFS: as aeronaves sem tipo ADS-B usam imediatamente um modelo FSLTL genérico seguro em vez de permanecerem invisíveis e adotam o modelo exato assim que o registo ICAO24 responde; a injeção atualiza agora a posição a cada segundo.
- Tráfego IVAO e OpenSky mais fluido no MSFS: o NaviXav extrapola a posição a cada segundo entre leituras da rede e mantém brevemente uma aeronave omitida pela fonte, evitando que desapareça e reapareça; a contagem decrescente fixa de 15 segundos, inexata para estas fontes, foi retirada da interface.
- Tráfego de rede nas portas e nas vias de rolagem: quando o VATSIM não publica o estado no solo, o NaviXav passa a deduzi-lo de uma velocidade igual ou inferior a 50 kt; as aeronaves estacionadas e em rolagem são injetadas em vez de descartadas.
- Inventário de aeronaves: Atualizar passa a detetar add-ons pilotáveis com isAirTraffic incorreto, como o Rafale M, e cada aeronave mostra a sua própria miniatura local em vez de reutilizar a imagem da aeronave carregada.
- Plano de rolagem à chegada: a posição real da aeronave e o rumo da pista passam a excluir as saídas já ultrapassadas; após aterrar na 24R, o NaviXav deixa de propor um regresso em sentido contrário a uma saída atrás da aeronave.
- Mapa: a parte em rota do plano de voo mantém a cor violeta, mas passa a usar uma linha contínua mais legível com níveis de zoom baixos.
- Página Aircraft: as cadeias longas de equipamento ICAO passam a quebrar dentro do respetivo cartão em vez de transbordarem para o perfil vizinho.
- Identidade SimConnect: as variáveis de texto como TITLE e ATC MODEL passam a ser declaradas com a unidade nula esperada pelo SDK do MSFS, em vez da cadeia literal NULL que produzia silenciosamente um valor vazio.
- Página Aircraft: a identidade principal passa a seguir em direto a aeronave realmente carregada no MSFS, recorrendo automaticamente a ATC MODEL quando um add-on deixa TITLE vazio; a aeronave planeada no SimBrief permanece claramente separada para os pesos e desempenhos do OFP.
- Luzes exteriores: o NaviXav cruza agora as sete SimVars individuais com a máscara oficial LIGHT STATES do MSFS; as aeronaves complexas que publicam apenas o estado agregado voltam a mostrar os indicadores e a acionar corretamente os alertas, com retorno automático à leitura anterior se a máscara estiver indisponível.
- Acompanhamento do voo: o novo sinóptico Configuração da aeronave fica agora estritamente limitado ao seu próprio bloco e deixa de ampliar ou desorganizar os cartões de acompanhamento em tempo real.
- O modo Demo foi removido: o NaviXav passa a utilizar exclusivamente o último plano SimBrief e os dados de voo reais fornecidos pelo MSFS através do SimConnect.
- Interface guiada: a faixa horizontal da rota passa a aparecer apenas no menu Plano de voo e deixa de se sobrepor à faixa superior nos outros módulos; a interface clássica mantém a apresentação habitual.
- Navegação entre módulos: a faixa superior guiada mede agora a altura real da barra de ferramentas e permanece totalmente visível em vez de ficar cortada após mudar de menu.
- Módulo Procedimentos: uma fase composta apenas por lembretes, como a aterragem, deixa de aparecer concluída antes do voo; o seu indicador fica vazio e os seus pontos levam a marca de informação em vez de uma confirmação verde.
- Módulo Procedimentos: uma fase que o voo ainda não atingiu deixa de mostrar confirmações; no estacionamento, o travão de parqueamento e as luzes apagadas já não validam os pontos de depois da aterragem nem de paragem.
- Plano de rolagem: a entrada de partida passa a ser escolhida entre todas as ligações à pista acessíveis a aeronaves, conforme a proximidade à cabeceira pedida. Em CYYZ, uma partida do posto 139 para a pista 23 usa agora AK, A, H e Q em vez de atravessar a pista 15L para chegar à interseção H3. Cada atravessamento de pista confirmado é dividido num ponto de espera explícito e a rota é recusada se essa instrução faltar.
- Tráfego de rede injetado no MSFS: as aeronaves que o simulador descartava em pleno voo são agora detetadas e recriadas no ciclo seguinte, em vez de desaparecerem definitivamente enquanto o NaviXav julgava segui-las.
- O registo anota agora cada alteração de um ciclo de injeção — aeronaves seguidas, recriadas, removidas e descartadas — tornando visível uma injeção que ficara muda.
- O rótulo da opção de injeção já não menciona apenas o VATSIM: nomeia o tráfego de rede, seja qual for a fonte escolhida.
- A fonte real chama-se agora «Tráfego real · OpenSky» nas três listas de escolha, em vez do simples nome do fornecedor, e esse rótulo segue por fim o idioma da interface.
- Uma aeronave situada no local exato da tua deixa de ser mostrada ou injetada: é quase sempre a tua própria, representada pela rede a que estás ligado. O estacionamento vizinho continua visível e um sobrevoo não é confundido com uma sobreposição.
- Uma aeronave que não publica indicativo recebe um genérico e estável, em vez do seu endereço hexadecimal ou de um campo vazio que o simulador mostraria como matrícula em falta.
- A injeção de tráfego passa a ter o seu próprio ciclo de vida: o estado pode ser consultado em vez de ficar fechado no serviço web, pelo que uma injeção parada já não pode passar por saudável.

## Alterações

- Integration trafic.

O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática.
