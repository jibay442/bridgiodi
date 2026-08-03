# Lumio (plugin.video.lumio)

Addon Kodi qui permet de lire les flux d'un addon Stremio "stream-only" (comme [Lumio.tv](https://mylumio.tv)) directement dans Kodi, sans passer par l'application Stremio.

## Pourquoi ce projet ?

Chez moi je fais tourner Kodi sur un boîtier **CoreELEC**, pas d'app Stremio installée dessus. J'utilise [Lumio.tv](https://mylumio.tv) comme fournisseur de flux (via mon propre compte/manifest personnel), et je voulais pouvoir lire ces flux directement depuis Kodi. Ce petit addon fait exactement ça : il interroge le manifest Stremio de Lumio et propose les flux trouvés dans une interface Kodi classique.

## Important : il te faut ton propre manifest Lumio.tv

Cet addon **ne fonctionne pas seul**. Il a besoin d'une URL de manifest Stremio valide, de la forme :

```
https://mylumio.tv/<TON_ID_PERSONNEL>/manifest.json
```

Cette URL est **personnelle et confidentielle** — elle est liée à ton compte Lumio.tv. Ne la partage jamais publiquement (ni dans un dépôt Git, ni sur un forum). Va sur [mylumio.tv](https://mylumio.tv) pour obtenir la tienne, puis renseigne-la dans les réglages de l'addon.

L'addon ne fournit **aucune URL par défaut** volontairement, pour éviter toute fuite ou dépendance à un manifest qui ne t'appartient pas.

## Il te faut aussi une clé API TMDB (gratuite)

Les catalogues viennent de [TMDB](https://www.themoviedb.org). La clé est gratuite : crée un compte, puis *Paramètres → API*, et colle la clé dans l'onglet **Catalogue (TMDB)** des réglages. Sans elle, l'addon ne peut rien afficher.

> This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

## Fonctionnement

1. **Configuration** : renseigne ton URL de manifest Lumio et ta clé TMDB dans les réglages.
2. **Navigation** : le menu principal propose trois sections — **Films**, **Séries**, **Animes** — chacune avec :
   - **Populaires** — le score de popularité TMDB
   - **Box-office** — les plus gros revenus (films uniquement : TMDB n'expose pas de revenus pour les séries)
   - **Mieux notés** — note moyenne, avec un plancher de 200 votes pour écarter les titres à deux votes
   - **Par genre** et **Par année** — navigation en dossiers

   Plus **Rechercher un film / une série** à la racine.
3. **Sélection** : l'addon résout l'identifiant IMDb du titre choisi, interroge ton manifest Lumio sur `/stream/...` et affiche les flux disponibles (nom du fichier, taille).
4. **Lecture** : le flux est joué directement dans Kodi, avec un User-Agent de navigateur ajouté à la requête (nécessaire pour que le CDN accepte la connexion).

### Animes

TMDB n'a **ni type ni genre « anime »**. La détection combine le genre *Animation* et les mots-clés anime de TMDB, ce que recommandent leurs modérateurs. Le réglage *Détection des animes* permet de basculer sur « toute l'animation japonaise », plus large mais qui attrape des animations japonaises qui ne sont pas des animes. Le mode par mot-clé est plus précis mais dépend du travail des bénévoles qui étiquettent, donc les titres très récents peuvent manquer.

### Pourquoi Cinemeta subsiste pour les épisodes

Les catalogues, la recherche et les fiches viennent de TMDB. Mais la **liste des épisodes** reste sur [Cinemeta](https://github.com/Stremio/stremio-addon-catalogs), et ce n'est pas un oubli : les identifiants de flux Stremio ont la forme `tt1234567:saison:épisode`, construite sur la numérotation d'IMDb/TVDB. Celle de TMDB en diverge — surtout sur les animes, où les cours sont découpés en saisons différemment et où les longues séries utilisent une numérotation absolue. Construire les identifiants depuis TMDB casserait silencieusement la recherche de flux.

## Réglages

Les réglages sont organisés en quatre onglets :

| Onglet | Contenu |
|---|---|
| **General** | Journalisation de débogage (détaille les requêtes de flux et les priorités de tri dans le journal Kodi) |
| **Catalogue (TMDB)** | Clé API TMDB, détection des animes, titres pour adultes, enregistrement dans TMDb Helper |
| **Addon (Stremio)** | Ton URL de manifest personnelle (`manifest_url`) |
| **Filter** | Tri des flux par qualité, priorités, lecture automatique du meilleur |

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

  La priorité 1 classe en premier ; en cas d'égalité c'est la priorité 2 qui tranche, puis la 3, etc. Les emplacements laissés sur **Non utilisé** sont ignorés, et un critère mis deux fois n'est compté qu'une fois. Par défaut : Résolution > Dolby Vision > HDR > Taille.

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
- **Always play the best stream automatically** (désactivé par défaut) : si activé, saute complètement la liste de sélection des flux et lance directement le mieux classé (celui du tri ci-dessus). Utile si tu veux un "Play" en un clic sans jamais voir la liste des sources.

  Même avec ce réglage activé, un **menu contextuel « Choisir une source »** (touche menu / clic droit / appui long) ouvre la liste complète sur n'importe quel film ou épisode. Pas besoin d'aller retourner le réglage quand le fichier le mieux classé n'est pas le bon.

## Utiliser Lumio comme lecteur de TMDb Helper

Si tu as [TMDb Helper](https://github.com/jurialmunkey/plugin.video.themoviedb.helper), Lumio peut devenir son **player** : tu lances un film ou un épisode depuis ses listes — ou depuis les widgets et raccourcis de skin qui tirent leur contenu de TMDb Helper — et c'est Lumio qui trouve et joue le flux.

C'est ce qui permet d'avoir un dossier « Continuer à regarder » façon Netflix sans dépendre de Trakt : la création d'une application Trakt (nécessaire pour l'API native, voir Limitations) est désormais réservée aux membres VIP, donc pas d'option côté Lumio pour ça. TMDb Helper, lui, a sa propre intégration Trakt et propose ses widgets de reprise de lecture indépendamment de cette restriction — Lumio n'a plus qu'à servir de player derrière.

Va dans *Catalogue (TMDB)* → **Enregistrer Lumio dans TMDb Helper**, puis choisis « Lumio » comme player dans les réglages de TMDb Helper.

Ce bouton **écrit un fichier dans les données de TMDb Helper** (`addon_data/plugin.video.themoviedb.helper/players/lumio.json`) — c'est le seul moyen, TMDb Helper ne va pas lire les fichiers des autres addons. Rien n'est écrit tant que tu n'appuies pas : pas d'installation automatique au démarrage.

Le réglage **Lancer directement depuis TMDb Helper** (activé par défaut) fait partir le flux le mieux classé sans rien demander. C'est indépendant du réglage de l'onglet *Filter*, qui ne concerne que la navigation dans Lumio : tu peux donc garder le choix manuel des sources en naviguant, et avoir TMDb Helper en un clic. Désactive-le si tu veux aussi choisir la source depuis TMDb Helper.

**Si tu dois cliquer plusieurs fois**, les clics viennent de deux endroits : le dialogue « choisis un player » de TMDb Helper apparaît tant qu'aucun player par défaut n'est défini (réglages TMDb Helper → *Players* → *Default player for movies* **et** *Default player for episodes*, deux réglages distincts), et le sélecteur de sources de Lumio apparaît si le réglage ci-dessus est désactivé.

⚠️ Détail qui compte pour les épisodes : TMDb Helper peut fournir l'identifiant IMDb **de l'épisode** plutôt que celui de la série, ce qui donnerait un identifiant de flux (`tt…:saison:épisode`) que personne ne sert. Lumio résout donc l'identifiant de la série depuis l'identifiant TMDB fourni, et ne retombe sur le `{imdb}` de l'URL qu'en dernier recours.

## Suivi Trakt (watched/reprise de lecture) via script.trakt

Cet addon n'a pas d'intégration Trakt native (voir Limitations), mais il envoie déjà toutes les métadonnées nécessaires (IMDb id, année, titre, saison/épisode) sur l'élément en cours de lecture. Ça veut dire que l'addon officiel **[script.trakt](https://kodi.wiki/view/Add-on:Trakt)** (disponible dans le repo officiel Kodi ou sur [github.com/razzeee/script.trakt](https://github.com/razzeee/script.trakt)) fonctionne automatiquement par-dessus, sans aucune configuration côté Lumio :

1. Installe `script.trakt` (Add-ons → Installer depuis le dépôt → Vidéo → Trakt, ou via zip depuis leur repo GitHub).
2. Autorise-le avec ton compte Trakt normal (son propre écran d'autorisation, pas besoin de créer d'application ni d'être VIP — c'est lui qui gère ça avec ses propres identifiants).
3. Regarde un film/épisode via Lumio comme d'habitude : script.trakt détecte la lecture, marque "vu" sur Trakt une fois le seuil de visionnage atteint, et synchronise la reprise de lecture entre appareils.

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

## Installation

1. Télécharge ou clone ce dépôt.
2. Copie le dossier `plugin.video.lumio/` dans le répertoire `addons` de ton Kodi (ou installe-le via "Installer depuis un fichier zip").
3. Va dans les réglages de l'addon et renseigne ton URL de manifest Lumio personnelle, ainsi que ta clé API TMDB.
4. Profite !

## Crédits

Le logo de l'addon (`resources/icon.png`) est celui de [mylumio.tv](https://mylumio.tv), l'addon Stremio qui fournit les flux.
