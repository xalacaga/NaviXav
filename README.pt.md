# NaviXav

**Site oficial:** [navixav.fr](https://navixav.fr/en)

**Documentação:** [Français](README.fr.md) · [English](README.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · Português · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

O NaviXav é uma aplicação local de assistência ao voo IFR para o Microsoft
Flight Simulator. Obtém o último plano de voo do SimBrief, completa as
informações terminais com os dados do simulador e apresenta tudo numa interface
concebida para a preparação do voo e a introdução no MCDU.

A aplicação possui a sua própria janela do Windows. A interface é apresentada
pelo Microsoft WebView2 e comunica apenas com um serviço local associado a
`127.0.0.1`. Um navegador externo só é aberto quando o utilizador seleciona
**Criar plano SimBrief** para abrir o editor oficial. As definições, a base de
navegação e as caches permanecem no computador.

A janela é totalmente redimensionável. A interface reorganiza os seus painéis,
comandos, separadores e a altura do mapa consoante o espaço disponível, até um
tamanho mínimo de 720 × 560 píxeis.

> O NaviXav destina-se exclusivamente à simulação de voo. As informações
> apresentadas devem ser verificadas com as publicações oficiais e as
> instruções ATC aplicáveis.

## Funcionalidades

### Plano de voo SimBrief

- obtenção automática do último OFP no arranque;
- suporte do Pilot ID ou do nome de utilizador SimBrief;
- apresentação da rota completa, da origem ao destino;
- destaque do próximo ponto de rota conforme a posição real da aeronave, com
  atenuação dos pontos já ultrapassados;
- massas, combustível, tempo de voo, alternante e dados de despacho;
- informações sobre a aeronave, matrícula e equipamento declarado.

### Meteorologia do voo

- METAR e TAF essenciais para partida, chegada e alternante;
- vento e temperatura de cruzeiro provenientes do OFP SimBrief;
- no modo **METAR em direto**, atualização automática a cada cinco minutos a
  partir de aviationweather.gov e botão de atualização imediata;
- representação gráfica das condições, vento, visibilidade e teto sem alterar
  automaticamente a pista ou os procedimentos do plano.

### Preparação IFR

O NaviXav completa e apresenta:

- a pista de partida e a pista de chegada;
- a SID e a sua transição;
- a STAR e a sua transição;
- a aproximação e a sua VIA;
- a frequência e o identificador ILS;
- as restrições de altitude e de velocidade;
- a altitude de transição e o nível de transição;
- a altitude de interceção da aproximação;
- a altitude de aproximação falhada;
- a justificação e o nível de confiança de cada escolha.

Os blocos **Partida · Rota · Chegada** podem ser recolhidos para libertar
espaço na interface.

### Seguimento do voo

O separador **Seguimento do voo** utiliza a posição MSFS em tempo real para
apresentar:

- a fase de voo detetada automaticamente;
- a velocidade em relação ao solo (GS) e a velocidade indicada (IAS) fornecidas
  pelo MSFS;
- o próximo ponto e a sua distância;
- o desvio lateral em relação ao segmento ativo;
- a distância restante;
- a próxima restrição de altitude ou de velocidade;
- a razão vertical necessária para atingir essa restrição;
- o Top of Descent e uma razão de descida indicativa numa rampa de 3°;
- o desvio em relação ao perfil vertical previsto.

Após a aterragem, o diário local guarda um resumo conciso e uma cronologia
limitada de eventos: fases do voo, pista de descolagem e aterragem com o vento
observado, e alterações estáveis do trem, flaps, spoilers, travão de
estacionamento, luzes e modos do piloto automático. Os eventos são guardados
como dados e reproduzidos no idioma selecionado nesse momento. Todos os resumos
podem ser eliminados na interface e nenhum dado de voo é enviado para serviços
externos.

Para flaps, spoilers e travão de estacionamento, o NaviXav cruza as SimVars
oficiais da alavanca, posição efetiva, superfície e indicador do cockpit. A
configuração da aeronave e os eventos de voo continuam assim a atualizar-se
quando uma aeronave de terceiros deixa um valor padrão do MSFS bloqueado.
Um adaptador dedicado aos Fenix A319/A320/A321 lê diretamente os três comandos
do cockpit, pelo que alterações nos flaps, spoilers e travão de estacionamento
são registadas mesmo com os motores e sistemas hidráulicos desligados.

### Ficha MCDU

O separador **Ficha MCDU** adapta as páginas ao tipo de aeronave: MCDU Airbus,
CDU Boeing ou FMS genérico para as restantes aeronaves. Não apresenta
desempenhos de descolagem que não possam ser automatizados:

- `FROM/TO`, número de voo e alternante;
- Cost Index e nível de cruzeiro;
- ZFW, combustível de bloco, rolagem, trajeto e reservas;
- pista, SID, transição e altitude de transição;
- rota `VIA/TO`;
- STAR, transição, aproximação e VIA;
- QNH, temperatura, vento, frequência ILS e rumo final;
- mínimos RADIO ou BARO e RVR.

### Ligação direta ao MSFS

O NaviXav utiliza o SimConnect para:

- detetar a presença do simulador;
- apresentar um indicador verde ou vermelho na barra superior;
- seguir a posição da aeronave em tempo real;
- ler a altitude, a altura acima do solo, o rumo, a velocidade em relação ao
  solo e a velocidade vertical;
- obter aeroportos, pistas, procedimentos, pontos de notificação e
  radioajudas;
- construir progressivamente uma base local em `data/navixav.sqlite`.

O simulador deve estar iniciado com um voo carregado para obter novos dados. As
informações já colocadas em cache permanecem disponíveis sem ligação.

Quando o registo de navegação detalhado do SimBrief fornece coordenadas
validadas, o NaviXav utiliza-as imediatamente para desenhar a rota e consulta
o MSFS Facilities apenas para as posições em falta. As ligações publicadas das
proceduras também evitam consultas de posição desnecessárias. Assim, o primeiro
carregamento do plano é mais rápido, mantendo as verificações do corredor e a
cache local do MSFS como alternativa.

### Mapa

O mapa inclui:

- um fundo OpenStreetMap;
- a rota SimBrief desenhada com os seus pontos;
- cores distintas para a SID, a parte em rota, a STAR e a aproximação;
- as pistas e a pista selecionada;
- a posição e o rumo da aeronave;
- um rasto do deslocamento;
- um modo de seguimento automático;
- o zoom, o deslocamento e o ajuste ao aeroporto ou à rota.

### Rolagem no solo

O separador **Rolagem** apresenta um plano de aeródromo dedicado, separado do
mapa de voo e construído apenas com as instalações nativas do MSFS:

- o canvas ocupa todo o espaço disponível, mesmo em janelas compactas;
- um fundo aeronáutico escuro com grelha métrica e seta do norte fornece escala
  e orientação sem o ruído de um mapa rodoviário;
- pistas, caminhos principais, estacionamentos e aeronave têm prioridade visual;
- os caminhos de circulação com nome permanecem visíveis mesmo quando o MSFS
  os classifica como segmentos genéricos `path`; apenas as ligações secundárias
  sem nome e os acessos aos estacionamentos ficam ocultos por predefinição, e
  o botão **Secundários** mostra-os a pedido;
- à partida, se a aeronave estiver no solo a menos de 180 m de um estacionamento,
  o NaviXav propõe automaticamente a rota até à pista selecionada;
- clicar noutro estacionamento substitui imediatamente a proposta; à chegada,
  o estacionamento de destino continua a ser uma escolha manual;
- são mostrados o trajeto percorrido e restante, nomes úteis, pontos de espera,
  próxima manobra e distância restante;
- após um desvio, a rota é recalculada a partir da posição real da aeronave.

Os caminhos de estacionamento SimConnect servem apenas para ligar os postos à
rede e nunca podem criar atalhos artificiais através das pistas.

### Cartas AIS nacionais oficiais

O NaviXav consulta diretamente as publicações das autoridades nacionais, sem
passar pelo EUROCONTROL/EAD:

- França: SIA eAIP (`LF`);
- Espanha e Canárias: AIP da ENAIRE (`LE`, `GC`, `GE`);
- Países Baixos: LVNL eAIP (`EH`);
- Suécia: LFV eAIP (`ES`);
- Bélgica e Luxemburgo: skeyes eAIP (`EB`, `EL`);
- Áustria: Austro Control eAIP (`LO`);
- Reino Unido: NATS eAIP (`EG`);
- Estados Unidos e territórios abrangidos: FAA d-TPP.

Para estes aeródromos, o NaviXav pode:

- apresentar no separador **Cartas oficiais** todos os PDF da partida e da
  chegada, classificados por tipo;
- abrir cada documento na interface ou em separado;
- selecionar por predefinição a SID, a STAR ou a aproximação correspondente ao
  voo atual;
- encontrar automaticamente a carta de aproximação correspondente à pista e ao
  tipo de aproximação escolhidos;
- transferir a pedido apenas os PDF consultados;
- conservar a publicação na cache AIRAC local;
- apresentar a carta oficial na ficha MCDU;
- extrair os mínimos ILS CAT I do SIA quando o formato é reconhecido;
- propor a DA, a DH e a RVR antes da validação.

Os valores extraídos nunca são aplicados de forma silenciosa: devem ser
validados na interface. O botão **Camada oficial** só é proposto para um
documento com georreferenciação validada. Segue a escolha da carta: o PDF da
partida só pode ser sobreposto à partida e o da chegada à chegada. Esta regra é
idêntica para todas as fontes.

Um país só é acrescentado à lista automática após validação de um acesso direto
e estável aos seus PDF oficiais. Uma fonte ausente nunca é, portanto,
substituída em silêncio por um agregador de terceiros.

## Requisitos

- Windows 10 ou Windows 11 de 64 bits;
- Microsoft WebView2 Runtime, instalado automaticamente pelo instalador;
- Microsoft Flight Simulator para os dados e o seguimento em tempo real;
- uma conta SimBrief com um OFP gerado;
- uma ligação à Internet para o SimBrief, o fundo cartográfico e as publicações
  AIS nacionais ou da FAA.

O instalador inclui o Python, as bibliotecas, o pywebview, o conector
SimConnect autónomo do NaviXav e o bootstrapper Microsoft WebView2 assinado.
Nenhuma destas ferramentas tem de ser instalada separadamente. O MSFS não é
obrigatório para experimentar o modo Demo ou consultar os dados já guardados.

O SimConnect nunca é instalado nem reinstalado no Windows pelo NaviXav. A
aplicação incorpora uma cópia privada da DLL moderna na sua própria pasta. Se a
máquina já possuir o SimConnect, a sua instalação, a sua versão e as suas
definições não são substituídas nem modificadas. Esta DLL privada dialoga com o
serviço SimConnect do MSFS: apenas o simulador tem de estar instalado e
iniciado para receber os dados em direto.

### Idiomas da interface

O idioma escolhe-se em **Definições**, aplica-se de imediato e fica memorizado
no computador. O NaviXav disponibiliza as interfaces em francês, inglês,
alemão, espanhol, italiano, português, neerlandês e polaco. As abreviaturas
aeronáuticas, os identificadores de procedimentos, os METAR e os valores MCDU
mantêm-se deliberadamente na sua notação internacional.

## Instalação rápida no Windows

1. Transferir o ficheiro `NaviXav-Setup-<versão>.exe` da última
   [Release do GitHub](https://github.com/xalacaga/NaviXav/releases/latest).
2. Executar o instalador.
3. Verificar a página de controlo dos requisitos.
4. Manter ou alterar a pasta proposta e clicar em **Instalar**.
5. Iniciar o NaviXav a partir do menu Iniciar ou do atalho opcional do ambiente
   de trabalho.

O instalador verifica o Microsoft WebView2 e instala-o automaticamente se
faltar. A instalação é feita para o utilizador atual e normalmente não exige
direitos de administrador.

Está igualmente disponível um arquivo portátil: extrair
`NaviXav-<versão>-windows-x64-portable.zip` e executar `NaviXav.exe`. Numa
máquina sem WebView2, utilizar primeiro o instalador completo.

### A partir do código-fonte

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

No primeiro arranque, o script:

1. procura o Python;
2. cria o ambiente virtual `.venv`;
3. instala o NaviXav e as suas dependências;
4. inicia o serviço local privado;
5. abre a interface na janela do NaviXav.

Os arranques seguintes reutilizam o ambiente já instalado.

### Construir uma distribuição

A partir do PowerShell, na pasta do projeto:

```powershell
.\scripts\build_windows.ps1
```

O script:

1. verifica o Windows de 64 bits, o Python e o SDK SimConnect;
2. instala as ferramentas de construção em falta;
3. obtém o bootstrapper WebView2 oficial e verifica a sua assinatura
   Microsoft;
4. executa os testes excluindo a integração MSFS em direto;
5. produz o instalador, o arquivo portátil e as suas somas SHA-256 em
   `release\`.

O SDK SimConnect mencionado no passo 1 diz respeito apenas à máquina que
constrói o NaviXav. Não é instalado nas máquinas dos utilizadores.

### Ficheiros de distribuição

Após uma construção bem-sucedida:

| Ficheiro | Utilização |
|---|---|
| `release\NaviXav-Setup-<versão>.exe` | instalador Windows recomendado |
| `release\NaviXav-<versão>-windows-x64-portable.zip` | versão portátil |
| `release\*.sha256` | impressões de controlo dos ficheiros distribuídos |

A pasta `release\` é deliberadamente ignorada pelo Git. Os executáveis são
artefactos de construção a publicar numa Release do GitHub, não fontes a
versionar.

## Instalação manual

A partir do PowerShell, na pasta do projeto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

Este comando abre a janela do NaviXav. Para um diagnóstico do serviço local sem
janela:

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

O serviço permanece então acessível apenas em `http://127.0.0.1:8765`.

## Configuração

A configuração corrente faz-se a partir do botão **Definições** da interface.

### Conta SimBrief

Preencher um dos dois campos:

- **Pilot ID SimBrief**: identificador numérico apresentado nas definições da
  conta SimBrief;
- **Nome de utilizador SimBrief**: alias da conta.

O Pilot ID é recomendado. Após a gravação, o NaviXav obtém imediatamente o
último OFP disponível. Em cada novo arranque, esse último plano é carregado
automaticamente.

### Definições disponíveis

A interface permite igualmente configurar:

- a fonte METAR;
- a ordem de preferência das aproximações;
- a componente máxima de vento de cauda;
- a componente máxima de vento cruzado;
- o comprimento mínimo de pista;
- a capacidade RNP da aeronave.

Na versão instalada, os valores são conservados em
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

## Primeira utilização

1. Gerar um plano de voo no SimBrief.
2. Iniciar o Microsoft Flight Simulator e carregar um voo.
3. Iniciar o NaviXav a partir do menu Iniciar, ou com `NaviXav.bat` em modo de
   desenvolvimento.
4. Abrir **Definições** e guardar o Pilot ID SimBrief.
5. Aguardar o carregamento automático do último OFP.
6. Verificar o indicador **MSFS ligado** no canto superior direito.
7. Controlar as escolhas de pista, SID, STAR e aproximação.
8. Consultar as restrições e a carta oficial.
9. Validar os mínimos antes de os copiar para o MCDU.

O botão **Completar o plano** permite obter novamente o último OFP após gerar
ou modificar um voo no SimBrief.

## Utilização do mapa

- **Fundo do mapa**: apresenta ou oculta o OpenStreetMap.
- **Rolagem**: abre o plano de solo dedicado; **Secundários** mostra ou oculta
  os acessos e caminhos de menor prioridade.
- **Camada oficial**: aparece apenas para a carta georreferenciada do aeródromo
  atualmente apresentado e regula a sua opacidade.
- **Rota completa**: enquadra toda a rota do voo.
- **Seguir**: mantém a aeronave ao centro.
- **Ajustar**: enquadra o aeroporto selecionado.
- **+ / −**: modifica o nível de zoom.
- **Roda**: amplia sob o ponteiro.
- **Arrastar**: desloca o mapa.

Os botões de aeroporto permitem passar rapidamente do aeródromo de partida ao
de chegada.

## Janela e apresentação adaptável

### Acesso por telefone e tablet na rede local

Ative **Acesso por telefone e tablet** em **Configuração**, guarde e reinicie o
NaviXav. Abra o endereço protegido apresentado no PC num dispositivo ligado ao
mesmo Wi-Fi. A interface móvel disponibiliza seguimento em tempo real, mapa,
restrições, dados do MCDU, da aeronave e cartas oficiais. A configuração, o
encerramento e as atualizações permanecem reservados ao PC. Se o Windows
perguntar, autorize o NaviXav apenas em redes privadas.

Em ecrãs remotos com menos de 760 px, o estado da ligação ao MSFS é reduzido
ao ponto colorido, para que `MSFS connected` não ultrapasse a barra de
ferramentas. A etiqueta traduzida continua disponível para tecnologias de
assistência. A barra móvel também disponibiliza o seu próprio seletor de idioma
sem expor as definições reservadas ao PC.

O NaviXav adapta automaticamente a sua interface ao redimensionamento:

- acima de 1100 px, a navegação entre módulos passa para uma barra flutuante
  compacta no canto superior esquerdo, com um indicador ativo claro; a entrada curta **Plano de
  voo** abre Partida, Rota e Chegada como um módulo exclusivo normal, sem
  comando de recolher, fica selecionada por predefinição e cada escolha desloca diretamente para o conteúdo. A
  área principal usa toda a largura restante e um PDF oficial aberto ocupa a
  grelha completa. As janelas mais estreitas mantêm o seletor horizontal e os
  ecrãs móveis o painel lateral acessível. Quando um alerta global de voo adiciona
  uma segunda linha ao cabeçalho, a barra do ambiente de trabalho desce
  automaticamente e volta a subir depois de o alerta desaparecer;
- acima de 1100 px, os cartões Partida, Rota e Chegada podem ser apresentados
  lado a lado;
- abaixo de 1100 px, estes cartões passam para uma única coluna;
- abaixo de 980 px, a barra de ferramentas e os comandos do mapa ocupam toda a
  largura disponível;
- abaixo de 760 px, os separadores tornam-se deslizáveis, os botões
  redistribuem-se e as tabelas continuam consultáveis na horizontal;
- abaixo de 520 px, as estatísticas e os painéis complexos passam para coluna.

O mapa deteta cada alteração de tamanho da janela e recalcula imediatamente a
sua tela. O tamanho mínimo da janela nativa é de 720 × 560 píxeis.

## Modo Demo

O comutador **Demo** carrega um voo de exemplo e simula um deslocamento no
solo. Permite descobrir a interface sem conta SimBrief nem simulador.

O modo Demo está sempre desativado no arranque, para que o NaviXav dê
prioridade ao último plano SimBrief.

## Encerramento da aplicação

Utilizar o botão **Sair** na barra superior. O NaviXav encerra corretamente o
servidor, fecha a janela e a ligação SimConnect e liberta a porta `8765`.
Fechar diretamente a janela produz o mesmo resultado.

No modo de diagnóstico `--no-open`, a combinação `Ctrl+C` na consola também
efetua um encerramento normal.

## Opções de arranque

O lançador do Windows aceita as seguintes opções:

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` altera a porta local;
- `--no-open` inicia apenas o serviço local, para diagnóstico.

O endereço de escuta permanece deliberadamente fixado em `127.0.0.1`.

## Comandos complementares

O NaviXav também pode ser utilizado a partir do PowerShell:

```powershell
# Apresentar o último plano SimBrief
.\.venv\Scripts\navixav.exe plan

# Gerar uma ficha MCDU textual
.\.venv\Scripts\navixav.exe plan --mcdu

# Produzir uma saída JSON
.\.venv\Scripts\navixav.exe plan --json

# Importar aeroportos do MSFS
.\.venv\Scripts\navixav.exe import LFBO LFPO

# Examinar a base local
.\.venv\Scripts\navixav.exe navdata

# Apresentar as informações de um aeroporto
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Dados locais

O NaviXav utiliza as seguintes localizações:

| Localização | Conteúdo |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | configuração da versão instalada |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | base de navegação construída a partir do MSFS |
| `%LOCALAPPDATA%\NaviXav\cache\` | cartas AIS nacionais e da FAA em cache |
| `%LOCALAPPDATA%\NaviXav\webview\` | armazenamento local da janela WebView2 |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | registo da versão instalada |
| `data\` e `.venv\` | dados e ambiente do modo de desenvolvimento |

Estes dados locais, os segredos e as caches não se destinam a ser versionados.

O registo anota os arranques e encerramentos, os erros, as chamadas API lentas,
os tempos de obtenção do SimBrief, os tempos de conclusão MSFS e os
preenchimentos da cache. Não anota o Pilot ID, nem o nome de utilizador, nem a
rota completa. O seu tamanho está limitado a 2 MB, conservando cinco versões
anteriores (`navixav.log.1` a `navixav.log.5`).

No primeiro acesso a um aeródromo ou a um procedimento, a interface avisa que a
cache MSFS está a ser preenchida e que a operação pode demorar várias dezenas
de segundos. Os acessos seguintes reutilizam os dados locais.

## Versionamento Git

O repositório de origem está previsto para ser alojado em:
`https://github.com/xalacaga/NaviXav.git`.

O ficheiro `.gitignore` exclui nomeadamente:

- `.env`, as definições de utilizador e as bases locais;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` e `CODEX.md`;
- os dados Graphify e `graphify-out/`;
- os ambientes Python, as caches de testes e as saídas de construção;
- `dist\`, `build\` e `release\`.

As memórias Claude/Codex podem assim ser mantidas localmente sem serem
publicadas no repositório Git.

### Atualizações automáticas

No arranque, o NaviXav consulta apenas a última Release pública do repositório
`xalacaga/NaviXav`. Se a sua versão for superior à instalada, aparece um botão
**Atualização** na barra superior. A instalação só começa após confirmação do
utilizador.

O instalador é transferido para `%LOCALAPPDATA%\NaviXav\updates\` e a sua
impressão SHA-256 é depois comparada com a publicada pelo GitHub. Em caso de
impressão ausente ou diferente, o ficheiro é eliminado e nunca é executado. Uma
avaria do GitHub ou da Internet não bloqueia o arranque nem as funções de voo.

O repositório é público em leitura. Um utilizador pode consultar o código e
transferir as Releases sem conta GitHub, mas apenas os colaboradores
autorizados podem escrever no repositório.

### Versão e notas de Release

A versão segue o formato semântico `MAIOR.MENOR.CORREÇÃO`. As mensagens de
commit convencionais determinam automaticamente o nível seguinte:

- `feat:` produz normalmente uma versão menor;
- `fix:` produz uma versão de correção;
- `BREAKING CHANGE` ou `!:` produz uma versão maior;
- as restantes alterações produzem uma versão de correção.

Preparar localmente a versão e as suas notas:

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Publicar o instalador, o arquivo portátil, as suas impressões e as notas numa
Release do GitHub:

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

O segundo script exige um repositório limpo e o GitHub CLI autenticado. Executa
os testes, constrói os entregáveis, cria o commit e a etiqueta de versão, envia
`main` e a etiqueta e depois cria a Release do GitHub. O `CHANGELOG.md` conserva
o histórico e o `RELEASE_NOTES.md` contém as notas da versão atual.

## Resolução de problemas

### A porta 8765 já está a ser utilizada

Provavelmente ainda está aberta uma instância do NaviXav. Fechar a sua janela
ou clicar em **Sair** na interface. O executável deteta uma instância
existente; se outra aplicação ocupar a 8765, escolhe automaticamente uma porta
livre entre 8766 e 8775.

Para identificar o processo:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

Também é possível iniciar a aplicação noutra porta:

```powershell
.\NaviXav.bat --port 9000
```

### A janela do NaviXav não abre

- executar novamente o instalador completo para que verifique o WebView2;
- verificar se o Windows e o Microsoft Edge WebView2 Runtime estão
  atualizados;
- consultar `%LOCALAPPDATA%\NaviXav\logs\navixav.log`;
- verificar se um antivírus não está a bloquear o `NaviXav.exe` ou os processos
  `msedgewebview2.exe`.

O arquivo portátil não consegue instalar o WebView2 sozinho. Numa máquina que
não possua este componente, utilizar `NaviXav-Setup-<versão>.exe`.

### O indicador MSFS permanece vermelho

- verificar se o simulador está iniciado;
- carregar completamente um voo;
- aguardar alguns segundos e depois clicar no indicador;
- executar novamente o instalador se a cópia privada de `SimConnect.dll`
  fornecida com o NaviXav tiver sido eliminada ou colocada em quarentena por um
  antivírus.

### Nenhum plano SimBrief é carregado

- verificar o Pilot ID ou o nome de utilizador em **Definições**;
- gerar um OFP no SimBrief antes de repetir a obtenção;
- verificar a ligação à Internet.

### Uma carta oficial não está disponível

- verificar se o prefixo OACI é abrangido pelo SIA, ENAIRE, LVNL, LFV,
  skeyes, Austro Control, NATS ou FAA;
- verificar a ligação à Internet;
- confirmar que a pista e a aproximação foram determinadas;
- utilizar a introdução manual dos mínimos se a extração não estiver
  disponível.

## Limitações atuais

- o procedimento realmente autorizado pode diferir do plano consoante o ATIS, a
  meteorologia e as instruções ATC;
- os mínimos dependem da categoria da aeronave, do seu equipamento e das
  condições operacionais;
- a extração automática dos mínimos está limitada aos formatos SIA
  reconhecidos;
- um PDF sem georreferenciação validada continua consultável, mas não pode ser
  utilizado como camada;
- os novos dados MSFS exigem que o simulador esteja acessível.

Confirmar sempre as informações importantes antes de as introduzir no
simulador.

## Arquitetura e confidencialidade

- `navixav/desktop.py` gere a janela nativa e o ciclo de vida do processo;
- `navixav/web/app.py` fornece a API FastAPI associada apenas a `127.0.0.1`;
- `navixav/web/static/` contém a interface adaptável HTML/CSS/JavaScript;
- `navixav/planner/` completa o plano IFR;
- `navixav/navdata/` constrói e consulta a base proveniente do MSFS;
- `navixav/live/` assegura o seguimento SimConnect;
- `navixav/sia.py`, `navixav/faa.py` e `navixav/national_aip.py` gerem as
  publicações oficiais.

O serviço local nunca escuta na rede exterior. O Pilot ID SimBrief, as
preferências, os resumos de voo e os PDF em cache permanecem na máquina. Apenas os
pedidos necessários ao SimBrief, ao OpenStreetMap, à meteorologia e às
publicações AIS oficiais saem do computador.

## Licença

O NaviXav é software livre distribuído sob a licença
[Apache 2.0](LICENSE).

Copyright 2026 Xavier BEGUE (xalacaga)

Podes usar, modificar, redistribuir e integrar o NaviXav livremente, incluindo
num projeto comercial. Em contrapartida, a licença obriga a **creditar o
autor**:

- conservar a menção de copyright e uma cópia da licença em qualquer
  redistribuição;
- conservar o ficheiro [NOTICE](NOTICE) e o seu conteúdo de atribuição;
- **assinalar de forma visível qualquer ficheiro que tenhas modificado**, nos
  termos da secção 4(b) da licença.

A licença concede ainda uma licença de patentes e exclui qualquer garantia. Os
dados de navegação, as cartas oficiais e o fundo cartográfico não são cobertos
por esta licença: permanecem sujeitos às condições dos respetivos fornecedores,
detalhadas no ficheiro NOTICE.

## Testes

O perfil reproduzível utilizado para construir a distribuição é:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

Os testes marcados `live_msfs` consultam um simulador realmente iniciado e não
fazem, por isso, parte do controlo automático do instalador.
