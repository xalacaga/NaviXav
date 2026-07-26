# NaviXav

**Documentação:** [Français](README.md) · [English](README.en.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · Português · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav é um assistente IFR local para Microsoft Flight Simulator. Obtém
automaticamente o último OFP SimBrief, completa a informação terminal com dados
do simulador e apresenta os valores necessários à preparação do voo e
introdução no MCDU.

A aplicação utiliza uma janela Windows própria e adaptável baseada no Microsoft
WebView2. Não abre um navegador externo. O serviço privado escuta apenas em
`127.0.0.1`; definições, dados de navegação, cartas e caches permanecem no
computador.

> NaviXav destina-se exclusivamente à simulação de voo. Confirme sempre os
> dados nas publicações oficiais atuais e nas instruções ATC aplicáveis.

## Funcionalidades

- obtenção automática do último plano de voo SimBrief;
- Pilot ID ou nome de utilizador SimBrief configurado na interface;
- rota completa com progresso da aeronave;
- seleção justificada de pista, SID, STAR, transições e aproximação;
- restrições de altitude/velocidade, altitude e nível de transição, ILS,
  altitude de interceção e de aproximação falhada;
- dados da aeronave, despacho, pesos, combustível e MCDU;
- QNH apresentado sob os dados do vento;
- acompanhamento MSFS em tempo real e trajetória local reproduzível;
- rota desenhada sobre um mapa OpenStreetMap;
- acesso direto aos PDF oficiais de partida e chegada;
- sobreposição da carta apenas com georreferenciação validada;
- navegação diretamente do MSFS, sem Little Navmap, Navigraph ou EUROCONTROL.

## Requisitos e instalação

- Windows 10 ou 11 de 64 bits;
- Microsoft Flight Simulator para dados em direto e navegação;
- conta SimBrief com um OFP já gerado;
- Internet para SimBrief, mapa e publicações AIS/FAA.

Execute `NaviXav-Setup-0.1.0.exe`, confirme os pré-requisitos e escolha
**Instalar**. Python e as bibliotecas estão incluídos. WebView2 só é instalado
se estiver ausente. Também pode extrair o arquivo portátil e executar
`NaviXav.exe`.

### SimConnect autónomo

NaviXav nunca instala, regista, reinstala ou substitui o SimConnect do Windows.
Inclui uma `SimConnect.dll` moderna e privada na sua própria pasta. Qualquer
instalação existente permanece intacta. O MSFS deve estar em execução porque o
conector privado comunica com o serviço SimConnect do simulador.

## Primeira configuração

Em **Definições**, escolha o idioma, introduza o Pilot ID ou utilizador
SimBrief e configure a fonte METAR e preferências de aproximação, pista e
aeronave. O idioma é aplicado imediatamente e guardado localmente. Estão
disponíveis francês, inglês, alemão, espanhol, italiano, português, neerlandês
e polaco.

Ao iniciar, NaviXav procura sempre o último OFP disponível. A geração do plano
continua a ser feita no sítio Web do SimBrief.

## Cartas oficiais

O separador **Cartas oficiais** propõe documentos de partida e chegada de
fontes suportadas como SIA, ENAIRE, LVNL e FAA d-TPP. Os PDF podem ser
visualizados no NaviXav. O botão de sobreposição fica oculto quando o
alinhamento geográfico não foi validado.

## Código-fonte e distribuição

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Para construir:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

O instalador, arquivo portátil e somas SHA-256 são criados em `release\`. O SDK
SimConnect do MSFS só é necessário no computador de compilação.

## Resolução de problemas e privacidade

- Sem plano: confirme a identificação SimBrief, o OFP e a Internet.
- Indicador MSFS vermelho: inicie o MSFS, carregue o voo e aguarde.
- Janela não abre: use o instalador completo para reparar o WebView2.
- Porta 8765 ocupada: feche a instância NaviXav anterior.

NaviXav não envia telemetria. Definições, caches e histórico permanecem no
computador; apenas SimBrief, OpenStreetMap e as fontes oficiais solicitadas são
contactados.

O registo de diagnóstico rotativo encontra-se em
`%LOCALAPPDATA%\NaviXav\logs\navixav.log`. Contém erros e tempos, mas não o
identificador SimBrief nem a rota completa.

## Funcionamento detalhado

### Plano de voo e procedimentos

Ao iniciar, o NaviXav obtém o último OFP gerado no SimBrief: partida, destino,
alternante, rota, nível de cruzeiro, aeronave, combustível, pesos e METAR. A
geração do plano continua no SimBrief. Os dados lidos diretamente do MSFS
completam pista, SID, transição, STAR e aproximação; uma autorização ATIS ou
ATC diferente pode ser imposta na interface. O bloco Partida–Rota–Chegada pode
ser recolhido e o waypoint ativo muda de cor durante o progresso.

### Orientação, aproximação e MCDU

A orientação mostra distância, rumo, altitude prevista, próxima restrição,
velocidade no solo (GS) e velocidade indicada (IAS). Quando disponíveis, mostra
frequência e curso ILS, ângulo de descida, altitude de interceção, elevação da
cabeceira, mínimos e altitude de aproximação falhada. A carta oficial e o ATC
prevalecem sempre.

A ficha MCDU agrupa valores para INIT, F-PLN, RAD NAV, PERF TAKEOFF e PERF APPR:
aeroportos, voo, cost index, cruzeiro, pistas, procedimentos, transições, ILS,
QNH, vento, temperatura, mínimos e dados de descolagem conhecidos.

### Mapa, gravação e documentos oficiais

A rota SimBrief é desenhada sobre OpenStreetMap com estilos distintos para SID,
rota, STAR e aproximação. Os detalhes do solo são filtrados conforme o zoom. O
rasto local pode ser reproduzido e nunca é enviado para um servidor.

Partida e chegada são pré-selecionadas para os PDF oficiais. São suportados SIA
França, ENAIRE Espanha, LVNL Países Baixos e FAA d-TPP EUA. O botão de camada
só aparece com georreferenciação validada; um PDF normal continua disponível
para leitura, mas não é alinhado aproximadamente.

### Dados locais e cache

As definições ficam em `%LOCALAPPDATA%\NaviXav\user_settings.json`, a navegação
em `%LOCALAPPDATA%\NaviXav\navixav.sqlite` e os registos sob
`%LOCALAPPDATA%\NaviXav\logs`. O primeiro carregamento de um aeroporto ou
procedimento pode demorar várias dezenas de segundos ao preencher a cache MSFS.

## Atualizações automáticas e Releases

Ao iniciar, o NaviXav consulta a última Release pública de `xalacaga/NaviXav`.
Se for mais recente, aparece **Atualizar**. Após confirmação, o instalador é
transferido para `%LOCALAPPDATA%\NaviXav\updates`, verificado com o SHA-256
publicado e executado. Uma falha de rede não bloqueia as funções de voo.

O repositório é público para leitura; só colaboradores autorizados podem
escrever. As versões seguem `MAJOR.MINOR.PATCH`: `feat:` incrementa minor,
`fix:` patch e `BREAKING CHANGE` ou `!:` major. As notas ficam em
`RELEASE_NOTES.md` e o histórico em `CHANGELOG.md`.

```powershell
.\scripts\prepare_release.ps1 -Bump auto
.\scripts\publish_release.ps1 -Bump auto
```

A publicação requer um repositório limpo e GitHub CLI autenticado. O script
testa, compila, cria a tag e publica instalador, arquivo portátil, SHA-256 e
notas.

## Comandos de diagnóstico

```powershell
.\NaviXav.bat
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
.\scripts\build_windows.ps1
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```
