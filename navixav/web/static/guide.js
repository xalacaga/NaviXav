"use strict";

/**
 * Guide d'utilisation, ouvert depuis l'en-tête des paramètres.
 *
 * Un texte d'aide se lit : il suit donc la langue de l'interface, dans les
 * huit langues, comme i18n.js. Chaque section et chaque entrée porte un
 * identifiant stable ; les tests vérifient que toutes les langues ont les
 * mêmes, et que chaque module et chaque groupe de réglages y est décrit.
 * Les identifiants aéronautiques (SID, STAR, METAR, MCDU…) restent tels quels.
 */
const GUIDE = (() => {
  const SECTIONS = ["start", "toolbar", "modules", "settings", "setup", "alerts", "troubleshooting"];

  const TEXT = {};

  TEXT.fr = {
    title: "Guide d’utilisation",
    intro: "Tout ce que fait chaque menu, et comment configurer NaviXav pas à pas.",
    contents: "Sommaire",
    sections: {
      start: {
        title: "Premiers pas",
        items: {
          install: ["Installation", "Installez NaviXav comme une application Windows ordinaire, jamais dans le dossier Community. Seul le panneau MSFS facultatif y va, et uniquement quand vous le demandez dans les paramètres."],
          plan: ["Source du plan", "Renseignez votre Pilot ID SimBrief (ou votre nom d’utilisateur) dans {settings} > {settings_section_general}. Vous pouvez aussi choisir le plan de vol chargé dans MSFS (.PLN)."],
          msfs: ["Simulateur", "Lancez MSFS 2024 et chargez un vol : NaviXav s’y connecte seul. Les données de navigation déjà récupérées restent consultables hors ligne."],
          first_import: ["Premier import", "Générez un OFP dans SimBrief, puis cliquez sur « {complete} ». NaviXav complète le départ et l’arrivée et explique chacun de ses choix."],
          interface: ["Interface guidée ou classique", "En mode guidé, un bandeau en haut résume le vol actif, la phase, le temps restant et la prochaine action, et met en avant le module utile. Le mode classique affiche tous les modules à égalité."],
        },
      },
      toolbar: {
        title: "Barre d’outils",
        items: {
          import: ["Importation du plan", "Recharge votre dernier OFP SimBrief, ou le plan MSFS, et recalcule départ et arrivée."],
          simbrief: ["Créer dans SimBrief / Ouvrir un .PLN", "Ouvre l’éditeur SimBrief dans votre navigateur, ou permet de choisir un autre fichier .PLN selon la source du plan."],
          sim_status: ["État MSFS", "Vert : connecté. Orange : simulateur en pause. Gris : MSFS hors ligne ou aucun vol chargé."],
          theme: ["Apparence", "Bascule entre thème clair et sombre."],
          settings: ["Paramètres", "Ouvre les réglages, ce guide et le journal des versions."],
          update: ["Rechercher MAJ", "Vérifie s’il existe une nouvelle version. L’installateur est contrôlé par sa somme SHA-256 avant toute mise à jour."],
          support: ["Soutenir", "Ouvre la page de soutien au développement. NaviXav reste gratuit."],
          quit: ["Quitter", "Arrête NaviXav, ferme les connexions et libère le port."],
        },
      },
      modules: {
        title: "Les modules",
        items: {
          terminal: ["Plan de vol", "Départ, route et arrivée : pistes, SID, STAR, approche, transitions, altitude et niveau de transition, fréquence ILS. Chaque choix automatique affiche sa raison et son niveau de confiance, et peut être modifié."],
          turnaround: ["Escale", "Avec GSX Pro, l’avion au poste vu de dessus : la cabine se remplit au fil de l’embarquement, les soutes et les réservoirs se chargent, les véhicules arrivent et repartent. La chronologie mesure le rythme de chaque service et estime l’heure de départ (TOBT) face à l’OFP ; le devis de masse et centrage signale toute correction de dernière minute. À l’arrivée, un guidage d’accostage estimé mène au point d’arrêt."],
          map: ["Carte", "Route complète par couleur de procédure, position et trace de l’avion, trafic, contraintes et zones SIGMET. Boutons Suivre, Route complète et Ajuster ; le fond de carte et chaque calque se masquent depuis la barre de la carte. Le calque « {map_turbulence} » montre le risque de turbulence en air clair prévu par l’OFP et la turbulence signalée par les pilotes près de la route."],
          ground: ["Roulage", "Plan d’aérodrome issu de MSFS. Cliquez sur un poste pour obtenir un itinéraire ; NaviXav annonce la prochaine manœuvre, les arrêts avant piste et surveille votre vitesse de roulage."],
          procedures: ["Procédures", "Checklists de votre appareil, phase par phase, cochées automatiquement quand le simulateur le permet. Les onglets séparent procédures normales, anormales et d’urgence."],
          flight: ["Suivi du vol", "Phase, prochain point, écarts, TOD, profil vertical, suivi carburant et approche stabilisée, configuration avion et alarmes. Le journal de vol local s’y trouve aussi."],
          constraints: ["Contraintes", "Toutes les contraintes d’altitude et de vitesse du SID, de la STAR et de l’approche, dans l’ordre du vol."],
          dispatch: ["Dispatch", "Masses, carburant, dégagement et temps de vol de l’OFP SimBrief."],
          aircraft: ["Avion", "Appareil reconnu, équipements déclarés et documents disponibles."],
          sia: ["Cartes officielles", "Cartes des autorités nationales, triées par type ; celles qui correspondent à votre vol sont présélectionnées. Seuls les PDF consultés sont téléchargés."],
          mcdu: ["Fiche MCDU", "Les données à saisir dans le MCDU, le CDU ou le FMS, page par page, avec la carte officielle à côté."],
          weather: ["Météo", "METAR et TAF du départ, de l’arrivée et du dégagement, vent et température en route, et SIGMET proches de la route avec leur texte complet."],
        },
      },
      settings: {
        title: "Les paramètres",
        intro: "Les réglages sont enregistrés sur cet ordinateur. Cliquez sur « {save} » pour les appliquer.",
        items: {
          general: ["Général & SimBrief", "Langue, apparence, organisation de l’interface, source du plan (SimBrief ou .PLN MSFS) et identifiants SimBrief."],
          flight: ["Vol & météo", "Source METAR (SimBrief ou en direct), approches préférées, limites de vent arrière et traversier, longueur de piste minimale et compatibilité RNP."],
          audio: ["Audio du cockpit", "Annonces vocales et choix de la voix, volume des annonces et alarmes, ambiance radio ATC, ATC et interphone hors ligne, et téléchargement de la voix naturelle."],
          display: ["Carte & roulage", "Fond de carte, couleur de la trace, vitesses maximales de roulage en ligne droite et en virage, alarme sonore de vitesse."],
          traffic: ["Trafic & modèles", "Source du trafic (VATSIM, IVAO, OpenSky ou statique), rayon, nombre d’avions, jeu de modèles (FSLTL ou AIG) et leurs chemins si la détection automatique échoue."],
          msfs_panel: ["Panneau MSFS", "Installe, met à jour ou retire l’icône NaviXav de la barre d’outils du simulateur."],
          connections: ["Connexions", "Accès depuis un téléphone ou une tablette sur le réseau local, et liaison facultative avec ChartFox."],
          aircraft_procedures: ["Procédures par appareil", "Compare les avions installés dans Community avec la base de procédures de NaviXav, et indique ceux qui sont couverts."],
          about: ["NaviXav & soutien", "Site du projet et soutien au développement."],
          changelog: ["Journal des versions", "L’icône à trois traits, en haut des paramètres, liste tous les changements depuis les premières versions."],
        },
      },
      setup: {
        title: "Configurer pas à pas",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general} : saisissez le Pilot ID (visible dans votre compte SimBrief) ou le nom d’utilisateur, enregistrez, puis cliquez sur « {complete} »."],
          metar: ["Météo en direct", "{settings} > {settings_section_flight} > METAR : « {live_metar} ». La météo se met à jour toutes les 5 minutes sans jamais changer vos pistes ni vos procédures."],
          voice: ["Annonces vocales", "{settings} > {settings_audio_title} : activez « {voice_settings_toggle} », choisissez une voix, puis « {voice_test} ». Les voix sont livrées avec NaviXav et fonctionnent hors ligne. L’interrupteur du module {tab_flight} les coupe à tout moment."],
          voice_volume: ["Volume des annonces et alarmes", "{settings} > {settings_audio_title} : le curseur « {voice_volume} » règle les annonces vocales et le bip de survitesse au roulage. En le relâchant, un exemple est joué au niveau choisi."],
          tower: ["Tour hors ligne", "{settings} > {settings_audio_title} : « {tower_toggle} ». Au départ, une tour fictive s’adresse à votre vol avec l’indicatif, la piste et les fréquences du vol chargé : alignement au point d’arrêt, autorisation de décollage avec le vent, transfert vers le départ. Elle parle français sur un aérodrome français quand l’interface est en français, et se tait quand le trafic VATSIM ou IVAO est choisi. « {tower_test} » en fait entendre un exemple. Une voix naturelle, synthétisée sur votre ordinateur, est proposée en option : « {tower_engine_download} » dans la même section, ou à l’installation. Avec la voix naturelle, le contrôle et l’équipe au sol accompagnent aussi la préparation : clairance, fin d’embarquement, devis de masse, repoussage, roulage, poste et cales à l’arrivée."],
          traffic: ["Trafic dans MSFS", "Installez FSLTL Base Models ou AIG AI Traffic, choisissez le jeu de modèles et la source dans {settings} > {settings_section_traffic}, puis allumez le trafic depuis la barre de la carte ou du roulage."],
          panel: ["Panneau MSFS", "{settings} > {settings_section_msfs_panel} > « {settings_msfs_panel_install} ». Une icône NaviXav apparaît dans la barre d’outils du simulateur au prochain chargement. Quand une nouvelle version est disponible, le même bouton la met à jour."],
          tablet: ["Téléphone ou tablette", "{settings} > {settings_section_connections} : activez l’accès, redémarrez NaviXav, autorisez le réseau privé si Windows le demande, puis ouvrez l’adresse affichée depuis un appareil du même Wi-Fi."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > « {chartfox_connect} ». La connexion passe par votre navigateur ; NaviXav ne voit jamais votre mot de passe."],
          chatter: ["Ambiance radio ATC", "{settings} > {settings_audio_title} : activez « {chatter_toggle} » et réglez son volume. Des échanges radio en anglais, enregistrés hors ligne, se jouent en fond selon la phase du vol ; ils ne concernent pas votre avion et se taisent pendant les annonces NaviXav."],
        },
      },
      alerts: {
        title: "Alarmes et annonces",
        items: {
          master: ["MASTER CAUTION et MASTER WARNING", "NaviXav compare la configuration de l’avion à la phase de vol : train, volets, feux, calage altimétrique, carburant, approche stabilisée, SIGMET devant… Une alarme ne concerne que les systèmes que l’avion possède et doit persister quelques secondes."],
          ack: ["Acquitter", "Cliquez sur une alarme pour l’acquitter. Elle se réarme d’elle-même au changement de phase ou si la situation se dégrade de nouveau."],
          toggle: ["Couper les alarmes", "L’interrupteur « {alerts_toggle} » du module {tab_flight} les désactive toutes. Elles sont suspendues automatiquement en simulation accélérée et pendant une relecture."],
          voice: ["Annonces vocales", "Alarmes, TOD, approche stabilisée et consignes de roulage sont annoncés si les annonces sont actives. Les termes aéronautiques restent en anglais, comme dans un vrai poste."],
          landing: ["Analyse d’atterrissage", "Après le toucher, NaviXav affiche le taux de chute, la stabilité de l’approche et une note. Elle se rouvre depuis le journal de vol."],
        },
      },
      troubleshooting: {
        title: "En cas de problème",
        items: {
          msfs_offline: ["« MSFS hors ligne »", "Vérifiez que MSFS 2024 est lancé avec un vol chargé, pas seulement le menu principal. NaviXav retente la connexion tout seul."],
          no_plan: ["Aucun plan importé", "Vérifiez le Pilot ID SimBrief et qu’un OFP a bien été généré. Avec la source MSFS, chargez d’abord un vol dans le simulateur."],
          no_traffic: ["Pas de trafic dans MSFS", "Il faut un jeu de modèles détecté (FSLTL ou AIG) et le trafic allumé. Le message d’état sous la carte indique ce qui manque."],
          disconnects: ["Déconnexions", "Chaque perte et chaque rétablissement de la liaison SimConnect sont consignés avec leur cause et leur durée dans le journal de diagnostic."],
          logs: ["Journal de diagnostic", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Joignez-le à un signalement avec la version de NaviXav, de Windows, de MSFS et l’avion utilisé. Il ne contient ni votre identifiant SimBrief ni votre route complète."],
        },
      },
    },
  };

  TEXT.en = {
    title: "User guide",
    intro: "What each menu does, and how to set NaviXav up step by step.",
    contents: "Contents",
    sections: {
      start: {
        title: "Getting started",
        items: {
          install: ["Installation", "Install NaviXav like any Windows application, never in the Community folder. Only the optional MSFS panel goes there, and only when you ask for it in Settings."],
          plan: ["Flight plan source", "Enter your SimBrief Pilot ID (or username) in {settings} > {settings_section_general}. You can also use the flight plan loaded in MSFS (.PLN)."],
          msfs: ["Simulator", "Start MSFS 2024 and load a flight: NaviXav connects on its own. Navigation data already retrieved remains available offline."],
          first_import: ["First import", "Generate an OFP in SimBrief, then click “{complete}”. NaviXav completes the departure and the arrival and explains each of its choices."],
          interface: ["Guided or classic layout", "In guided mode, a bar at the top sums up the active flight, the phase, the time remaining and the next action, and brings the useful module forward. The classic layout shows every module on an equal footing."],
        },
      },
      toolbar: {
        title: "Toolbar",
        items: {
          import: ["Import plan", "Reloads your latest SimBrief OFP, or the MSFS plan, and recalculates departure and arrival."],
          simbrief: ["Create in SimBrief / Open a .PLN", "Opens the SimBrief editor in your browser, or lets you pick another .PLN file, depending on the plan source."],
          sim_status: ["MSFS status", "Green: connected. Orange: simulator paused. Grey: MSFS offline or no flight loaded."],
          theme: ["Appearance", "Switches between the light and dark themes."],
          settings: ["Settings", "Opens the settings, this guide and the version history."],
          update: ["Check for updates", "Looks for a newer version. The installer is verified against its SHA-256 checksum before any update."],
          support: ["Support", "Opens the page to support development. NaviXav stays free."],
          quit: ["Quit", "Stops NaviXav, closes its connections and frees the port."],
        },
      },
      modules: {
        title: "Modules",
        items: {
          terminal: ["Flight plan", "Departure, route and arrival: runways, SID, STAR, approach, transitions, transition altitude and level, ILS frequency. Every automatic choice shows its reason and confidence, and can be changed."],
          turnaround: ["Turnaround", "With GSX Pro, the aircraft at its stand seen from above: the cabin fills as passengers board, holds and tanks load, and vehicles come and go. The timeline measures each service’s rate and estimates the departure time (TOBT) against the OFP; the load and trim sheet flags any last-minute change. On arrival, estimated docking guidance leads you to the stop point."],
          map: ["Map", "Complete route coloured by procedure, aircraft position and track, traffic, constraints and SIGMET areas. Follow, Full route and Fit buttons; the background and each layer can be hidden from the map toolbar. The “{map_turbulence}” layer shows the clear-air turbulence risk forecast by the OFP and turbulence reported by pilots near the route."],
          ground: ["Taxi", "Airport diagram built from MSFS. Click a stand to get a route; NaviXav announces the next manoeuvre and hold-short points and watches your taxi speed."],
          procedures: ["Procedures", "Your aircraft’s checklists, phase by phase, ticked automatically where the simulator allows it. Tabs separate normal, abnormal and emergency procedures."],
          flight: ["Flight tracking", "Phase, next waypoint, deviations, TOD, vertical profile, fuel monitoring and stabilized approach, aircraft configuration and alerts. The local logbook is here too."],
          constraints: ["Constraints", "Every altitude and speed constraint of the SID, STAR and approach, in flight order."],
          dispatch: ["Dispatch", "Weights, fuel, alternate and flight time from the SimBrief OFP."],
          aircraft: ["Aircraft", "Recognised aircraft, declared equipment and available documents."],
          sia: ["Official charts", "Charts from the national authorities, sorted by type; those matching your flight are pre-selected. Only the PDFs you open are downloaded."],
          mcdu: ["MCDU card", "The data to enter in the MCDU, CDU or FMS, page by page, with the official chart alongside."],
          weather: ["Weather", "Departure, arrival and alternate METAR and TAF, en-route wind and temperature, and SIGMETs near the route with their full text."],
        },
      },
      settings: {
        title: "Settings",
        intro: "Settings are stored on this computer. Click “{save}” to apply them.",
        items: {
          general: ["General & SimBrief", "Language, appearance, interface layout, plan source (SimBrief or MSFS .PLN) and SimBrief identifiers."],
          flight: ["Flight & weather", "METAR source (SimBrief or live), preferred approaches, tailwind and crosswind limits, minimum runway length and RNP capability."],
          audio: ["Cockpit audio", "Voice callouts and voice choice, callout and alarm volume, ATC radio ambience, offline ATC and interphone, and the natural voice download."],
          display: ["Map & taxi", "Map background, track colour, maximum taxi speeds straight and in turns, taxi speed audio alarm."],
          traffic: ["Traffic & models", "Traffic source (VATSIM, IVAO, OpenSky or static), radius, aircraft count, model set (FSLTL or AIG) and their paths if automatic detection fails."],
          msfs_panel: ["MSFS panel", "Installs, updates or removes the NaviXav icon in the simulator toolbar."],
          connections: ["Connections", "Access from a phone or tablet on the local network, and the optional ChartFox link."],
          aircraft_procedures: ["Procedures per aircraft", "Compares the aircraft installed in Community with NaviXav’s procedure database and shows which ones are covered."],
          about: ["NaviXav & support", "Project website and support for development."],
          changelog: ["Version history", "The three-line icon at the top of the settings lists every change since the first versions."],
        },
      },
      setup: {
        title: "Step-by-step setup",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general}: enter your Pilot ID (shown in your SimBrief account) or username, save, then click “{complete}”."],
          metar: ["Live weather", "{settings} > {settings_section_flight} > METAR: “{live_metar}”. Weather refreshes every 5 minutes and never changes your runways or procedures."],
          voice: ["Voice callouts", "{settings} > {settings_audio_title}: turn on “{voice_settings_toggle}”, pick a voice, then “{voice_test}”. The voices ship with NaviXav and work offline. The switch in {tab_flight} silences them at any time."],
          voice_volume: ["Callout and alarm volume", "{settings} > {settings_audio_title}: the “{voice_volume}” slider sets the voice callouts and the taxi overspeed beep. Releasing it plays a sample at the chosen level."],
          tower: ["Offline tower", "{settings} > {settings_audio_title}: “{tower_toggle}”. On departure, a simulated tower talks to your flight with the callsign, runway and frequencies of the loaded flight: line up at the holding point, takeoff clearance with the wind, handoff to departure. It falls silent when VATSIM or IVAO traffic is selected. “{tower_test}” plays a sample. A natural voice, synthesized on your computer, is available as an option: “{tower_engine_download}” in the same section, or at installation. With the natural voice, ATC and the ground crew also accompany the preparation: clearance, boarding completed, loadsheet, pushback, taxi, stand and chocks on arrival."],
          traffic: ["Traffic in MSFS", "Install FSLTL Base Models or AIG AI Traffic, choose the model set and the source in {settings} > {settings_section_traffic}, then turn traffic on from the Map or Taxi toolbar."],
          panel: ["MSFS panel", "{settings} > {settings_section_msfs_panel} > “{settings_msfs_panel_install}”. A NaviXav icon appears in the simulator toolbar at the next load. When a new version is available, the same button updates it."],
          tablet: ["Phone or tablet", "{settings} > {settings_section_connections}: turn access on, restart NaviXav, allow private networks if Windows asks, then open the address shown from a device on the same Wi-Fi."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > “{chartfox_connect}”. Sign-in goes through your browser; NaviXav never sees your password."],
          chatter: ["ATC radio ambience", "{settings} > {settings_audio_title}: turn on “{chatter_toggle}” and set its volume. Pre-recorded English radio exchanges play in the background according to the flight phase; they do not concern your aircraft and pause during NaviXav callouts."],
        },
      },
      alerts: {
        title: "Alerts and callouts",
        items: {
          master: ["MASTER CAUTION and MASTER WARNING", "NaviXav checks the aircraft configuration against the flight phase: gear, flaps, lights, altimeter setting, fuel, stabilized approach, SIGMET ahead… An alert only concerns systems the aircraft actually has and must persist a few seconds."],
          ack: ["Acknowledge", "Click an alert to acknowledge it. It re-arms on its own at the next phase change or if the situation degrades again."],
          toggle: ["Switch alerts off", "The “{alerts_toggle}” switch in {tab_flight} disables them all. They are suspended automatically at accelerated simulation rate and during a replay."],
          voice: ["Voice callouts", "Alerts, TOD, stabilized approach and taxi instructions are spoken when callouts are on. Aviation terms stay in English, as in a real cockpit."],
          landing: ["Landing analysis", "After touchdown, NaviXav shows the sink rate, approach stability and a score. It can be reopened from the logbook."],
        },
      },
      troubleshooting: {
        title: "Troubleshooting",
        items: {
          msfs_offline: ["“MSFS offline”", "Check that MSFS 2024 is running with a flight loaded, not just the main menu. NaviXav retries the connection on its own."],
          no_plan: ["No plan imported", "Check your SimBrief Pilot ID and that an OFP has been generated. With the MSFS source, load a flight in the simulator first."],
          no_traffic: ["No traffic in MSFS", "A detected model set (FSLTL or AIG) and traffic switched on are both required. The status line under the map says what is missing."],
          disconnects: ["Disconnections", "Every loss and recovery of the SimConnect link is recorded with its cause and duration in the diagnostic log."],
          logs: ["Diagnostic log", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Attach it to a report with your NaviXav, Windows and MSFS versions and the aircraft used. It contains neither your SimBrief identifier nor your complete route."],
        },
      },
    },
  };

  TEXT.de = {
    title: "Benutzerhandbuch",
    intro: "Was jedes Menü tut und wie Sie NaviXav Schritt für Schritt einrichten.",
    contents: "Inhalt",
    sections: {
      start: {
        title: "Erste Schritte",
        items: {
          install: ["Installation", "Installieren Sie NaviXav wie jede Windows-Anwendung, niemals im Community-Ordner. Nur das optionale MSFS-Panel kommt dorthin, und nur wenn Sie es in den Einstellungen anfordern."],
          plan: ["Flugplanquelle", "Tragen Sie Ihre SimBrief Pilot ID (oder Ihren Benutzernamen) unter {settings} > {settings_section_general} ein. Sie können auch den in MSFS geladenen Flugplan (.PLN) verwenden."],
          msfs: ["Simulator", "Starten Sie MSFS 2024 und laden Sie einen Flug: NaviXav verbindet sich selbst. Bereits abgerufene Navigationsdaten bleiben offline verfügbar."],
          first_import: ["Erster Import", "Erzeugen Sie in SimBrief einen OFP und klicken Sie dann auf „{complete}“. NaviXav ergänzt Abflug und Ankunft und begründet jede seiner Entscheidungen."],
          interface: ["Geführte oder klassische Oberfläche", "Im geführten Modus fasst eine Leiste oben den aktiven Flug, die Phase, die Restzeit und die nächste Aktion zusammen und stellt das passende Modul in den Vordergrund. Die klassische Oberfläche zeigt alle Module gleichrangig."],
        },
      },
      toolbar: {
        title: "Symbolleiste",
        items: {
          import: ["Flugplan importieren", "Lädt Ihren letzten SimBrief-OFP oder den MSFS-Plan neu und berechnet Abflug und Ankunft erneut."],
          simbrief: ["In SimBrief erstellen / .PLN öffnen", "Öffnet je nach Planquelle den SimBrief-Editor im Browser oder lässt Sie eine andere .PLN-Datei wählen."],
          sim_status: ["MSFS-Status", "Grün: verbunden. Orange: Simulator pausiert. Grau: MSFS offline oder kein Flug geladen."],
          theme: ["Darstellung", "Wechselt zwischen hellem und dunklem Design."],
          settings: ["Einstellungen", "Öffnet die Einstellungen, dieses Handbuch und den Versionsverlauf."],
          update: ["Nach Updates suchen", "Prüft, ob es eine neuere Version gibt. Das Installationsprogramm wird vor jedem Update anhand seiner SHA-256-Prüfsumme verifiziert."],
          support: ["Unterstützen", "Öffnet die Seite zur Unterstützung der Entwicklung. NaviXav bleibt kostenlos."],
          quit: ["Beenden", "Beendet NaviXav, schließt seine Verbindungen und gibt den Port frei."],
        },
      },
      modules: {
        title: "Die Module",
        items: {
          terminal: ["Flugplan", "Abflug, Route und Ankunft: Pisten, SID, STAR, Anflug, Transitions, Übergangshöhe und -fläche, ILS-Frequenz. Jede automatische Wahl zeigt ihren Grund und ihre Sicherheit und kann geändert werden."],
          turnaround: ["Abfertigung", "Mit GSX Pro das Flugzeug an der Parkposition von oben: Die Kabine füllt sich beim Boarding, Frachträume und Tanks werden beladen, Fahrzeuge kommen und fahren. Der Ablauf misst das Tempo jedes Dienstes und schätzt die Abflugzeit (TOBT) gegenüber dem OFP; das Ladeblatt meldet jede Last-Minute-Änderung. Bei der Ankunft führt eine geschätzte Andockführung zum Haltepunkt."],
          map: ["Karte", "Vollständige Route nach Verfahren eingefärbt, Position und Spur des Flugzeugs, Verkehr, Beschränkungen und SIGMET-Gebiete. Schaltflächen Folgen, Ganze Route und Einpassen; Hintergrund und jede Ebene lassen sich in der Kartenleiste ausblenden. Die Ebene „{map_turbulence}“ zeigt das vom OFP vorhergesagte Risiko klarer Luftturbulenz und von Piloten gemeldete Turbulenzen nahe der Route."],
          ground: ["Rollen", "Flughafenplan aus MSFS-Daten. Klicken Sie auf eine Parkposition, um eine Rollroute zu erhalten; NaviXav kündigt das nächste Manöver und die Haltepunkte an und überwacht Ihre Rollgeschwindigkeit."],
          procedures: ["Verfahren", "Die Checklisten Ihres Flugzeugs, Phase für Phase, automatisch abgehakt, wo der Simulator es erlaubt. Reiter trennen normale, abnormale und Notverfahren."],
          flight: ["Flugverfolgung", "Phase, nächster Wegpunkt, Abweichungen, TOD, Vertikalprofil, Kraftstoffüberwachung und stabilisierter Anflug, Flugzeugkonfiguration und Alarme. Auch das lokale Flugbuch ist hier."],
          constraints: ["Beschränkungen", "Alle Höhen- und Geschwindigkeitsbeschränkungen von SID, STAR und Anflug in Flugreihenfolge."],
          dispatch: ["Dispatch", "Massen, Kraftstoff, Ausweichflughafen und Flugzeit aus dem SimBrief-OFP."],
          aircraft: ["Flugzeug", "Erkanntes Flugzeug, angegebene Ausrüstung und verfügbare Dokumente."],
          sia: ["Offizielle Karten", "Karten der nationalen Behörden, nach Typ sortiert; die zu Ihrem Flug passenden sind vorausgewählt. Nur die geöffneten PDFs werden heruntergeladen."],
          mcdu: ["MCDU-Daten", "Die Eingaben für MCDU, CDU oder FMS, Seite für Seite, mit der offiziellen Karte daneben."],
          weather: ["Wetter", "METAR und TAF von Abflug, Ankunft und Ausweichflughafen, Wind und Temperatur auf der Strecke sowie SIGMETs nahe der Route mit ihrem vollständigen Text."],
        },
      },
      settings: {
        title: "Die Einstellungen",
        intro: "Die Einstellungen werden auf diesem Computer gespeichert. Klicken Sie auf „{save}“, um sie anzuwenden.",
        items: {
          general: ["Allgemein & SimBrief", "Sprache, Darstellung, Aufbau der Oberfläche, Planquelle (SimBrief oder MSFS-.PLN) und SimBrief-Kennungen."],
          flight: ["Flug & Wetter", "METAR-Quelle (SimBrief oder live), bevorzugte Anflüge, Rücken- und Seitenwindgrenzen, minimale Pistenlänge und RNP-Fähigkeit."],
          audio: ["Cockpit-Audio", "Sprachansagen und Stimmwahl, Lautstärke der Ansagen und Alarme, ATC-Funkatmosphäre, Offline-ATC und Interphone sowie der Download der natürlichen Stimme."],
          display: ["Karte & Rollen", "Kartenhintergrund, Farbe der Spur, maximale Rollgeschwindigkeit geradeaus und in Kurven, akustischer Geschwindigkeitsalarm."],
          traffic: ["Verkehr & Modelle", "Verkehrsquelle (VATSIM, IVAO, OpenSky oder statisch), Radius, Anzahl der Flugzeuge, Modellsatz (FSLTL oder AIG) und deren Pfade, falls die automatische Erkennung scheitert."],
          msfs_panel: ["MSFS-Panel", "Installiert, aktualisiert oder entfernt das NaviXav-Symbol in der Symbolleiste des Simulators."],
          connections: ["Verbindungen", "Zugriff von Telefon oder Tablet im lokalen Netz und optionale Verbindung mit ChartFox."],
          aircraft_procedures: ["Verfahren nach Flugzeug", "Vergleicht die in Community installierten Flugzeuge mit der Verfahrensdatenbank von NaviXav und zeigt, welche abgedeckt sind."],
          about: ["NaviXav & Unterstützung", "Projektwebsite und Unterstützung der Entwicklung."],
          changelog: ["Versionsverlauf", "Das Symbol mit drei Strichen oben in den Einstellungen listet alle Änderungen seit den ersten Versionen."],
        },
      },
      setup: {
        title: "Schritt-für-Schritt-Einrichtung",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general}: Pilot ID (in Ihrem SimBrief-Konto sichtbar) oder Benutzernamen eingeben, speichern und dann auf „{complete}“ klicken."],
          metar: ["Live-Wetter", "{settings} > {settings_section_flight} > METAR: „{live_metar}“. Das Wetter wird alle 5 Minuten aktualisiert und ändert nie Ihre Pisten oder Verfahren."],
          voice: ["Sprachansagen", "{settings} > {settings_audio_title}: „{voice_settings_toggle}“ einschalten, eine Stimme wählen und „{voice_test}“. Die Stimmen werden mit NaviXav geliefert und funktionieren offline. Der Schalter in {tab_flight} schaltet sie jederzeit stumm."],
          voice_volume: ["Lautstärke der Ansagen und Alarme", "{settings} > {settings_audio_title}: Der Regler „{voice_volume}“ stellt die Sprachansagen und das Piepsignal bei zu schnellem Rollen ein. Beim Loslassen ertönt ein Beispiel in der gewählten Lautstärke."],
          tower: ["Offline-Turm", "{settings} > {settings_audio_title}: „{tower_toggle}“. Beim Abflug spricht ein simulierter Turm Ihren Flug mit Rufzeichen, Piste und Frequenzen des geladenen Flugs an: Aufrollen am Rollhalt, Startfreigabe mit dem Wind, Übergabe an Departure. Er schweigt, wenn VATSIM- oder IVAO-Verkehr gewählt ist. „{tower_test}“ spielt ein Beispiel ab. Eine natürliche, auf Ihrem Computer erzeugte Stimme ist optional verfügbar: „{tower_engine_download}“ im selben Abschnitt oder bei der Installation. Mit der natürlichen Stimme begleiten Lotsen und Bodenpersonal auch die Vorbereitung: Freigabe, Boarding-Ende, Ladeblatt, Pushback, Rollen, Parkposition und Bremsklötze bei der Ankunft."],
          traffic: ["Verkehr in MSFS", "Installieren Sie FSLTL Base Models oder AIG AI Traffic, wählen Sie Modellsatz und Quelle unter {settings} > {settings_section_traffic} und schalten Sie den Verkehr in der Karten- oder Rollleiste ein."],
          panel: ["MSFS-Panel", "{settings} > {settings_section_msfs_panel} > „{settings_msfs_panel_install}“. Beim nächsten Laden erscheint ein NaviXav-Symbol in der Symbolleiste des Simulators. Gibt es eine neue Version, aktualisiert sie dieselbe Schaltfläche."],
          tablet: ["Telefon oder Tablet", "{settings} > {settings_section_connections}: Zugriff einschalten, NaviXav neu starten, private Netzwerke zulassen, wenn Windows fragt, und die angezeigte Adresse auf einem Gerät im selben WLAN öffnen."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > „{chartfox_connect}“. Die Anmeldung läuft über Ihren Browser; NaviXav sieht Ihr Passwort nie."],
          chatter: ["ATC-Funkatmosphäre", "{settings} > {settings_audio_title}: „{chatter_toggle}“ einschalten und die Lautstärke einstellen. Vorab aufgenommener englischer Funkverkehr läuft je nach Flugphase im Hintergrund; er betrifft nicht Ihr Flugzeug und verstummt während der NaviXav-Ansagen."],
        },
      },
      alerts: {
        title: "Alarme und Ansagen",
        items: {
          master: ["MASTER CAUTION und MASTER WARNING", "NaviXav vergleicht die Flugzeugkonfiguration mit der Flugphase: Fahrwerk, Klappen, Lichter, Höhenmessereinstellung, Kraftstoff, stabilisierter Anflug, SIGMET voraus… Ein Alarm betrifft nur Systeme, die das Flugzeug wirklich hat, und muss einige Sekunden anhalten."],
          ack: ["Quittieren", "Klicken Sie auf einen Alarm, um ihn zu quittieren. Er wird beim nächsten Phasenwechsel oder bei erneuter Verschlechterung von selbst wieder scharf."],
          toggle: ["Alarme abschalten", "Der Schalter „{alerts_toggle}“ in {tab_flight} deaktiviert alle Alarme. Bei beschleunigter Simulation und während einer Wiedergabe sind sie automatisch ausgesetzt."],
          voice: ["Sprachansagen", "Alarme, TOD, stabilisierter Anflug und Rollanweisungen werden angesagt, wenn die Ansagen aktiv sind. Luftfahrtbegriffe bleiben englisch, wie in einem echten Cockpit."],
          landing: ["Landeanalyse", "Nach dem Aufsetzen zeigt NaviXav Sinkrate, Stabilität des Anflugs und eine Bewertung. Sie lässt sich aus dem Flugbuch erneut öffnen."],
        },
      },
      troubleshooting: {
        title: "Fehlerbehebung",
        items: {
          msfs_offline: ["„MSFS offline“", "Prüfen Sie, ob MSFS 2024 mit geladenem Flug läuft und nicht nur im Hauptmenü. NaviXav versucht die Verbindung selbst erneut."],
          no_plan: ["Kein Plan importiert", "Prüfen Sie die SimBrief Pilot ID und ob ein OFP erzeugt wurde. Mit der MSFS-Quelle laden Sie zuerst einen Flug im Simulator."],
          no_traffic: ["Kein Verkehr in MSFS", "Nötig sind ein erkannter Modellsatz (FSLTL oder AIG) und eingeschalteter Verkehr. Die Statuszeile unter der Karte zeigt, was fehlt."],
          disconnects: ["Verbindungsabbrüche", "Jeder Verlust und jede Wiederherstellung der SimConnect-Verbindung wird mit Ursache und Dauer im Diagnoseprotokoll festgehalten."],
          logs: ["Diagnoseprotokoll", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Hängen Sie es einer Meldung an, zusammen mit den Versionen von NaviXav, Windows und MSFS und dem verwendeten Flugzeug. Es enthält weder Ihre SimBrief-Kennung noch Ihre vollständige Route."],
        },
      },
    },
  };

  TEXT.es = {
    title: "Guía de uso",
    intro: "Qué hace cada menú y cómo configurar NaviXav paso a paso.",
    contents: "Índice",
    sections: {
      start: {
        title: "Primeros pasos",
        items: {
          install: ["Instalación", "Instala NaviXav como cualquier aplicación de Windows, nunca en la carpeta Community. Solo el panel opcional de MSFS va allí, y solo cuando lo pides en los ajustes."],
          plan: ["Origen del plan", "Introduce tu Pilot ID de SimBrief (o tu nombre de usuario) en {settings} > {settings_section_general}. También puedes usar el plan de vuelo cargado en MSFS (.PLN)."],
          msfs: ["Simulador", "Inicia MSFS 2024 y carga un vuelo: NaviXav se conecta solo. Los datos de navegación ya obtenidos siguen disponibles sin conexión."],
          first_import: ["Primera importación", "Genera un OFP en SimBrief y pulsa «{complete}». NaviXav completa la salida y la llegada y explica cada una de sus elecciones."],
          interface: ["Interfaz guiada o clásica", "En modo guiado, una barra superior resume el vuelo activo, la fase, el tiempo restante y la próxima acción, y destaca el módulo útil. El modo clásico muestra todos los módulos por igual."],
        },
      },
      toolbar: {
        title: "Barra de herramientas",
        items: {
          import: ["Importar plan de vuelo", "Vuelve a cargar tu último OFP de SimBrief, o el plan de MSFS, y recalcula salida y llegada."],
          simbrief: ["Crear en SimBrief / Abrir un .PLN", "Según el origen del plan, abre el editor de SimBrief en el navegador o permite elegir otro archivo .PLN."],
          sim_status: ["Estado de MSFS", "Verde: conectado. Naranja: simulador en pausa. Gris: MSFS desconectado o sin vuelo cargado."],
          theme: ["Apariencia", "Alterna entre el tema claro y el oscuro."],
          settings: ["Ajustes", "Abre los ajustes, esta guía y el historial de versiones."],
          update: ["Buscar actualizaciones", "Comprueba si hay una versión nueva. El instalador se verifica con su suma SHA-256 antes de cualquier actualización."],
          support: ["Apoyar", "Abre la página de apoyo al desarrollo. NaviXav sigue siendo gratuito."],
          quit: ["Salir", "Detiene NaviXav, cierra sus conexiones y libera el puerto."],
        },
      },
      modules: {
        title: "Los módulos",
        items: {
          terminal: ["Plan de vuelo", "Salida, ruta y llegada: pistas, SID, STAR, aproximación, transiciones, altitud y nivel de transición, frecuencia ILS. Cada elección automática muestra su motivo y su fiabilidad, y puede cambiarse."],
          turnaround: ["Escala", "Con GSX Pro, el avión en su puesto visto desde arriba: la cabina se llena durante el embarque, bodegas y depósitos se cargan y los vehículos llegan y se van. La cronología mide el ritmo de cada servicio y estima la hora de salida (TOBT) frente al OFP; la hoja de carga y centrado señala cualquier cambio de última hora. A la llegada, un guiado de atraque estimado le lleva al punto de parada."],
          map: ["Mapa", "Ruta completa coloreada por procedimiento, posición y traza del avión, tráfico, restricciones y zonas SIGMET. Botones Seguir, Ruta completa y Ajustar; el fondo y cada capa se ocultan desde la barra del mapa. La capa «{map_turbulence}» muestra el riesgo de turbulencia en aire claro previsto por el OFP y la turbulencia notificada por los pilotos cerca de la ruta."],
          ground: ["Rodaje", "Plano del aeródromo construido con datos de MSFS. Pulsa en un puesto para obtener un itinerario; NaviXav anuncia la próxima maniobra y los puntos de espera y vigila tu velocidad de rodaje."],
          procedures: ["Procedimientos", "Las listas de comprobación de tu avión, fase por fase, marcadas automáticamente cuando el simulador lo permite. Las pestañas separan procedimientos normales, anormales y de emergencia."],
          flight: ["Seguimiento", "Fase, próximo punto, desviaciones, TOD, perfil vertical, seguimiento del combustible y aproximación estabilizada, configuración del avión y alarmas. Aquí está también el diario de vuelo local."],
          constraints: ["Restricciones", "Todas las restricciones de altitud y velocidad del SID, la STAR y la aproximación, en el orden del vuelo."],
          dispatch: ["Despacho", "Masas, combustible, alternativo y tiempo de vuelo del OFP de SimBrief."],
          aircraft: ["Avión", "Avión reconocido, equipos declarados y documentos disponibles."],
          sia: ["Cartas oficiales", "Cartas de las autoridades nacionales, ordenadas por tipo; las que corresponden a tu vuelo están preseleccionadas. Solo se descargan los PDF que abres."],
          mcdu: ["Ficha MCDU", "Los datos que hay que introducir en el MCDU, el CDU o el FMS, página por página, con la carta oficial al lado."],
          weather: ["Meteorología", "METAR y TAF de salida, llegada y alternativo, viento y temperatura en ruta, y SIGMET cercanos a la ruta con su texto completo."],
        },
      },
      settings: {
        title: "Los ajustes",
        intro: "Los ajustes se guardan en este ordenador. Pulsa «{save}» para aplicarlos.",
        items: {
          general: ["General y SimBrief", "Idioma, apariencia, organización de la interfaz, origen del plan (SimBrief o .PLN de MSFS) e identificadores de SimBrief."],
          flight: ["Vuelo y meteorología", "Fuente METAR (SimBrief o en directo), aproximaciones preferidas, límites de viento de cola y cruzado, longitud mínima de pista y capacidad RNP."],
          audio: ["Audio de cabina", "Avisos de voz y elección de la voz, volumen de avisos y alarmas, ambiente de radio ATC, ATC e interfono sin conexión, y descarga de la voz natural."],
          display: ["Mapa y rodaje", "Fondo del mapa, color de la traza, velocidades máximas de rodaje en recta y en viraje, alarma sonora de velocidad."],
          traffic: ["Tráfico y modelos", "Origen del tráfico (VATSIM, IVAO, OpenSky o estático), radio, número de aviones, juego de modelos (FSLTL o AIG) y sus rutas si falla la detección automática."],
          msfs_panel: ["Panel de MSFS", "Instala, actualiza o retira el icono de NaviXav de la barra de herramientas del simulador."],
          connections: ["Conexiones", "Acceso desde un teléfono o una tableta en la red local, y enlace opcional con ChartFox."],
          aircraft_procedures: ["Procedimientos por avión", "Compara los aviones instalados en Community con la base de procedimientos de NaviXav e indica cuáles están cubiertos."],
          about: ["NaviXav y apoyo", "Sitio del proyecto y apoyo al desarrollo."],
          changelog: ["Historial de versiones", "El icono de tres líneas, arriba en los ajustes, enumera todos los cambios desde las primeras versiones."],
        },
      },
      setup: {
        title: "Configuración paso a paso",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general}: introduce el Pilot ID (visible en tu cuenta de SimBrief) o el nombre de usuario, guarda y pulsa «{complete}»."],
          metar: ["Meteorología en directo", "{settings} > {settings_section_flight} > METAR: «{live_metar}». La meteorología se actualiza cada 5 minutos sin cambiar nunca tus pistas ni tus procedimientos."],
          voice: ["Avisos de voz", "{settings} > {settings_audio_title}: activa «{voice_settings_toggle}», elige una voz y pulsa «{voice_test}». Las voces vienen con NaviXav y funcionan sin conexión. El interruptor de {tab_flight} las silencia en cualquier momento."],
          voice_volume: ["Volumen de avisos y alarmas", "{settings} > {settings_audio_title}: el control «{voice_volume}» regula los avisos de voz y el pitido de exceso de velocidad en rodaje. Al soltarlo se reproduce un ejemplo al nivel elegido."],
          tower: ["Torre sin conexión", "{settings} > {settings_audio_title}: «{tower_toggle}». En la salida, una torre simulada se dirige a su vuelo con el indicativo, la pista y las frecuencias del vuelo cargado: alineación en el punto de espera, autorización de despegue con el viento y transferencia a salidas. Se calla cuando se elige el tráfico de VATSIM o IVAO. «{tower_test}» reproduce un ejemplo. Hay una voz natural, sintetizada en su ordenador, disponible como opción: «{tower_engine_download}» en la misma sección, o en la instalación. Con la voz natural, el control y el personal de tierra también acompañan la preparación: autorización, fin del embarque, hoja de carga, pushback, rodaje, puesto y calzos a la llegada."],
          traffic: ["Tráfico en MSFS", "Instala FSLTL Base Models o AIG AI Traffic, elige el juego de modelos y el origen en {settings} > {settings_section_traffic} y enciende el tráfico desde la barra del mapa o del rodaje."],
          panel: ["Panel de MSFS", "{settings} > {settings_section_msfs_panel} > «{settings_msfs_panel_install}». Un icono de NaviXav aparece en la barra del simulador en la siguiente carga. Cuando hay una versión nueva, el mismo botón la actualiza."],
          tablet: ["Teléfono o tableta", "{settings} > {settings_section_connections}: activa el acceso, reinicia NaviXav, permite las redes privadas si Windows lo pide y abre la dirección mostrada desde un dispositivo de la misma Wi-Fi."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > «{chartfox_connect}». El inicio de sesión pasa por tu navegador; NaviXav nunca ve tu contraseña."],
          chatter: ["Ambiente de radio ATC", "{settings} > {settings_audio_title}: activa «{chatter_toggle}» y ajusta su volumen. Comunicaciones de radio en inglés grabadas de antemano suenan de fondo según la fase del vuelo; no conciernen a tu avión y se callan durante los avisos de NaviXav."],
        },
      },
      alerts: {
        title: "Alarmas y avisos",
        items: {
          master: ["MASTER CAUTION y MASTER WARNING", "NaviXav compara la configuración del avión con la fase de vuelo: tren, flaps, luces, reglaje altimétrico, combustible, aproximación estabilizada, SIGMET por delante… Una alarma solo afecta a los sistemas que el avión tiene y debe persistir unos segundos."],
          ack: ["Reconocer", "Pulsa una alarma para reconocerla. Se rearma sola en el siguiente cambio de fase o si la situación vuelve a empeorar."],
          toggle: ["Desactivar las alarmas", "El interruptor «{alerts_toggle}» de {tab_flight} las desactiva todas. Se suspenden automáticamente con simulación acelerada y durante una repetición."],
          voice: ["Avisos de voz", "Alarmas, TOD, aproximación estabilizada e instrucciones de rodaje se anuncian si los avisos están activos. Los términos aeronáuticos siguen en inglés, como en una cabina real."],
          landing: ["Análisis del aterrizaje", "Tras la toma, NaviXav muestra la velocidad vertical, la estabilidad de la aproximación y una nota. Puede volver a abrirse desde el diario de vuelo."],
        },
      },
      troubleshooting: {
        title: "Solución de problemas",
        items: {
          msfs_offline: ["«MSFS desconectado»", "Comprueba que MSFS 2024 está en marcha con un vuelo cargado, no solo en el menú principal. NaviXav reintenta la conexión solo."],
          no_plan: ["Ningún plan importado", "Comprueba el Pilot ID de SimBrief y que se ha generado un OFP. Con el origen MSFS, carga primero un vuelo en el simulador."],
          no_traffic: ["Sin tráfico en MSFS", "Hacen falta un juego de modelos detectado (FSLTL o AIG) y el tráfico encendido. La línea de estado bajo el mapa indica qué falta."],
          disconnects: ["Desconexiones", "Cada pérdida y cada restablecimiento del enlace SimConnect quedan registrados con su causa y su duración en el registro de diagnóstico."],
          logs: ["Registro de diagnóstico", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Adjúntalo a un informe con las versiones de NaviXav, Windows y MSFS y el avión utilizado. No contiene ni tu identificador de SimBrief ni tu ruta completa."],
        },
      },
    },
  };

  TEXT.it = {
    title: "Guida all’uso",
    intro: "Cosa fa ogni menu e come configurare NaviXav passo dopo passo.",
    contents: "Indice",
    sections: {
      start: {
        title: "Primi passi",
        items: {
          install: ["Installazione", "Installa NaviXav come una normale applicazione Windows, mai nella cartella Community. Solo il pannello MSFS facoltativo va lì, e solo quando lo richiedi nelle impostazioni."],
          plan: ["Origine del piano", "Inserisci il tuo Pilot ID SimBrief (o il nome utente) in {settings} > {settings_section_general}. Puoi anche usare il piano di volo caricato in MSFS (.PLN)."],
          msfs: ["Simulatore", "Avvia MSFS 2024 e carica un volo: NaviXav si collega da solo. I dati di navigazione già recuperati restano disponibili offline."],
          first_import: ["Prima importazione", "Genera un OFP in SimBrief, poi fai clic su «{complete}». NaviXav completa partenza e arrivo e spiega ogni sua scelta."],
          interface: ["Interfaccia guidata o classica", "In modalità guidata, una barra in alto riassume il volo attivo, la fase, il tempo rimanente e la prossima azione, e mette in evidenza il modulo utile. La modalità classica mostra tutti i moduli alla pari."],
        },
      },
      toolbar: {
        title: "Barra degli strumenti",
        items: {
          import: ["Importa piano di volo", "Ricarica l’ultimo OFP SimBrief, o il piano MSFS, e ricalcola partenza e arrivo."],
          simbrief: ["Crea in SimBrief / Apri un .PLN", "A seconda dell’origine del piano, apre l’editor SimBrief nel browser o permette di scegliere un altro file .PLN."],
          sim_status: ["Stato di MSFS", "Verde: collegato. Arancione: simulatore in pausa. Grigio: MSFS offline o nessun volo caricato."],
          theme: ["Aspetto", "Passa dal tema chiaro a quello scuro."],
          settings: ["Impostazioni", "Apre le impostazioni, questa guida e la cronologia delle versioni."],
          update: ["Cerca aggiornamenti", "Verifica se esiste una versione più recente. Il programma di installazione è controllato tramite la sua somma SHA-256 prima di ogni aggiornamento."],
          support: ["Sostieni", "Apre la pagina di sostegno allo sviluppo. NaviXav resta gratuito."],
          quit: ["Esci", "Arresta NaviXav, chiude le connessioni e libera la porta."],
        },
      },
      modules: {
        title: "I moduli",
        items: {
          terminal: ["Piano di volo", "Partenza, rotta e arrivo: piste, SID, STAR, avvicinamento, transizioni, altitudine e livello di transizione, frequenza ILS. Ogni scelta automatica mostra il suo motivo e la sua affidabilità, e può essere modificata."],
          turnaround: ["Scalo", "Con GSX Pro, l’aereo in piazzola visto dall’alto: la cabina si riempie durante l’imbarco, stive e serbatoi si caricano, i mezzi arrivano e ripartono. La cronologia misura il ritmo di ogni servizio e stima l’orario di partenza (TOBT) rispetto all’OFP; il foglio di carico e centraggio segnala ogni modifica dell’ultimo minuto. All’arrivo, una guida all’attracco stimata porta al punto di arresto."],
          map: ["Mappa", "Rotta completa colorata per procedura, posizione e traccia dell’aereo, traffico, vincoli e aree SIGMET. Pulsanti Segui, Rotta completa e Adatta; lo sfondo e ogni livello si nascondono dalla barra della mappa. Il livello «{map_turbulence}» mostra il rischio di turbolenza in aria chiara previsto dall’OFP e la turbolenza segnalata dai piloti vicino alla rotta."],
          ground: ["Rullaggio", "Pianta dell’aeroporto costruita con i dati di MSFS. Fai clic su una piazzola per ottenere un percorso; NaviXav annuncia la prossima manovra e i punti di attesa e sorveglia la velocità di rullaggio."],
          procedures: ["Procedure", "Le checklist del tuo aereo, fase per fase, spuntate automaticamente quando il simulatore lo consente. Le schede separano procedure normali, anormali e di emergenza."],
          flight: ["Monitoraggio del volo", "Fase, prossimo punto, scostamenti, TOD, profilo verticale, monitoraggio del carburante e avvicinamento stabilizzato, configurazione dell’aereo e allarmi. Qui si trova anche il giornale di volo locale."],
          constraints: ["Vincoli", "Tutti i vincoli di quota e velocità di SID, STAR e avvicinamento, nell’ordine del volo."],
          dispatch: ["Dispatch", "Masse, carburante, alternato e tempo di volo dall’OFP SimBrief."],
          aircraft: ["Aereo", "Aereo riconosciuto, equipaggiamenti dichiarati e documenti disponibili."],
          sia: ["Carte ufficiali", "Carte delle autorità nazionali, ordinate per tipo; quelle del tuo volo sono preselezionate. Vengono scaricati solo i PDF aperti."],
          mcdu: ["Scheda MCDU", "I dati da inserire nell’MCDU, nel CDU o nell’FMS, pagina per pagina, con la carta ufficiale accanto."],
          weather: ["Meteo", "METAR e TAF di partenza, arrivo e alternato, vento e temperatura in rotta e SIGMET vicini alla rotta con il testo completo."],
        },
      },
      settings: {
        title: "Le impostazioni",
        intro: "Le impostazioni sono salvate su questo computer. Fai clic su «{save}» per applicarle.",
        items: {
          general: ["Generale e SimBrief", "Lingua, aspetto, organizzazione dell’interfaccia, origine del piano (SimBrief o .PLN di MSFS) e identificativi SimBrief."],
          flight: ["Volo e meteo", "Fonte METAR (SimBrief o in diretta), avvicinamenti preferiti, limiti di vento in coda e al traverso, lunghezza minima della pista e capacità RNP."],
          audio: ["Audio del cockpit", "Annunci vocali e scelta della voce, volume di annunci e allarmi, atmosfera radio ATC, ATC e interfono offline, e download della voce naturale."],
          display: ["Mappa e rullaggio", "Sfondo della mappa, colore della traccia, velocità massime di rullaggio in rettilineo e in virata, allarme sonoro di velocità."],
          traffic: ["Traffico e modelli", "Origine del traffico (VATSIM, IVAO, OpenSky o statico), raggio, numero di aerei, set di modelli (FSLTL o AIG) e i loro percorsi se il rilevamento automatico fallisce."],
          msfs_panel: ["Pannello MSFS", "Installa, aggiorna o rimuove l’icona di NaviXav dalla barra degli strumenti del simulatore."],
          connections: ["Connessioni", "Accesso da telefono o tablet sulla rete locale e collegamento facoltativo con ChartFox."],
          aircraft_procedures: ["Procedure per aereo", "Confronta gli aerei installati in Community con la base di procedure di NaviXav e indica quelli coperti."],
          about: ["NaviXav e sostegno", "Sito del progetto e sostegno allo sviluppo."],
          changelog: ["Cronologia delle versioni", "L’icona a tre linee, in alto nelle impostazioni, elenca tutte le modifiche dalle prime versioni."],
        },
      },
      setup: {
        title: "Configurazione passo dopo passo",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general}: inserisci il Pilot ID (visibile nel tuo account SimBrief) o il nome utente, salva, poi fai clic su «{complete}»."],
          metar: ["Meteo in diretta", "{settings} > {settings_section_flight} > METAR: «{live_metar}». Il meteo si aggiorna ogni 5 minuti senza mai cambiare piste o procedure."],
          voice: ["Annunci vocali", "{settings} > {settings_audio_title}: attiva «{voice_settings_toggle}», scegli una voce, poi «{voice_test}». Le voci sono fornite con NaviXav e funzionano offline. L’interruttore di {tab_flight} le silenzia in qualsiasi momento."],
          voice_volume: ["Volume di annunci e allarmi", "{settings} > {settings_audio_title}: il cursore «{voice_volume}» regola gli annunci vocali e il segnale di velocità eccessiva in rullaggio. Al rilascio viene riprodotto un esempio al livello scelto."],
          tower: ["Torre offline", "{settings} > {settings_audio_title}: «{tower_toggle}». In partenza, una torre simulata si rivolge al vostro volo con nominativo, pista e frequenze del volo caricato: allineamento al punto attesa, autorizzazione al decollo con il vento, trasferimento alle partenze. Tace quando è scelto il traffico VATSIM o IVAO. «{tower_test}» ne riproduce un esempio. Una voce naturale, sintetizzata sul vostro computer, è disponibile come opzione: «{tower_engine_download}» nella stessa sezione, o durante l’installazione. Con la voce naturale, il controllo e il personale di terra accompagnano anche la preparazione: autorizzazione, fine imbarco, foglio di carico, pushback, rullaggio, piazzola e tacchi all’arrivo."],
          traffic: ["Traffico in MSFS", "Installa FSLTL Base Models o AIG AI Traffic, scegli set di modelli e origine in {settings} > {settings_section_traffic}, poi accendi il traffico dalla barra della mappa o del rullaggio."],
          panel: ["Pannello MSFS", "{settings} > {settings_section_msfs_panel} > «{settings_msfs_panel_install}». Al caricamento successivo compare un’icona NaviXav nella barra del simulatore. Quando esce una nuova versione, lo stesso pulsante la aggiorna."],
          tablet: ["Telefono o tablet", "{settings} > {settings_section_connections}: attiva l’accesso, riavvia NaviXav, consenti le reti private se Windows lo chiede, poi apri l’indirizzo mostrato da un dispositivo sulla stessa Wi-Fi."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > «{chartfox_connect}». L’accesso passa dal browser; NaviXav non vede mai la tua password."],
          chatter: ["Atmosfera radio ATC", "{settings} > {settings_audio_title}: attiva «{chatter_toggle}» e regola il volume. Comunicazioni radio in inglese preregistrate suonano in sottofondo secondo la fase del volo; non riguardano il tuo aereo e tacciono durante gli annunci di NaviXav."],
        },
      },
      alerts: {
        title: "Allarmi e annunci",
        items: {
          master: ["MASTER CAUTION e MASTER WARNING", "NaviXav confronta la configurazione dell’aereo con la fase di volo: carrello, flap, luci, regolazione altimetrica, carburante, avvicinamento stabilizzato, SIGMET davanti… Un allarme riguarda solo i sistemi che l’aereo possiede e deve persistere qualche secondo."],
          ack: ["Riconoscere", "Fai clic su un allarme per riconoscerlo. Si riarma da solo al successivo cambio di fase o se la situazione peggiora di nuovo."],
          toggle: ["Disattivare gli allarmi", "L’interruttore «{alerts_toggle}» di {tab_flight} li disattiva tutti. Sono sospesi automaticamente con simulazione accelerata e durante una riproduzione."],
          voice: ["Annunci vocali", "Allarmi, TOD, avvicinamento stabilizzato e istruzioni di rullaggio sono annunciati se gli annunci sono attivi. I termini aeronautici restano in inglese, come in una vera cabina."],
          landing: ["Analisi dell’atterraggio", "Dopo il contatto, NaviXav mostra il rateo di discesa, la stabilità dell’avvicinamento e un voto. Si riapre dal giornale di volo."],
        },
      },
      troubleshooting: {
        title: "Risoluzione dei problemi",
        items: {
          msfs_offline: ["«MSFS offline»", "Verifica che MSFS 2024 sia avviato con un volo caricato, non solo il menu principale. NaviXav ritenta la connessione da solo."],
          no_plan: ["Nessun piano importato", "Verifica il Pilot ID SimBrief e che sia stato generato un OFP. Con l’origine MSFS, carica prima un volo nel simulatore."],
          no_traffic: ["Nessun traffico in MSFS", "Servono un set di modelli rilevato (FSLTL o AIG) e il traffico acceso. La riga di stato sotto la mappa indica cosa manca."],
          disconnects: ["Disconnessioni", "Ogni perdita e ogni ripristino del collegamento SimConnect sono registrati con causa e durata nel registro diagnostico."],
          logs: ["Registro diagnostico", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Allegalo a una segnalazione con le versioni di NaviXav, Windows e MSFS e l’aereo usato. Non contiene né il tuo identificativo SimBrief né la tua rotta completa."],
        },
      },
    },
  };

  TEXT.pt = {
    title: "Guia de utilização",
    intro: "O que faz cada menu e como configurar o NaviXav passo a passo.",
    contents: "Índice",
    sections: {
      start: {
        title: "Primeiros passos",
        items: {
          install: ["Instalação", "Instale o NaviXav como qualquer aplicação do Windows, nunca na pasta Community. Só o painel opcional do MSFS vai para lá, e apenas quando o pedir nas definições."],
          plan: ["Origem do plano", "Introduza o seu Pilot ID do SimBrief (ou nome de utilizador) em {settings} > {settings_section_general}. Também pode usar o plano de voo carregado no MSFS (.PLN)."],
          msfs: ["Simulador", "Inicie o MSFS 2024 e carregue um voo: o NaviXav liga-se sozinho. Os dados de navegação já obtidos continuam disponíveis offline."],
          first_import: ["Primeira importação", "Gere um OFP no SimBrief e clique em «{complete}». O NaviXav completa a partida e a chegada e explica cada uma das suas escolhas."],
          interface: ["Interface guiada ou clássica", "No modo guiado, uma barra no topo resume o voo ativo, a fase, o tempo restante e a próxima ação, e destaca o módulo útil. O modo clássico mostra todos os módulos em pé de igualdade."],
        },
      },
      toolbar: {
        title: "Barra de ferramentas",
        items: {
          import: ["Importar plano de voo", "Recarrega o seu último OFP do SimBrief, ou o plano do MSFS, e recalcula partida e chegada."],
          simbrief: ["Criar no SimBrief / Abrir um .PLN", "Conforme a origem do plano, abre o editor do SimBrief no navegador ou permite escolher outro ficheiro .PLN."],
          sim_status: ["Estado do MSFS", "Verde: ligado. Laranja: simulador em pausa. Cinzento: MSFS offline ou nenhum voo carregado."],
          theme: ["Aparência", "Alterna entre o tema claro e o escuro."],
          settings: ["Definições", "Abre as definições, este guia e o histórico de versões."],
          update: ["Procurar atualizações", "Verifica se existe uma versão mais recente. O instalador é verificado pela sua soma SHA-256 antes de qualquer atualização."],
          support: ["Apoiar", "Abre a página de apoio ao desenvolvimento. O NaviXav continua gratuito."],
          quit: ["Sair", "Para o NaviXav, fecha as ligações e liberta a porta."],
        },
      },
      modules: {
        title: "Os módulos",
        items: {
          terminal: ["Plano de voo", "Partida, rota e chegada: pistas, SID, STAR, aproximação, transições, altitude e nível de transição, frequência ILS. Cada escolha automática mostra o motivo e a confiança, e pode ser alterada."],
          turnaround: ["Escala", "Com o GSX Pro, a aeronave na posição vista de cima: a cabina enche-se durante o embarque, porões e depósitos são carregados e os veículos chegam e partem. A cronologia mede o ritmo de cada serviço e estima a hora de partida (TOBT) face ao OFP; a folha de carga e centragem assinala qualquer alteração de última hora. À chegada, um guiamento de estacionamento estimado leva-o ao ponto de paragem."],
          map: ["Mapa", "Rota completa colorida por procedimento, posição e rasto do avião, tráfego, restrições e zonas SIGMET. Botões Seguir, Rota completa e Ajustar; o fundo e cada camada ocultam-se na barra do mapa. A camada «{map_turbulence}» mostra o risco de turbulência de ar limpo previsto pelo OFP e a turbulência reportada pelos pilotos perto da rota."],
          ground: ["Rolagem", "Planta do aeródromo construída com dados do MSFS. Clique num lugar de estacionamento para obter um percurso; o NaviXav anuncia a próxima manobra e os pontos de espera e vigia a velocidade de rolagem."],
          procedures: ["Procedimentos", "As listas de verificação do seu avião, fase a fase, assinaladas automaticamente quando o simulador o permite. Os separadores distinguem procedimentos normais, anormais e de emergência."],
          flight: ["Acompanhamento do voo", "Fase, próximo ponto, desvios, TOD, perfil vertical, acompanhamento do combustível e aproximação estabilizada, configuração do avião e alarmes. O diário de bordo local também está aqui."],
          constraints: ["Restrições", "Todas as restrições de altitude e velocidade do SID, da STAR e da aproximação, pela ordem do voo."],
          dispatch: ["Despacho", "Massas, combustível, alternante e tempo de voo do OFP do SimBrief."],
          aircraft: ["Avião", "Avião reconhecido, equipamentos declarados e documentos disponíveis."],
          sia: ["Cartas oficiais", "Cartas das autoridades nacionais, ordenadas por tipo; as que correspondem ao seu voo vêm pré-selecionadas. Só são descarregados os PDF que abrir."],
          mcdu: ["Ficha MCDU", "Os dados a introduzir no MCDU, CDU ou FMS, página a página, com a carta oficial ao lado."],
          weather: ["Meteorologia", "METAR e TAF da partida, da chegada e do alternante, vento e temperatura em rota e SIGMET perto da rota com o texto completo."],
        },
      },
      settings: {
        title: "As definições",
        intro: "As definições são guardadas neste computador. Clique em «{save}» para as aplicar.",
        items: {
          general: ["Geral e SimBrief", "Idioma, aparência, organização da interface, origem do plano (SimBrief ou .PLN do MSFS) e identificadores do SimBrief."],
          flight: ["Voo e meteorologia", "Fonte METAR (SimBrief ou em direto), aproximações preferidas, limites de vento de cauda e cruzado, comprimento mínimo de pista e capacidade RNP."],
          audio: ["Áudio do cockpit", "Avisos de voz e escolha da voz, volume dos avisos e alarmes, ambiente de rádio ATC, ATC e intercomunicador offline, e transferência da voz natural."],
          display: ["Mapa e rolagem", "Fundo do mapa, cor do rasto, velocidades máximas de rolagem em reta e em curva, alarme sonoro de velocidade."],
          traffic: ["Tráfego e modelos", "Origem do tráfego (VATSIM, IVAO, OpenSky ou estático), raio, número de aviões, conjunto de modelos (FSLTL ou AIG) e respetivos caminhos se a deteção automática falhar."],
          msfs_panel: ["Painel do MSFS", "Instala, atualiza ou remove o ícone do NaviXav da barra de ferramentas do simulador."],
          connections: ["Ligações", "Acesso a partir de um telemóvel ou tablet na rede local e ligação opcional ao ChartFox."],
          aircraft_procedures: ["Procedimentos por avião", "Compara os aviões instalados em Community com a base de procedimentos do NaviXav e indica os que estão cobertos."],
          about: ["NaviXav e apoio", "Site do projeto e apoio ao desenvolvimento."],
          changelog: ["Histórico de versões", "O ícone de três linhas, no topo das definições, lista todas as alterações desde as primeiras versões."],
        },
      },
      setup: {
        title: "Configuração passo a passo",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general}: introduza o Pilot ID (visível na sua conta SimBrief) ou o nome de utilizador, guarde e clique em «{complete}»."],
          metar: ["Meteorologia em direto", "{settings} > {settings_section_flight} > METAR: «{live_metar}». A meteorologia atualiza-se a cada 5 minutos sem nunca alterar as suas pistas ou procedimentos."],
          voice: ["Avisos de voz", "{settings} > {settings_audio_title}: ative «{voice_settings_toggle}», escolha uma voz e clique em «{voice_test}». As vozes vêm com o NaviXav e funcionam offline. O interruptor de {tab_flight} silencia-as a qualquer momento."],
          voice_volume: ["Volume dos avisos e alarmes", "{settings} > {settings_audio_title}: o cursor «{voice_volume}» regula os avisos de voz e o sinal sonoro de excesso de velocidade na rolagem. Ao soltá-lo, é reproduzido um exemplo no nível escolhido."],
          tower: ["Torre offline", "{settings} > {settings_audio_title}: «{tower_toggle}». Na partida, uma torre simulada dirige-se ao seu voo com o indicativo, a pista e as frequências do voo carregado: alinhamento no ponto de espera, autorização de descolagem com o vento, transferência para as partidas. Cala-se quando o tráfego VATSIM ou IVAO é escolhido. «{tower_test}» reproduz um exemplo. Está disponível como opção uma voz natural, sintetizada no seu computador: «{tower_engine_download}» na mesma secção, ou na instalação. Com a voz natural, o controlo e a equipa de terra acompanham também a preparação: autorização, fim do embarque, folha de carga, pushback, rolagem, posição e calços à chegada."],
          traffic: ["Tráfego no MSFS", "Instale FSLTL Base Models ou AIG AI Traffic, escolha o conjunto de modelos e a origem em {settings} > {settings_section_traffic} e ligue o tráfego na barra do mapa ou da rolagem."],
          panel: ["Painel do MSFS", "{settings} > {settings_section_msfs_panel} > «{settings_msfs_panel_install}». Um ícone do NaviXav aparece na barra do simulador no carregamento seguinte. Quando há uma versão nova, o mesmo botão atualiza-a."],
          tablet: ["Telemóvel ou tablet", "{settings} > {settings_section_connections}: ative o acesso, reinicie o NaviXav, autorize as redes privadas se o Windows pedir e abra o endereço indicado num dispositivo da mesma rede Wi-Fi."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > «{chartfox_connect}». O início de sessão passa pelo navegador; o NaviXav nunca vê a sua palavra-passe."],
          chatter: ["Ambiente de rádio ATC", "{settings} > {settings_audio_title}: ative «{chatter_toggle}» e ajuste o volume. Comunicações de rádio em inglês pré-gravadas tocam em fundo conforme a fase do voo; não dizem respeito ao seu avião e calam-se durante os avisos do NaviXav."],
        },
      },
      alerts: {
        title: "Alarmes e avisos",
        items: {
          master: ["MASTER CAUTION e MASTER WARNING", "O NaviXav compara a configuração do avião com a fase de voo: trem, flaps, luzes, calagem altimétrica, combustível, aproximação estabilizada, SIGMET à frente… Um alarme só diz respeito aos sistemas que o avião tem e tem de persistir alguns segundos."],
          ack: ["Reconhecer", "Clique num alarme para o reconhecer. Volta a armar-se sozinho na mudança de fase seguinte ou se a situação voltar a piorar."],
          toggle: ["Desligar os alarmes", "O interruptor «{alerts_toggle}» de {tab_flight} desativa-os todos. Ficam suspensos automaticamente em simulação acelerada e durante uma repetição."],
          voice: ["Avisos de voz", "Alarmes, TOD, aproximação estabilizada e instruções de rolagem são anunciados se os avisos estiverem ativos. Os termos aeronáuticos ficam em inglês, como num cockpit real."],
          landing: ["Análise da aterragem", "Após o toque, o NaviXav mostra a razão de descida, a estabilidade da aproximação e uma nota. Pode ser reaberta a partir do diário de bordo."],
        },
      },
      troubleshooting: {
        title: "Resolução de problemas",
        items: {
          msfs_offline: ["«MSFS offline»", "Verifique se o MSFS 2024 está a correr com um voo carregado, e não apenas no menu principal. O NaviXav volta a tentar a ligação sozinho."],
          no_plan: ["Nenhum plano importado", "Verifique o Pilot ID do SimBrief e se foi gerado um OFP. Com a origem MSFS, carregue primeiro um voo no simulador."],
          no_traffic: ["Sem tráfego no MSFS", "São precisos um conjunto de modelos detetado (FSLTL ou AIG) e o tráfego ligado. A linha de estado por baixo do mapa indica o que falta."],
          disconnects: ["Desconexões", "Cada perda e cada restabelecimento da ligação SimConnect ficam registados com a causa e a duração no registo de diagnóstico."],
          logs: ["Registo de diagnóstico", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Anexe-o a um relatório com as versões do NaviXav, do Windows e do MSFS e o avião usado. Não contém o seu identificador SimBrief nem a sua rota completa."],
        },
      },
    },
  };

  TEXT.nl = {
    title: "Gebruikershandleiding",
    intro: "Wat elk menu doet en hoe u NaviXav stap voor stap instelt.",
    contents: "Inhoud",
    sections: {
      start: {
        title: "Aan de slag",
        items: {
          install: ["Installatie", "Installeer NaviXav zoals elke Windows-toepassing, nooit in de map Community. Alleen het optionele MSFS-paneel komt daar, en alleen als u erom vraagt in de instellingen."],
          plan: ["Bron van het vliegplan", "Vul uw SimBrief Pilot ID (of gebruikersnaam) in bij {settings} > {settings_section_general}. U kunt ook het in MSFS geladen vliegplan (.PLN) gebruiken."],
          msfs: ["Simulator", "Start MSFS 2024 en laad een vlucht: NaviXav maakt zelf verbinding. Al opgehaalde navigatiegegevens blijven offline beschikbaar."],
          first_import: ["Eerste import", "Genereer een OFP in SimBrief en klik dan op „{complete}”. NaviXav vult vertrek en aankomst aan en licht elke keuze toe."],
          interface: ["Begeleide of klassieke indeling", "In de begeleide modus vat een balk bovenaan de actieve vlucht, de fase, de resterende tijd en de volgende actie samen en zet de nuttige module vooraan. De klassieke indeling toont alle modules gelijkwaardig."],
        },
      },
      toolbar: {
        title: "Werkbalk",
        items: {
          import: ["Vliegplan importeren", "Laadt uw laatste SimBrief-OFP of het MSFS-plan opnieuw en berekent vertrek en aankomst opnieuw."],
          simbrief: ["Maken in SimBrief / .PLN openen", "Opent afhankelijk van de planbron de SimBrief-editor in uw browser of laat u een ander .PLN-bestand kiezen."],
          sim_status: ["MSFS-status", "Groen: verbonden. Oranje: simulator gepauzeerd. Grijs: MSFS offline of geen vlucht geladen."],
          theme: ["Weergave", "Wisselt tussen het lichte en het donkere thema."],
          settings: ["Instellingen", "Opent de instellingen, deze handleiding en de versiegeschiedenis."],
          update: ["Naar updates zoeken", "Controleert of er een nieuwere versie is. Het installatieprogramma wordt vóór elke update gecontroleerd aan de hand van zijn SHA-256-controlesom."],
          support: ["Steunen", "Opent de pagina om de ontwikkeling te steunen. NaviXav blijft gratis."],
          quit: ["Afsluiten", "Stopt NaviXav, sluit de verbindingen en geeft de poort vrij."],
        },
      },
      modules: {
        title: "De modules",
        items: {
          terminal: ["Vliegplan", "Vertrek, route en aankomst: banen, SID, STAR, nadering, transities, transitiehoogte en -niveau, ILS-frequentie. Elke automatische keuze toont haar reden en betrouwbaarheid en kan worden gewijzigd."],
          turnaround: ["Turnaround", "Met GSX Pro het vliegtuig op zijn standplaats van bovenaf: de cabine vult zich tijdens het boarden, ruimen en tanks worden geladen en voertuigen komen en gaan. De tijdlijn meet het tempo van elke dienst en schat de vertrektijd (TOBT) ten opzichte van de OFP; het beladings- en balansblad meldt elke last-minute wijziging. Bij aankomst leidt een geschatte parkeergeleiding naar het stoppunt."],
          map: ["Kaart", "Volledige route gekleurd per procedure, positie en spoor van het vliegtuig, verkeer, beperkingen en SIGMET-gebieden. Knoppen Volgen, Volledige route en Passend maken; de achtergrond en elke laag zijn via de kaartbalk te verbergen. De laag „{map_turbulence}” toont het door de OFP voorspelde risico op clear-air turbulentie en door piloten gemelde turbulentie nabij de route."],
          ground: ["Taxiën", "Luchthavenkaart opgebouwd uit MSFS-gegevens. Klik op een standplaats voor een taxiroute; NaviXav meldt de volgende manoeuvre en de wachtpunten en bewaakt uw taxisnelheid."],
          procedures: ["Procedures", "De checklists van uw vliegtuig, fase per fase, automatisch afgevinkt waar de simulator dat toelaat. Tabbladen scheiden normale, abnormale en noodprocedures."],
          flight: ["Vluchtvolging", "Fase, volgend punt, afwijkingen, TOD, verticaal profiel, brandstofbewaking en gestabiliseerde nadering, vliegtuigconfiguratie en alarmen. Ook het lokale logboek staat hier."],
          constraints: ["Beperkingen", "Alle hoogte- en snelheidsbeperkingen van SID, STAR en nadering, in de volgorde van de vlucht."],
          dispatch: ["Dispatch", "Gewichten, brandstof, uitwijkhaven en vliegtijd uit de SimBrief-OFP."],
          aircraft: ["Vliegtuig", "Herkend vliegtuig, opgegeven uitrusting en beschikbare documenten."],
          sia: ["Officiële kaarten", "Kaarten van de nationale autoriteiten, gesorteerd per type; die bij uw vlucht horen zijn voorgeselecteerd. Alleen de geopende PDF’s worden gedownload."],
          mcdu: ["MCDU-blad", "De gegevens om in te voeren in de MCDU, CDU of FMS, pagina per pagina, met de officiële kaart ernaast."],
          weather: ["Weer", "METAR en TAF van vertrek, aankomst en uitwijkhaven, wind en temperatuur onderweg, en SIGMET’s bij de route met hun volledige tekst."],
        },
      },
      settings: {
        title: "De instellingen",
        intro: "De instellingen worden op deze computer bewaard. Klik op „{save}” om ze toe te passen.",
        items: {
          general: ["Algemeen & SimBrief", "Taal, weergave, indeling van de interface, planbron (SimBrief of MSFS-.PLN) en SimBrief-gegevens."],
          flight: ["Vlucht & weer", "METAR-bron (SimBrief of live), voorkeursnaderingen, limieten voor staart- en zijwind, minimale baanlengte en RNP-geschiktheid."],
          audio: ["Cockpitaudio", "Gesproken meldingen en stemkeuze, volume van meldingen en alarmen, ATC-radiosfeer, offline ATC en intercom, en download van de natuurlijke stem."],
          display: ["Kaart & taxiën", "Kaartachtergrond, kleur van het spoor, maximale taxisnelheid rechtuit en in bochten, geluidsalarm voor snelheid."],
          traffic: ["Verkeer & modellen", "Verkeersbron (VATSIM, IVAO, OpenSky of statisch), straal, aantal vliegtuigen, modellenset (FSLTL of AIG) en hun paden als de automatische detectie mislukt."],
          msfs_panel: ["MSFS-paneel", "Installeert, werkt bij of verwijdert het NaviXav-pictogram in de werkbalk van de simulator."],
          connections: ["Verbindingen", "Toegang vanaf een telefoon of tablet op het lokale netwerk en optionele koppeling met ChartFox."],
          aircraft_procedures: ["Procedures per vliegtuig", "Vergelijkt de in Community geïnstalleerde vliegtuigen met de proceduredatabase van NaviXav en toont welke gedekt zijn."],
          about: ["NaviXav & steun", "Projectwebsite en steun voor de ontwikkeling."],
          changelog: ["Versiegeschiedenis", "Het pictogram met drie streepjes bovenaan de instellingen toont alle wijzigingen sinds de eerste versies."],
        },
      },
      setup: {
        title: "Stap voor stap instellen",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general}: vul de Pilot ID (zichtbaar in uw SimBrief-account) of de gebruikersnaam in, sla op en klik op „{complete}”."],
          metar: ["Live weer", "{settings} > {settings_section_flight} > METAR: „{live_metar}”. Het weer wordt elke 5 minuten bijgewerkt en verandert nooit uw banen of procedures."],
          voice: ["Gesproken meldingen", "{settings} > {settings_audio_title}: zet „{voice_settings_toggle}” aan, kies een stem en klik op „{voice_test}”. De stemmen worden met NaviXav meegeleverd en werken offline. De schakelaar in {tab_flight} zet ze op elk moment stil."],
          voice_volume: ["Volume van meldingen en alarmen", "{settings} > {settings_audio_title}: de schuifregelaar „{voice_volume}” regelt de gesproken meldingen en de piep bij te hoge taxisnelheid. Bij loslaten klinkt een voorbeeld op het gekozen niveau."],
          tower: ["Offline toren", "{settings} > {settings_audio_title}: „{tower_toggle}”. Bij vertrek spreekt een gesimuleerde toren uw vlucht aan met de roepnaam, baan en frequenties van de geladen vlucht: opstellen bij het wachtpunt, startklaring met de wind, overdracht aan departure. Hij zwijgt als VATSIM- of IVAO-verkeer is gekozen. „{tower_test}” speelt een voorbeeld af. Een natuurlijke stem, gemaakt op uw computer, is optioneel beschikbaar: „{tower_engine_download}” in dezelfde sectie, of bij de installatie. Met de natuurlijke stem begeleiden verkeersleiding en grondpersoneel ook de voorbereiding: klaring, einde boarding, beladingsblad, pushback, taxiën, standplaats en blokken bij aankomst."],
          traffic: ["Verkeer in MSFS", "Installeer FSLTL Base Models of AIG AI Traffic, kies de modellenset en de bron in {settings} > {settings_section_traffic} en zet het verkeer aan via de kaart- of taxibalk."],
          panel: ["MSFS-paneel", "{settings} > {settings_section_msfs_panel} > „{settings_msfs_panel_install}”. Bij de volgende keer laden verschijnt een NaviXav-pictogram in de werkbalk van de simulator. Is er een nieuwe versie, dan werkt dezelfde knop die bij."],
          tablet: ["Telefoon of tablet", "{settings} > {settings_section_connections}: zet de toegang aan, start NaviXav opnieuw, sta privénetwerken toe als Windows erom vraagt en open het getoonde adres op een apparaat in hetzelfde wifi-netwerk."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > „{chartfox_connect}”. Het aanmelden loopt via uw browser; NaviXav ziet uw wachtwoord nooit."],
          chatter: ["ATC-radiosfeer", "{settings} > {settings_audio_title}: zet „{chatter_toggle}” aan en stel het volume in. Vooraf opgenomen Engelstalig radioverkeer speelt op de achtergrond volgens de vluchtfase; het gaat niet over uw vliegtuig en zwijgt tijdens de meldingen van NaviXav."],
        },
      },
      alerts: {
        title: "Alarmen en meldingen",
        items: {
          master: ["MASTER CAUTION en MASTER WARNING", "NaviXav vergelijkt de vliegtuigconfiguratie met de vluchtfase: landingsgestel, flaps, lichten, hoogtemeterinstelling, brandstof, gestabiliseerde nadering, SIGMET vooruit… Een alarm geldt alleen voor systemen die het vliegtuig echt heeft en moet enkele seconden aanhouden."],
          ack: ["Bevestigen", "Klik op een alarm om het te bevestigen. Het wordt vanzelf opnieuw actief bij de volgende fasewissel of als de situatie weer verslechtert."],
          toggle: ["Alarmen uitschakelen", "De schakelaar „{alerts_toggle}” in {tab_flight} schakelt ze allemaal uit. Bij versnelde simulatie en tijdens een herhaling worden ze automatisch onderbroken."],
          voice: ["Gesproken meldingen", "Alarmen, TOD, gestabiliseerde nadering en taxi-instructies worden uitgesproken als de meldingen aan staan. Luchtvaarttermen blijven Engels, zoals in een echte cockpit."],
          landing: ["Landingsanalyse", "Na de landing toont NaviXav de daalsnelheid, de stabiliteit van de nadering en een score. Ze is opnieuw te openen vanuit het logboek."],
        },
      },
      troubleshooting: {
        title: "Problemen oplossen",
        items: {
          msfs_offline: ["„MSFS offline”", "Controleer of MSFS 2024 draait met een geladen vlucht en niet alleen in het hoofdmenu. NaviXav probeert de verbinding zelf opnieuw."],
          no_plan: ["Geen plan geïmporteerd", "Controleer de SimBrief Pilot ID en of er een OFP is gegenereerd. Laad met de MSFS-bron eerst een vlucht in de simulator."],
          no_traffic: ["Geen verkeer in MSFS", "Er zijn een gedetecteerde modellenset (FSLTL of AIG) en ingeschakeld verkeer nodig. De statusregel onder de kaart toont wat ontbreekt."],
          disconnects: ["Verbroken verbindingen", "Elk verlies en elk herstel van de SimConnect-verbinding wordt met oorzaak en duur vastgelegd in het diagnoselogboek."],
          logs: ["Diagnoselogboek", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Voeg het toe aan een melding, samen met de versies van NaviXav, Windows en MSFS en het gebruikte vliegtuig. Het bevat noch uw SimBrief-gegevens noch uw volledige route."],
        },
      },
    },
  };

  TEXT.pl = {
    title: "Przewodnik użytkownika",
    intro: "Co robi każde menu i jak krok po kroku skonfigurować NaviXav.",
    contents: "Spis treści",
    sections: {
      start: {
        title: "Pierwsze kroki",
        items: {
          install: ["Instalacja", "Zainstaluj NaviXav jak każdą aplikację Windows, nigdy w folderze Community. Trafia tam tylko opcjonalny panel MSFS, i to wyłącznie na Twoje żądanie w ustawieniach."],
          plan: ["Źródło planu", "Wpisz swój SimBrief Pilot ID (lub nazwę użytkownika) w {settings} > {settings_section_general}. Możesz też użyć planu lotu wczytanego w MSFS (.PLN)."],
          msfs: ["Symulator", "Uruchom MSFS 2024 i wczytaj lot: NaviXav połączy się sam. Pobrane już dane nawigacyjne pozostają dostępne offline."],
          first_import: ["Pierwszy import", "Wygeneruj OFP w SimBrief, a następnie kliknij „{complete}”. NaviXav uzupełnia odlot i przylot oraz uzasadnia każdy swój wybór."],
          interface: ["Interfejs prowadzony lub klasyczny", "W trybie prowadzonym pasek u góry podsumowuje aktywny lot, fazę, pozostały czas i następną czynność oraz wysuwa na pierwszy plan właściwy moduł. Tryb klasyczny pokazuje wszystkie moduły na równi."],
        },
      },
      toolbar: {
        title: "Pasek narzędzi",
        items: {
          import: ["Importuj plan lotu", "Ponownie wczytuje Twój ostatni OFP z SimBrief lub plan z MSFS i przelicza odlot i przylot."],
          simbrief: ["Utwórz w SimBrief / Otwórz plik .PLN", "Zależnie od źródła planu otwiera edytor SimBrief w przeglądarce lub pozwala wybrać inny plik .PLN."],
          sim_status: ["Stan MSFS", "Zielony: połączono. Pomarańczowy: symulator wstrzymany. Szary: MSFS offline lub brak wczytanego lotu."],
          theme: ["Wygląd", "Przełącza między jasnym a ciemnym motywem."],
          settings: ["Ustawienia", "Otwiera ustawienia, ten przewodnik i historię wersji."],
          update: ["Sprawdź aktualizacje", "Sprawdza, czy jest nowsza wersja. Instalator jest weryfikowany za pomocą sumy SHA-256 przed każdą aktualizacją."],
          support: ["Wesprzyj", "Otwiera stronę wsparcia rozwoju. NaviXav pozostaje bezpłatny."],
          quit: ["Zakończ", "Zatrzymuje NaviXav, zamyka połączenia i zwalnia port."],
        },
      },
      modules: {
        title: "Moduły",
        items: {
          terminal: ["Plan lotu", "Odlot, trasa i przylot: drogi startowe, SID, STAR, podejście, przejścia, wysokość i poziom przejściowy, częstotliwość ILS. Każdy automatyczny wybór pokazuje uzasadnienie i pewność, i można go zmienić."],
          turnaround: ["Obsługa postoju", "Z GSX Pro samolot na stanowisku widziany z góry: kabina zapełnia się podczas wsiadania, luki i zbiorniki są ładowane, pojazdy przyjeżdżają i odjeżdżają. Przebieg mierzy tempo każdej usługi i szacuje czas odlotu (TOBT) względem OFP; arkusz załadunku i wyważenia sygnalizuje każdą zmianę w ostatniej chwili. Po przylocie szacowane naprowadzanie prowadzi do punktu zatrzymania."],
          map: ["Mapa", "Pełna trasa w kolorach procedur, pozycja i ślad samolotu, ruch, ograniczenia i strefy SIGMET. Przyciski Śledź, Cała trasa i Dopasuj; tło i każdą warstwę można ukryć z paska mapy. Warstwa „{map_turbulence}” pokazuje ryzyko turbulencji w czystym powietrzu prognozowane przez OFP i turbulencje zgłoszone przez pilotów w pobliżu trasy."],
          ground: ["Kołowanie", "Plan lotniska zbudowany z danych MSFS. Kliknij stanowisko, aby otrzymać trasę; NaviXav zapowiada kolejny manewr i punkty oczekiwania oraz pilnuje prędkości kołowania."],
          procedures: ["Procedury", "Listy kontrolne Twojego samolotu, faza po fazie, odhaczane automatycznie tam, gdzie pozwala na to symulator. Karty oddzielają procedury normalne, nienormalne i awaryjne."],
          flight: ["Śledzenie lotu", "Faza, następny punkt, odchylenia, TOD, profil pionowy, kontrola paliwa i podejście ustabilizowane, konfiguracja samolotu i alarmy. Tu jest też lokalny dziennik lotów."],
          constraints: ["Ograniczenia", "Wszystkie ograniczenia wysokości i prędkości SID, STAR i podejścia, w kolejności lotu."],
          dispatch: ["Dispatch", "Masy, paliwo, lotnisko zapasowe i czas lotu z OFP SimBrief."],
          aircraft: ["Samolot", "Rozpoznany samolot, zadeklarowane wyposażenie i dostępne dokumenty."],
          sia: ["Mapy oficjalne", "Mapy władz krajowych, posortowane według typu; te pasujące do Twojego lotu są wstępnie wybrane. Pobierane są tylko otwarte pliki PDF."],
          mcdu: ["Karta MCDU", "Dane do wprowadzenia do MCDU, CDU lub FMS, strona po stronie, z mapą oficjalną obok."],
          weather: ["Pogoda", "METAR i TAF lotniska odlotu, przylotu i zapasowego, wiatr i temperatura na trasie oraz SIGMET w pobliżu trasy z pełną treścią."],
        },
      },
      settings: {
        title: "Ustawienia",
        intro: "Ustawienia są zapisywane na tym komputerze. Kliknij „{save}”, aby je zastosować.",
        items: {
          general: ["Ogólne i SimBrief", "Język, wygląd, układ interfejsu, źródło planu (SimBrief lub .PLN z MSFS) i identyfikatory SimBrief."],
          flight: ["Lot i pogoda", "Źródło METAR (SimBrief lub na żywo), preferowane podejścia, limity wiatru tylnego i bocznego, minimalna długość pasa i zgodność z RNP."],
          audio: ["Dźwięk w kokpicie", "Komunikaty głosowe i wybór głosu, głośność komunikatów i alarmów, atmosfera radiowa ATC, ATC i interkom offline oraz pobieranie naturalnego głosu."],
          display: ["Mapa i kołowanie", "Tło mapy, kolor śladu, maksymalne prędkości kołowania na prostej i w zakręcie, dźwiękowy alarm prędkości."],
          traffic: ["Ruch i modele", "Źródło ruchu (VATSIM, IVAO, OpenSky lub statyczny), promień, liczba samolotów, zestaw modeli (FSLTL lub AIG) i ich ścieżki, jeśli automatyczne wykrywanie zawiedzie."],
          msfs_panel: ["Panel MSFS", "Instaluje, aktualizuje lub usuwa ikonę NaviXav z paska narzędzi symulatora."],
          connections: ["Połączenia", "Dostęp z telefonu lub tabletu w sieci lokalnej i opcjonalne połączenie z ChartFox."],
          aircraft_procedures: ["Procedury według samolotu", "Porównuje samoloty zainstalowane w Community z bazą procedur NaviXav i pokazuje, które są objęte."],
          about: ["NaviXav i wsparcie", "Strona projektu i wsparcie rozwoju."],
          changelog: ["Historia wersji", "Ikona z trzema kreskami u góry ustawień wymienia wszystkie zmiany od pierwszych wersji."],
        },
      },
      setup: {
        title: "Konfiguracja krok po kroku",
        items: {
          simbrief: ["SimBrief", "{settings} > {settings_section_general}: wpisz Pilot ID (widoczny na koncie SimBrief) lub nazwę użytkownika, zapisz i kliknij „{complete}”."],
          metar: ["Pogoda na żywo", "{settings} > {settings_section_flight} > METAR: „{live_metar}”. Pogoda odświeża się co 5 minut i nigdy nie zmienia Twoich dróg startowych ani procedur."],
          voice: ["Komunikaty głosowe", "{settings} > {settings_audio_title}: włącz „{voice_settings_toggle}”, wybierz głos i kliknij „{voice_test}”. Głosy są dostarczane z NaviXav i działają offline. Przełącznik w {tab_flight} wycisza je w każdej chwili."],
          voice_volume: ["Głośność komunikatów i alarmów", "{settings} > {settings_audio_title}: suwak „{voice_volume}” reguluje komunikaty głosowe i sygnał przekroczenia prędkości kołowania. Po zwolnieniu odtwarzany jest przykład na wybranym poziomie."],
          tower: ["Wieża offline", "{settings} > {settings_audio_title}: „{tower_toggle}”. Przy odlocie symulowana wieża zwraca się do Twojego lotu, używając znaku wywoławczego, pasa i częstotliwości wczytanego lotu: zajęcie pasa w punkcie oczekiwania, zgoda na start z wiatrem, przekazanie do odlotów. Milknie, gdy wybrano ruch VATSIM lub IVAO. „{tower_test}” odtwarza przykład. Opcjonalnie dostępny jest naturalny głos syntezowany na komputerze: „{tower_engine_download}” w tej samej sekcji lub podczas instalacji. Z naturalnym głosem kontrola i obsługa naziemna towarzyszą też przygotowaniu: zgoda, koniec wsiadania, arkusz załadunku, wypychanie, kołowanie, stanowisko i klocki po przylocie."],
          traffic: ["Ruch w MSFS", "Zainstaluj FSLTL Base Models lub AIG AI Traffic, wybierz zestaw modeli i źródło w {settings} > {settings_section_traffic}, a następnie włącz ruch z paska mapy lub kołowania."],
          panel: ["Panel MSFS", "{settings} > {settings_section_msfs_panel} > „{settings_msfs_panel_install}”. Przy następnym wczytaniu w pasku symulatora pojawi się ikona NaviXav. Gdy pojawi się nowa wersja, ten sam przycisk ją zaktualizuje."],
          tablet: ["Telefon lub tablet", "{settings} > {settings_section_connections}: włącz dostęp, uruchom ponownie NaviXav, zezwól na sieci prywatne, jeśli Windows o to poprosi, i otwórz wyświetlony adres na urządzeniu w tej samej sieci Wi-Fi."],
          chartfox: ["ChartFox", "{settings} > {settings_section_connections} > „{chartfox_connect}”. Logowanie odbywa się w przeglądarce; NaviXav nigdy nie widzi Twojego hasła."],
          chatter: ["Atmosfera radiowa ATC", "{settings} > {settings_audio_title}: włącz „{chatter_toggle}” i ustaw głośność. Nagrana wcześniej angielska korespondencja radiowa gra w tle zależnie od fazy lotu; nie dotyczy Twojego samolotu i milknie podczas komunikatów NaviXav."],
        },
      },
      alerts: {
        title: "Alarmy i komunikaty",
        items: {
          master: ["MASTER CAUTION i MASTER WARNING", "NaviXav porównuje konfigurację samolotu z fazą lotu: podwozie, klapy, światła, nastawa wysokościomierza, paliwo, podejście ustabilizowane, SIGMET przed samolotem… Alarm dotyczy tylko systemów, które samolot naprawdę ma, i musi trwać kilka sekund."],
          ack: ["Potwierdzanie", "Kliknij alarm, aby go potwierdzić. Uzbraja się ponownie sam przy następnej zmianie fazy lub gdy sytuacja znów się pogorszy."],
          toggle: ["Wyłączanie alarmów", "Przełącznik „{alerts_toggle}” w {tab_flight} wyłącza wszystkie. Są automatycznie wstrzymywane przy przyspieszonej symulacji i podczas odtwarzania."],
          voice: ["Komunikaty głosowe", "Alarmy, TOD, podejście ustabilizowane i instrukcje kołowania są ogłaszane, gdy komunikaty są włączone. Terminy lotnicze pozostają po angielsku, jak w prawdziwym kokpicie."],
          landing: ["Analiza lądowania", "Po przyziemieniu NaviXav pokazuje prędkość opadania, stabilność podejścia i ocenę. Można ją ponownie otworzyć z dziennika lotów."],
        },
      },
      troubleshooting: {
        title: "Rozwiązywanie problemów",
        items: {
          msfs_offline: ["„MSFS offline”", "Sprawdź, czy MSFS 2024 działa z wczytanym lotem, a nie tylko w menu głównym. NaviXav sam ponawia połączenie."],
          no_plan: ["Nie zaimportowano planu", "Sprawdź SimBrief Pilot ID i czy wygenerowano OFP. Przy źródle MSFS najpierw wczytaj lot w symulatorze."],
          no_traffic: ["Brak ruchu w MSFS", "Potrzebne są wykryty zestaw modeli (FSLTL lub AIG) i włączony ruch. Wiersz stanu pod mapą wskazuje, czego brakuje."],
          disconnects: ["Rozłączenia", "Każda utrata i każde przywrócenie połączenia SimConnect są zapisywane wraz z przyczyną i czasem trwania w dzienniku diagnostycznym."],
          logs: ["Dziennik diagnostyczny", "%LOCALAPPDATA%\\NaviXav\\logs\\navixav.log. Dołącz go do zgłoszenia razem z wersjami NaviXav, Windows i MSFS oraz używanym samolotem. Nie zawiera ani Twojego identyfikatora SimBrief, ani pełnej trasy."],
        },
      },
    },
  };

  return {
    sections: SECTIONS,
    /** Texte du guide dans la langue demandée, l'anglais à défaut. */
    text(language) {
      return TEXT[language] || TEXT.en;
    },
    languages: () => Object.keys(TEXT),
  };
})();
