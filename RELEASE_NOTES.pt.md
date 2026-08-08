# NaviXav 1.4.16

Publicado em 2026-08-08.

## Correções

- Os speedbrakes dos Fenix A319/A320/A321 agora apresentam ARMED corretamente mesmo quando o nome da aeronave no SimBrief é genérico.
- O Top of Descent é agora um ponto fixo da rota, calculado a partir do nível de cruzeiro: diminui até zero e depois é indicado como ultrapassado. Antes podia ficar parado durante uma descida a 3° ou até aumentar quando a descida era iniciada demasiado cedo.
- O desvio em relação ao perfil de descida continua a ser indicado durante um nivelamento abaixo do nível de cruzeiro. Antes desaparecia assim que a velocidade vertical voltava a zero, precisamente quando a aeronave estava muito abaixo do perfil.
- O Top of Descent passa a ter em conta os tetos de altitude publicados da STAR e da aproximação e lê a altitude na atmosfera padrão como um nível de voo.
- A velocidade vertical necessária para a restrição seguinte passa a ser comparada com a altitude indicada, a única comparável com uma restrição publicada.

## Alterações

- Correction bug TOD.

O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática.
