# NaviXav 1.7.3

Publicado em 2026-09-16.

## Novidades

- Planos de voo do MSFS: o NaviXav lê agora o plano preparado no planeador do MSFS, para os pilotos que não usam o SimBrief. Uma definição «Origem do plano de voo» escolhe entre o SimBrief e um plano do MSFS (.PLN); o voo carregado no MSFS é lido automaticamente e um botão «Abrir um ficheiro .PLN» permite escolher outro. Aeroportos, rota, aerovias, SID, STAR e pistas previstas são usados como um OFP do SimBrief; a meteorologia é obtida em direto. O primeiro arranque propõe esta escolha e já não exige uma conta SimBrief.
- Diagnóstico: o comando «navixav probe-fms» regista o que o avião carregado expõe do seu FMS — o plano de voo do simulador via SimConnect e, no Fenix A320, o plano do FMGC publicado pelo gateway local do EFB — num relatório à parte, apenas de leitura.
- Fenix A320: o NaviXav lê o plano de voo ativo do FMGC através do gateway local do EFB Fenix, apenas leitura. No mapa, a rota FMS é traçada a amarelo apenas onde se afasta da rota NaviXav (DIRECT TO, nova STAR), com a sua entrada na legenda, e o plano de alternante mostra-se a pedido; o T/C e o T/D do FMGC substituem as estimativas (fonte «FMGC do avião»); em voo a fase do FMGC substitui a deduzida da telemetria. O acompanhamento do voo ganha o ponto ativo do FMGC, a ETA e as massas FMS, mais dois alertas: limite de velocidade 250 kt e ponto de desaceleração. A ficha MCDU abre com uma verificação linha a linha do que o FMGC contém (FROM/TO, alternante, número de voo, nível, pistas, SID, rota, STAR, aproximação, ZFW, velocidades de descolagem) e termina com um espelho dos MCDU 1 e 2. O diário de bordo guarda o número de voo e a ETA do FMGC.
- FlyByWire e PMDG: o espelho do MCDU funciona também no A32NX/A380X (ecrãs lidos pelo SimBridge, fase FMGC pela variável do avião) e nos PMDG 737/777 (ecrãs do CDU difundidos pelo SDK depois de ativar EnableCDUBroadcast). Apenas leitura, com a origem indicada no espelho; o comando «navixav probe-fms» indica qual o canal que responde.

## Correções

- Mapa: a marca TOC deixa de seguir o avião. Fica fixa onde a subida termina realmente, mesmo que o ATC tenha atribuído um nível diferente do planeado, e só é recalculada se a subida for retomada (step climb). Reiniciado em voo, o NaviXav deixa de colocar o TOC sob o avião: usa o do perfil SimBrief ou não o mostra. Com um plano do MSFS, o voo é reconhecido pelo seu conteúdo e não pela data do ficheiro, que o MSFS reescreve a cada carregamento: o registo de voo e o TOC recuperado sobrevivem a um reinício.
- Alertas: o alerta «Abertura perigosa detetada», retirado do sinal de segurança do MSFS, foi removido. Disparava com portas ou escotilhas que o piloto abre de propósito no solo.

## Alterações

- News.

O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática.
