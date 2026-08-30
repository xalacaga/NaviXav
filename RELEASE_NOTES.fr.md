# NaviXav 1.6.0

Publié le 2026-08-30.

## Nouveautés

- Commandes plus claires : Flight tracking propose désormais un interrupteur visible pour couper ou réactiver toutes les alarmes NaviXav, notamment les messages MASTER WARNING et MASTER CAUTION, sans arrêter le suivi du vol ; après une mise à jour, l’historique des versions s’ouvre automatiquement au premier redémarrage puis reste accessible à la demande.
- Changement instantané de la source trafic depuis les barres Carte et Taxi : les sélecteurs VATSIM, IVAO et OpenSky restent synchronisés, relancent proprement le relevé et enregistrent le choix localement.
- Trafic réel OpenSky : NaviXav peut afficher les vecteurs ADS-B publics dans une zone de 100 NM autour de l’avion, avec attribution de la source et un cache respectueux de l’API ; cette vue réelle reste strictement séparée de l’injection MSFS.
- Paramètres réorganisés en catégories repliables adaptées aux fenêtres compactes, avec chemin FSLTL manuel, accès à l’installateur officiel FlyByWire lorsque les modèles manquent et IVAO comme seconde source de trafic réseau publique et gratuite aux côtés de VATSIM.
- Compatibilité exclusivement MSFS 2024 : NaviXav utilise désormais l’API SimConnect AI EX1 native de MSFS 2024 et refuse au démarrage ou à la construction une ancienne DLL MSFS 2020, au lieu de poursuivre avec une connexion ou des fonctions inadaptées.
- Injection de trafic VATSIM dans MSFS : NaviXav détecte automatiquement FSLTL Base Models dans Community, indexe ses aircraft.cfg et ses règles VMR sans les modifier, choisit le modèle exact ou générique le plus sûr, puis crée, actualise et retire uniquement ses propres objets SimConnect dans une bulle bornée autour du joueur. L’option est désactivée par défaut et l’interface affiche la version FSLTL détectée.
- Trafic environnant : un bouton « Trafic VATSIM » dans la barre de la carte, « Trafic simulateur » dans celle du roulage, affiche les autres appareils. Sur la carte, chaque appareil du réseau est une silhouette orientée au cap avec son indicatif dessous, et un clic ouvre sa fiche : type, fréquence, pilote, terrains de départ et d’arrivée nommés d’après la base MSFS, vitesse sol et altitude. Le plan de roulage montre le trafic du simulateur, seul exact au mètre. Éteint par défaut, aucun appel réseau tant qu’il l’est.
- Profil vertical : le TOD reprend désormais en priorité le point de performances du dernier OFP SimBrief, après validation de ses coordonnées sur la route active ; les plafonds de la STAR et de l’approche restent appliqués, et le calcul géométrique à 3° prend automatiquement le relais si ce point manque ou ne correspond plus à la route.
- Positions VATSIM en ligne : activé dans les paramètres, NaviXav marque d’une pastille les fréquences du terrain dont le poste est tenu, et donne au survol l’indicatif du contrôleur et sa fréquence — celle du réseau n’étant pas toujours celle que publie le simulateur. Réglage désactivé par défaut, aucun appel réseau tant qu’il l’est.
- Fréquences du terrain : la fréquence de départ complète désormais la rangée, et un rôle qui compte plusieurs fréquences l’annonce par un « +n » au lieu de laisser croire qu’il n’y en a qu’une ; le détail de chaque poste, aires de stationnement comprises, se lit au survol.
- Suivi du vol : une seconde pastille annonce la fréquence attendue à la phase en cours et se marque lorsque la radio est déjà dessus. Elle reste muette quand le terrain publie plusieurs fréquences pour le même rôle, faute de savoir laquelle dessert la piste en service.
- Suivi du vol : une pastille radio indique la fréquence composée sur la COM1 et nomme le poste correspondant du terrain, sol de piste compris — de quoi vérifier d’un coup d’œil qu’on a bien tapé la fréquence annoncée.
- Diagnostic : la commande « navixav airport » liste les fréquences du terrain avec le nombre par lequel le simulateur désigne chaque rôle, et signale un rôle qu’elle ne sait pas traduire au lieu de le passer sous silence.
- Fréquences du terrain : les cartes Départ et Arrivée du plan de vol affichent la chaîne radio publiée par MSFS, dans l’ordre où elle se compose — ATIS, DEL, GND, TWR au départ, ATIS, APP, TWR, GND à l’arrivée. Lorsqu’un terrain publie plusieurs fréquences pour un même rôle, les autres se lisent au survol.
- Préparation TOD : à 50 NM, le moteur d’alarmes demande de préparer la descente et met la tuile TOD en évidence ; à 10 NM, une alarme TOD imminent distincte se déclenche et reste active jusqu’à l’engagement de la descente.
- Configuration avion : l'interface guidée adopte un synoptique cockpit plus lisible avec des tuiles équilibrées, un pictogramme par système, un liseré d'état et de véritables voyants pour les feux ; l'interface classique conserve le visuel précédent.
- Nouvelle interface guidée par le vol : un bandeau persistant met en avant la phase, la piste ou procédure, la prochaine action et le module recommandé ; les cartes de départ, d'arrivée et d'approche sont préparées dans un pinboard et le mode Roulage gagne de la place. Le réglage Organisation de l'interface permet de revenir instantanément à l'interface classique, sans redémarrage.
- Plan de roulage : le départ d'un poste nez au terminal commence par un repoussage, tracé en violet et pointillé serré sur le plan et annoncé dans le bandeau avec sa distance et le cap présenté une fois l'avion aligné ; une rampe, un départ repris en cours de roulage ou une arrivée n'en affichent aucun.
- Préparation du plan : le bandeau qui annonce le remplissage du cache MSFS montre désormais un avion qui traverse le cadre, traînée derrière lui, tant que la lecture dure. L'attente pouvait atteindre plusieurs dizaines de secondes sans que rien ne bouge à l'écran.
- Fiche MCDU : NaviXav récupère désormais le ZFWCG de SimBrief et affiche le centrage à masse sans carburant ainsi que le nombre de passagers dans la page des masses ; le ZFWCG apparaît également dans Dispatch.
- Choisir une source de trafic suffit maintenant à l'injecter dans MSFS : l'injection est active par défaut et la case des paramètres ne sert plus qu'à s'en retirer.
- Un repère « carte seule » apparaît sur la barre de la carte quand le trafic est affiché sans être injecté, et son infobulle en donne la raison : injection retirée, FSLTL absent ou source réelle.
- Le trafic réel ADS-B entre enfin dans MSFS : le type de chaque appareil est résolu depuis deux registres publics complémentaires, ce qui permet enfin de lui choisir un modèle FSLTL. Un appareil inconnu au premier relevé apparaît au suivant, le temps que son adresse soit résolue.
- Choisir une source de trafic suffit désormais à l'injecter dans le simulateur. La case « Injecter le trafic réseau dans MSFS » disparaît des paramètres : le bouton du calque est le seul interrupteur, et ce qu'il montre est ce qui vole.

## Corrections

- Les appareils OpenSky au parking restent injectables lorsque leur transpondeur omet l’altitude barométrique, la vitesse ou le cap : NaviXav reprend d’abord l’altitude géométrique puis complète uniquement les données sol manquantes.
- Trafic réel OpenSky dans MSFS : les appareils sans type ADS-B utilisent immédiatement un modèle FSLTL générique sûr au lieu de rester invisibles, puis adoptent leur modèle exact dès que le registre ICAO24 répond ; l’injection actualise désormais leur position chaque seconde.
- Trafic IVAO et OpenSky plus fluide dans MSFS : NaviXav extrapole la position chaque seconde entre deux relevés et conserve brièvement un appareil omis par la source, ce qui évite les disparitions et réapparitions ; le décompte fixe de 15 s, inexact pour ces sources, a été retiré de l’interface.
- Trafic réseau aux portes et au roulage : lorsque VATSIM ne publie pas l’état sol, NaviXav le déduit désormais d’une vitesse inférieure ou égale à 50 kt ; les avions stationnés et au roulage sont injectés au lieu d’être écartés.
- Inventaire des avions : Actualiser détecte maintenant les add-ons pilotables dont isAirTraffic est mal renseigné, comme le Rafale M, et chaque appareil affiche sa propre vignette locale au lieu de réutiliser celle de l'avion chargé.
- Plan de roulage à l’arrivée : la position réelle de l’avion et le cap de la piste écartent désormais les sorties déjà dépassées ; après un atterrissage en 24R, NaviXav ne propose plus de revenir à contresens vers une sortie située derrière l’avion.
- Carte : la partie en route du plan de vol conserve sa couleur violette mais utilise désormais une ligne pleine, plus lisible aux faibles niveaux de zoom.
- Page Aircraft : les longues chaînes d’équipement OACI se replient désormais à l’intérieur de leur tuile au lieu de déborder sur le profil voisin.
- Identité SimConnect : les variables texte comme TITLE et ATC MODEL sont désormais déclarées avec l’unité nulle attendue par le SDK MSFS, au lieu de la chaîne littérale NULL qui produisait silencieusement une valeur vide.
- Page Aircraft : l’identité principale suit désormais en direct l’avion réellement chargé dans MSFS, avec repli automatique sur ATC MODEL lorsqu’un add-on laisse TITLE vide ; l’avion prévu par SimBrief reste clairement séparé pour les masses et performances de l’OFP.
- Feux extérieurs : NaviXav recoupe désormais les sept SimVars individuelles avec le masque officiel LIGHT STATES de MSFS ; les avions complexes qui ne publient que l’état agrégé affichent de nouveau leurs voyants et déclenchent correctement les alarmes, avec retour automatique à l’ancienne lecture si le masque est indisponible.
- Suivi du vol : le nouveau synoptique Configuration avion est désormais strictement isolé à son propre bloc et ne grossit plus ni ne désorganise les tuiles du suivi temps réel.
- Le mode Démo a été supprimé : NaviXav utilise désormais exclusivement le dernier plan SimBrief et les données de vol réelles fournies par MSFS via SimConnect.
- Interface guidée : le ruban horizontal de route reste désormais dans le seul menu Plan de vol et ne se superpose plus au bandeau supérieur dans les autres modules ; l'interface classique conserve son affichage historique.
- Navigation entre les modules : le bandeau supérieur guidé mesure désormais la hauteur réelle de la barre d'outils et reste entièrement visible au lieu d'être rogné après un changement de menu.
- Module Procédures : une phase composée uniquement de rappels, comme l'atterrissage, ne s'affiche plus terminée avant le vol ; sa jauge reste vide et ses points portent la pastille d'information au lieu d'une confirmation verte.
- Module Procédures : une phase que le vol n'a pas encore atteinte n'affiche plus de confirmations ; au parking, le frein serré et les feux éteints ne valident plus les points de l'après-atterrissage ni de l'arrêt.
- Plan de roulage : l'entrée de départ est désormais choisie parmi toutes les jonctions de piste accessibles aux avions, selon leur proximité avec le seuil demandé. À CYYZ, un départ de la porte 139 vers la 23 emprunte maintenant AK, A, H et Q au lieu de traverser la 15L pour rejoindre l'intersection H3. Toute traversée de piste confirmée est découpée sur une attente explicite et la route est refusée si cette consigne disparaît.
- Trafic réseau injecté dans MSFS : les appareils que le simulateur laissait tomber en cours de vol sont désormais détectés et recréés au cycle suivant, au lieu de disparaître définitivement pendant que NaviXav croyait les suivre.
- Le journal note désormais chaque changement d'un cycle d'injection — appareils suivis, recréés, retirés, écartés — ce qui rend visible une injection devenue muette.
- Le libellé de l'option d'injection ne parle plus du seul VATSIM : il nomme le trafic réseau, quelle que soit la source choisie.
- La source réelle s'appelle désormais « Trafic réel · OpenSky » dans les trois listes de choix, au lieu du seul nom du fournisseur, et ce libellé suit enfin la langue de l'interface.
- Un appareil situé à l'endroit exact du vôtre n'est plus ni affiché ni injecté : c'est presque toujours votre propre avion, rendu par le réseau auquel vous êtes connecté. Le stationnement voisin reste visible, et le survol n'est pas confondu avec une superposition.
- Un appareil qui ne publie aucun indicatif en reçoit un, générique et stable, au lieu de son adresse hexadécimale ou d'un champ vide que le simulateur afficherait comme une immatriculation manquante.
- L'injection de trafic possède désormais son propre cycle de vie : son état est interrogeable au lieu d'être enfermé dans le service web, si bien qu'une injection arrêtée ne peut plus se faire passer pour une injection saine.

## Modifications

- Integration trafic.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
