# NaviXav 1.7.3

Publié le 2026-09-16.

## Nouveautés

- Plans de vol MSFS : NaviXav lit désormais le plan préparé dans le planificateur de MSFS, pour ceux qui n'utilisent pas SimBrief. Un réglage « Source du plan de vol » choisit entre SimBrief et un plan MSFS (.PLN) ; le vol chargé dans MSFS est lu automatiquement et un bouton « Ouvrir un fichier .PLN » permet d'en choisir un autre. Terrains, route, voies aériennes, SID, STAR et pistes prévues sont exploités comme un OFP SimBrief ; la météo est prise en direct. Le premier lancement propose ce choix et n'exige plus de compte SimBrief.
- Diagnostic : la commande « navixav probe-fms » relève ce que l'avion chargé expose de son FMS — le plan de vol du simulateur par SimConnect et, sur le Fenix A320, le plan du FMGC publié par la passerelle locale de l'EFB — et l'écrit dans un rapport à part, en lecture seule.
- Fenix A320 : NaviXav lit le plan de vol actif du FMGC par la passerelle locale de l'EFB Fenix, en lecture seule. Sur la carte, la route du FMS n'est tracée en jaune que là où elle s'écarte de la route NaviXav (DIRECT TO, nouvelle STAR), avec sa légende, et le plan de dégagement s'affiche à la demande ; le T/C et le T/D du FMGC remplacent les estimations (source « FMGC de l'avion ») ; en vol la phase du FMGC remplace celle déduite de la télémétrie. Le suivi du vol gagne le point actif FMGC, l'ETA et les masses FMS, et deux alertes : limite de vitesse 250 kt et point de décélération. La fiche MCDU s'ouvre sur une vérification ligne à ligne de ce que le FMGC contient (FROM/TO, dégagement, numéro de vol, niveau, pistes, SID, route, STAR, approche, ZFW, vitesses de décollage) et se termine par un miroir des MCDU 1 et 2. Le journal de bord retient le numéro de vol et l'ETA du FMGC.
- FlyByWire et PMDG : le miroir MCDU fonctionne aussi sur l'A32NX/A380X (écrans lus par SimBridge, phase FMGC par la variable de l'avion) et sur les 737/777 PMDG (écrans CDU diffusés par le SDK, une fois EnableCDUBroadcast activé). En lecture seule, source affichée dans le miroir ; la commande « navixav probe-fms » indique quel canal répond.

## Corrections

- Carte : le repère TOC ne suit plus l'avion. Il se fige là où la montée s'arrête réellement, même si le contrôle a donné un niveau différent de celui du plan, et n'est recalculé qu'en cas de montée reprise (step climb). Relancé en cours de vol, NaviXav ne place plus le TOC sous l'avion : il reprend celui du profil SimBrief, ou ne l'affiche pas. Avec un plan MSFS, le vol est reconnu à son contenu et non à la date du fichier, que MSFS réécrit à chaque chargement : le journal de vol et le TOC retrouvé survivent à un redémarrage.
- Alertes : l'alerte « Ouverture dangereuse détectée », reprise du signal de sécurité de MSFS, est retirée. Elle se déclenchait sur des portes ou trappes que le pilote ouvre volontairement au sol.

## Modifications

- News.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
