# Bridgiodi (plugin.video.bridgiodi)

Addon Kodi qui permet de lire les flux d'un ou plusieurs addons Stremio "stream-only" directement dans Kodi, sans passer par l'application Stremio.

## Pourquoi ce projet ?

Chez moi je fais tourner Kodi sur un boîtier **CoreELEC**, pas d'app Stremio installée dessus. J'utilise des fournisseurs de flux Stremio "stream-only" (via mes propres comptes/manifests personnels), et je voulais pouvoir lire ces flux directement depuis Kodi. Cet addon fait exactement ça : il interroge le(s) manifest(s) Stremio configuré(s) et propose les flux trouvés dans une interface Kodi classique.

Bridgiodi n'est pas lié à un fournisseur en particulier : il fonctionne avec n'importe quel addon Stremio qui expose une ressource `/stream/...` (Lumio.tv en est un exemple, mais pas le seul).

## Important : il te faut au moins un manifest Stremio personnel

Cet addon **ne fonctionne pas seul**. Il a besoin d'au moins une URL de manifest Stremio valide, de la forme :

```
https://<fournisseur>/<TON_ID_PERSONNEL>/manifest.json
```

Cette URL est **personnelle et confidentielle** — elle est liée à ton compte chez ce fournisseur. Ne la partage jamais publiquement (ni dans un dépôt Git, ni sur un forum). Renseigne-la dans les réglages de l'addon, onglet **Addons Stremio**.

L'addon ne fournit **aucune URL par défaut** volontairement, pour éviter toute fuite ou dépendance à un manifest qui ne t'appartient pas.

### Plusieurs fournisseurs à la fois

L'onglet **Addons Stremio** propose **5 emplacements** (`#1` à `#5`), chacun optionnel. Tu peux en remplir un seul, ou plusieurs si tu as plusieurs comptes/fournisseurs Stremio.

- Les emplacements sont **prioritaires dans l'ordre** : le `#1` est considéré comme ta source de confiance principale.
- Quand plusieurs sont configurés, les flux trouvés sont **groupés par fournisseur** dans la liste de sélection (préfixés par le nom d'hôte), pas mélangés entre eux — le tri par qualité s'applique *à l'intérieur* de chaque groupe, mais le groupe du `#1` reste toujours en tête.
- La lecture automatique (auto-play) essaie d'abord les flux du `#1`, puis passe au fournisseur suivant seulement si `#1` n'a rien de jouable.
- Si un fournisseur est injoignable, les autres continuent de fonctionner normalement — une erreur sur l'un n'empêche pas les autres de répondre.

## Il te faut aussi une clé API TMDB (gratuite)

Les catalogues viennent de [TMDB](https://www.themoviedb.org). La clé est gratuite : crée un compte, puis *Paramètres → API*, et colle la clé dans l'onglet **Catalogue (TMDB)** des réglages. Sans elle, l'addon ne peut rien afficher.

> This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

## Fonctionnement

1. **Configuration** : renseigne au moins une URL de manifest Stremio et ta clé TMDB dans les réglages.
2. **Navigation** : le menu principal propose trois sections — **Films**, **Séries**, **Animes** — chacune avec :
   - **Reprendre la lecture** — tout ce qui a une position de lecture sauvegardée (voir plus bas)
   - **Populaires** — le score de popularité TMDB
   - **Box-office** — les plus gros revenus (films uniquement : TMDB n'expose pas de revenus pour les séries)
   - **Mieux notés** — note moyenne, avec un plancher de 200 votes pour écarter les titres à deux votes
   - **Par genre** et **Par année** — navigation en dossiers

   Plus une entrée **Rechercher** à la racine (voir plus bas), et — si MDBList est connecté — Up Next, watchlist, et tes listes MDBList.
3. **Sélection** : l'addon résout l'identifiant IMDb du titre choisi, interroge le(s) manifest(s) configuré(s) sur `/stream/...` et affiche les flux disponibles (nom du fichier, taille, fournisseur si plusieurs sont configurés).
4. **Lecture** : le flux est joué directement dans Kodi, avec un User-Agent de navigateur ajouté à la requête (nécessaire pour que le CDN accepte la connexion).

### Animes

TMDB n'a **ni type ni genre « anime »**. La détection combine le genre *Animation* et les mots-clés anime de TMDB, ce que recommandent leurs modérateurs. Le réglage *Détection des animes* permet de basculer sur « toute l'animation japonaise », plus large mais qui attrape des animations japonaises qui ne sont pas des animes. Le mode par mot-clé est plus précis mais dépend du travail des bénévoles qui étiquettent, donc les titres très récents peuvent manquer.

### Pourquoi Cinemeta subsiste pour les épisodes

Les catalogues, la recherche et les fiches viennent de TMDB. Mais la **liste des épisodes** reste sur [Cinemeta](https://github.com/Stremio/stremio-addon-catalogs), et ce n'est pas un oubli : les identifiants de flux Stremio ont la forme `tt1234567:saison:épisode`, construite sur la numérotation d'IMDb/TVDB. Celle de TMDB en diverge — surtout sur les animes, où les cours sont découpés en saisons différemment et où les longues séries utilisent une numérotation absolue. Construire les identifiants depuis TMDB casserait silencieusement la recherche de flux. C'est aussi pour ça que l'intégration MDBList (voir plus bas) reste volontairement à l'écart de la numérotation d'épisodes : son `/upnext` est lui-même basé sur TMDB en interne, donc le même risque s'appliquerait.

## Recherche

Une seule entrée **Rechercher** à la racine, qui interroge à la fois les films et les séries en une seule recherche. En l'ouvrant, tu tombes directement sur :

- **Nouvelle recherche** — ouvre le clavier
- Ton **historique de recherche** juste en dessous (jusqu'à 15 requêtes récentes, la plus récente en premier)

Chaque recherche (nouvelle ou reprise depuis l'historique) alimente cet historique automatiquement.

Cette même entrée répond aussi au **global search** de Kodi : quand un skin appelle un addon vidéo avec `action=search&query=...` sans préciser de type de média, Bridgiodi lance la recherche combinée films+séries — aucune configuration supplémentaire nécessaire.

## Reprise de lecture (sans bibliothèque Kodi, Trakt ni TMDb Helper)

Le réglage **Remember playback position** (*General*, activé par défaut) sauvegarde localement où tu t'es arrêté sur un film ou un épisode, et reprend automatiquement à cet endroit la prochaine fois — sans dépendre d'une entrée de bibliothèque Kodi, de Trakt ou de TMDb Helper.

- Une entrée **Reprendre la lecture** apparaît en haut des sections Films et Séries dès qu'il y a quelque chose en cours.
- Un titre regardé à plus de 90% est considéré terminé et sort de cette liste (repart de zéro la prochaine fois).
- Le bouton *Vider le cache* (voir plus bas) ne touche jamais à ces positions sauvegardées.

## Réglages

Les réglages sont organisés en cinq onglets :

| Onglet | Contenu |
|---|---|
| **General** | Journalisation de débogage, bouton Vider le cache, reprise de lecture, forçage audio VO |
| **Catalogue (TMDB)** | Clé API TMDB, détection des animes, titres pour adultes, lecture directe depuis TMDb Helper, enregistrement dans TMDb Helper |
| **MDBList** | Intégration optionnelle Up Next / watchlist / listes / suivi "vu" (voir plus bas) |
| **Addons Stremio** | Jusqu'à 5 URLs de manifest, par ordre de priorité |
| **Filter** | Tri des flux par qualité, priorités, lecture automatique du meilleur |

### Audio en langue d'origine

Le réglage **Force original-language audio** (*General*, désactivé par défaut) bascule sur la piste audio correspondant à la langue d'origine TMDB juste après le début de la lecture, plutôt que de se fier au flag « default » du fichier — qui est souvent posé sur un doublage plutôt que sur la VO (par exemple un film japonais où la piste française est flaguée par défaut). Ne fonctionne que si l'addon a résolu un id TMDB pour le titre.

Pour les sous-titres, rien à configurer côté addon : les réglages natifs de Kodi (*Réglages → Lecteur → Langue*) gèrent déjà "langue audio = langue d'origine" et "langue des sous-titres préférée", pour peu que le fichier ait des pistes correctement tagguées.

### Filter

- **Sort streams by quality** (activé par défaut) : trie les flux trouvés selon les priorités choisies ci-dessous.
- **Priorité 1 à 7** : sept emplacements, chacun recevant le critère de ton choix parmi :

  | Critère | Classement |
  |---|---|
  | Taille du fichier | le plus gros d'abord, à la **tolérance** près (voir ci-dessous) |
  | Résolution | 4K/2160p > 1080p > 720p |
  | HDR | HDR10+ > HDR10 |
  | Dolby Vision | présent > absent |
  | Canaux audio | 7.1 > 5.1 > 2.0 |
  | Format audio | Atmos > TrueHD > DTS-HD/DTS-X > EAC3/DD+ > AC3/DTS/AAC |
  | Codec vidéo | AV1 > HEVC/x265 > H.264/x264 |

  La priorité 1 classe en premier ; en cas d'égalité c'est la priorité 2 qui tranche, puis la 3, etc. Les emplacements laissés sur **Non utilisé** sont ignorés, et un critère mis deux fois n'est compté qu'une fois. Par défaut, tous les emplacements sont sur **Non utilisé** — le tri par qualité ne fait rien tant que tu n'as pas choisi tes propres priorités.

  Ce tri s'applique **à l'intérieur du groupe de chaque fournisseur Stremio** quand plusieurs sont configurés — voir la section sur les fournisseurs multiples plus haut.

- **Size tolerance** (20 Go par défaut, réglable de 0 à 50 Go) : l'écart en dessous duquel deux fichiers comptent comme de **taille égale**, ce qui laisse la priorité suivante décider entre eux.

  C'est ce qui rend un ordre comme *Taille > Dolby Vision* réellement utile. Avec 20 Go de tolérance :

  | Comparaison | Résultat |
  |---|---|
  | 65 Go DV vs 70 Go HDR | **le DV gagne** — 5 Go d'écart, c'est du bruit |
  | 20 Go DV vs 50 Go HDR | **le 50 Go gagne** — 30 Go d'écart, c'est un vrai saut de qualité |

  L'écart est mesuré **à partir du plus gros fichier de la liste**, pas sur une grille fixe (0–20, 20–40…). C'est important : sur une grille fixe, une borne peut tomber entre deux fichiers quasi identiques — 59 Go et 61 Go se retrouveraient dans deux tranches différentes, et un HDR de 61 Go battrait un DV de 59 Go pour 2 Go d'écart. En ancrant sur le plus gros, tout ce qui est à moins d'une tolérance de lui est forcément à égalité.

  À `0`, la comparaison se fait à l'octet : le plus gros gagne toujours, et **aucun critère placé après la taille ne sert plus à rien**. À taille égale sur tous les critères choisis, la taille exacte départage en dernier recours, pour un ordre stable d'une fois sur l'autre.

  Résolution, HDR, DV, audio et codec sont détectés par **analyse du texte** : Stremio ne fournit aucun champ structuré pour ça, c'est la donnée la plus fiable disponible. Les quatre champs du flux sont analysés — `name`, `title`, `description` et `behaviorHints.filename` — parce que les fournisseurs ne sont pas d'accord entre eux sur où mettre l'information. La taille utilise en priorité le champ `behaviorHints.videoSize` quand il est envoyé, avec repli sur le texte.

  **Si le tri ne fait pas ce que tu attends**, active *General → Journalisation de débogage* et relance une recherche de flux : le journal Kodi liste alors chaque flux avec la valeur calculée pour chaque critère et le texte analysé. Un critère à `0` partout signifie que l'information n'est pas détectable dans ce que le fournisseur envoie — c'est visible immédiatement au lieu de se deviner.
- **Always play the best stream automatically** (désactivé par défaut) : si activé, saute complètement la liste de sélection des flux et lance directement le mieux classé (celui du tri ci-dessus, en respectant l'ordre de priorité des fournisseurs). Utile si tu veux un "Play" en un clic sans jamais voir la liste des sources.

  Même avec ce réglage activé, un **menu contextuel « Choisir une source »** (touche menu / clic droit / appui long) ouvre la liste complète sur n'importe quel film ou épisode. Pas besoin d'aller retourner le réglage quand le fichier le mieux classé n'est pas le bon.

  Avant de lancer un flux automatiquement, l'addon **vérifie que les premiers candidats répondent** (requête `GET` avec plage réduite) et bascule sur le suivant si le mieux classé s'avère mort/expiré côté fournisseur — évite de tomber systématiquement sur un lien cassé sans jamais essayer une alternative.

## Vider le cache

Le bouton **Clear cache** (*General*) supprime les données TMDB/Cinemeta mises en cache (pages de catalogue, fiches, listes d'épisodes), forçant un rechargement à la prochaine visite. Il **ne déconnecte pas** ton compte MDBList et **ne touche pas** à tes positions de reprise de lecture — ce ne sont pas des caches jetables.

## Intégration MDBList (optionnelle)

L'onglet **MDBList** ajoute, une fois activé et un compte connecté, des sections supplémentaires en plus de TMDB/Cinemeta (qui restent les sources de catalogue et de numérotation d'épisodes) :

- **Up Next** — séries en cours avec le prochain épisode non vu
- **Watchlist MDBList** — séries watchlistées, même sans épisode déjà vu (contrairement à Up Next)
- **Mes listes MDBList** et **Listes likées** — navigation dans tes listes perso/likées, chaque titre renvoyant vers la recherche de flux habituelle
- **Suivi du statut "vu"** — signale automatiquement à MDBList les films/épisodes regardés à plus de 80%

### Connexion

1. Crée une **Device Code App** sur [mdblist.com/developer](https://mdblist.com/developer) (gratuit, pas de secret nécessaire pour ce flow).
2. Colle le `client_id` généré dans *MDBList → MDBList client ID*.
3. Active *Enable MDBList integration*, puis appuie sur **Connect MDBList account**.
4. Un code s'affiche à l'écran avec l'URL où le saisir (`mdblist.com/oauth/device/`) — il reste affiché en permanence pendant l'attente, pas de raccourci clavier/presse-papier automatique (Kodi n'a pas d'API clipboard stable).

### Pourquoi ce n'est pas un remplacement de TMDB/Cinemeta

L'`/upnext` de MDBList est lui-même alimenté par une numérotation d'épisodes **basée sur TMDB** en interne — exactement la divergence que Cinemeta permet d'éviter pour la recherche de flux (voir plus haut). Router les épisodes par MDBList réintroduirait ce risque, donc l'intégration reste additive : elle ne remplace ni le catalogue TMDB ni la liste d'épisodes Cinemeta.

### Suivi "vu" : limite technique connue

Cet addon n'a pas de service Kodi en arrière-plan. Le suivi du statut "vu" fonctionne en gardant le process de résolution de lecture actif pendant toute la durée du visionnage (au lieu de rendre la main à Kodi immédiatement après avoir résolu l'URL), pour pouvoir détecter la fin de lecture. Ça fonctionne, mais c'est un choix d'implémentation plus lourd qu'un vrai service Kodi comme `script.trakt`.

## Utiliser Bridgiodi comme lecteur de TMDb Helper

Si tu as [TMDb Helper](https://github.com/jurialmunkey/plugin.video.themoviedb.helper), Bridgiodi peut devenir son **player** : tu lances un film ou un épisode depuis ses listes — ou depuis les widgets et raccourcis de skin qui tirent leur contenu de TMDb Helper — et c'est Bridgiodi qui trouve et joue le flux.

C'est ce qui permet d'avoir un dossier « Continuer à regarder » façon Netflix sans dépendre de Trakt : la création d'une application Trakt (nécessaire pour l'API native, voir Limitations) est désormais réservée aux membres VIP, donc pas d'option côté Bridgiodi pour ça. TMDb Helper, lui, a sa propre intégration Trakt et propose ses widgets de reprise de lecture indépendamment de cette restriction — Bridgiodi n'a plus qu'à servir de player derrière.

Va dans *Catalogue (TMDB)* → **Register Bridgiodi in TMDb Helper**, puis choisis « Bridgiodi » comme player dans les réglages de TMDb Helper.

Ce bouton **écrit un fichier dans les données de TMDb Helper** (`addon_data/plugin.video.themoviedb.helper/players/bridgiodi.json`) — c'est le seul moyen, TMDb Helper ne va pas lire les fichiers des autres addons. Rien n'est écrit tant que tu n'appuies pas : pas d'installation automatique au démarrage.

Le réglage **Play immediately when launched from TMDb Helper** (activé par défaut) fait partir le flux le mieux classé sans rien demander. C'est indépendant du réglage de l'onglet *Filter*, qui ne concerne que la navigation dans Bridgiodi : tu peux donc garder le choix manuel des sources en naviguant, et avoir TMDb Helper en un clic. Désactive-le si tu veux aussi choisir la source depuis TMDb Helper.

**Si tu dois cliquer plusieurs fois**, les clics viennent de deux endroits : le dialogue « choisis un player » de TMDb Helper apparaît tant qu'aucun player par défaut n'est défini (réglages TMDb Helper → *Players* → *Default player for movies* **et** *Default player for episodes*, deux réglages distincts), et le sélecteur de sources de Bridgiodi apparaît si le réglage ci-dessus est désactivé.

⚠️ Détail qui compte pour les épisodes : TMDb Helper peut fournir l'identifiant IMDb **de l'épisode** plutôt que celui de la série, ce qui donnerait un identifiant de flux (`tt…:saison:épisode`) que personne ne sert. Bridgiodi résout donc l'identifiant de la série depuis l'identifiant TMDB fourni, et ne retombe sur le `{imdb}` de l'URL qu'en dernier recours.

## Suivi Trakt (watched/reprise de lecture) via script.trakt

Cet addon n'a pas d'intégration Trakt native (voir Limitations), mais il envoie déjà toutes les métadonnées nécessaires (IMDb id, année, titre, saison/épisode) sur l'élément en cours de lecture. Ça veut dire que l'addon officiel **[script.trakt](https://kodi.wiki/view/Add-on:Trakt)** (disponible dans le repo officiel Kodi ou sur [github.com/razzeee/script.trakt](https://github.com/razzeee/script.trakt)) fonctionne automatiquement par-dessus, sans aucune configuration côté Bridgiodi :

1. Installe `script.trakt` (Add-ons → Installer depuis le dépôt → Vidéo → Trakt, ou via zip depuis leur repo GitHub).
2. Autorise-le avec ton compte Trakt normal (son propre écran d'autorisation, pas besoin de créer d'application ni d'être VIP — c'est lui qui gère ça avec ses propres identifiants).
3. Regarde un film/épisode via Bridgiodi comme d'habitude : script.trakt détecte la lecture, marque "vu" sur Trakt une fois le seuil de visionnage atteint, et synchronise la reprise de lecture entre appareils.

## Fiches complètes dans Kodi et sur la télécommande

Chaque élément — ligne de catalogue, épisode, ligne de flux, et **l'élément en cours de lecture** — porte un jeu complet de métadonnées : titre, titre original, résumé, année, durée, note, genre, casting, réalisateur, classification, plus affiche et fanart, et les identifiants IMDb/TMDB. C'est ce qui fait que [Kore](https://kodi.wiki/view/Kore) affiche une vraie fiche de film au lieu d'un nom de fichier.

Deux détails qui ont leur importance :

- Sur une ligne de flux, le nom du fichier ne vit que dans le **libellé** (pour distinguer les sources), jamais dans le titre de la fiche. Il écrasait auparavant le vrai titre, ce qui est précisément pourquoi Kore ne montrait qu'un nom de fichier.
- Le résumé et les images ne transitent **pas** par l'URL du plugin : elles sont relues depuis un cache disque par identifiant. Sur l'étape de résolution, cette URL contient déjà le lien de flux complet et toutes les métadonnées réencodées une seconde fois — y ajouter un synopsis la pousserait au-delà de la longueur où Kodi et Kore tronquent.

## Limitations connues

- Cet addon ne gère que les flux **HTTP directs** (champ `url` retourné par le manifest). Les éventuels flux **torrent/magnet** (champ `infoHash`) ne sont pas traités ici — il n'y a pas de client torrent ni de résolveur debrid intégré dans cet addon.
- Certains titres n'ont **pas d'identifiant IMDb** chez TMDB. Aucun flux ne peut être trouvé pour ceux-là, et l'addon le dit explicitement au lieu d'afficher une liste vide.
- Pas d'intégration Trakt native : la création d'une application Trakt (nécessaire pour utiliser directement leur API) est désormais réservée aux membres Trakt VIP. Utilise `script.trakt` (voir ci-dessus) pour le suivi/la reprise de lecture à la place.
- TMDB n'expose **pas** de notion de « les plus regardés » : ce n'est pas une métrique de leur API. Le Box-office (revenus) et les Populaires (score de popularité TMDB) sont les substituts les plus proches.
- L'usage de l'API TMDB est **non commercial** uniquement, et les métadonnées mises en cache ne doivent pas dépasser six mois. Le cache de l'addon expire au bout de sept jours.
- 5 emplacements de manifest Stremio maximum — les réglages Kodi ne gèrent pas bien les listes qui grandissent dynamiquement, donc c'est un nombre fixe plutôt qu'un bouton "+ Ajouter".

## Installation

1. Télécharge ou clone ce dépôt.
2. Copie le dossier `plugin.video.bridgiodi/` dans le répertoire `addons` de ton Kodi (ou installe-le via "Installer depuis un fichier zip").
3. Va dans les réglages de l'addon et renseigne au moins une URL de manifest Stremio personnelle (onglet *Addons Stremio*), ainsi que ta clé API TMDB (onglet *Catalogue (TMDB)*).
4. Profite !
