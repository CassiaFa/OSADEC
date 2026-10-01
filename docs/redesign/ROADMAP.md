# Roadmap du redesign OSADEC

Rédigé le 2026-08-31. Objectif : passer de l'interface actuelle (templates Jinja +
CSS/JS maison, sortie CSV uniquement) à une application moderne où l'utilisateur
**visualise le spectrogramme et les détections directement dans le navigateur** et
valide chaque détection.

- Maquette locale : [`mockup.html`](mockup.html) (ouvrir dans un navigateur)
- Maquette en ligne : https://claude.ai/code/artifact/de0dd077-c7bb-402b-aad0-dd5d3d994353
- Écrans sources (artboards) : `Main.dc.html`, `Dashboard.dc.html`, `FilLe es.dc.html`,
  `Upload.dc.html`, `SignIn.dc.html` (+ `canvas.json`)

---

## Où en est le code aujourd'hui

| Sujet | État actuel | Conséquence pour le redesign |
|---|---|---|
| Spectrogramme | Généré côté serveur dans `./tmp/tmp.png`, lu par le modèle, **puis supprimé**. Jamais envoyé au client. | Il faut un **nouvel endpoint** qui produit et sert l'image (ou des données), avec cache. |
| Fréquence des détections | `fmin`/`fmax` sont **calculés** (`compute_pipline.py:get_results`) mais **pas stockés**. Clé `"fmax:"` fautive à corriger. | Ajouter 2 colonnes à `DETECTIONS` + corriger le typo pour tracer des boîtes calibrées en fréquence. |
| Temps des détections | `start`/`stop` = `datetime` absolus (`FILES.date` + offset), pas des secondes. | L'API doit convertir en secondes relatives au fichier pour le viewer. |
| Détection individuelle | `id_detection` existe mais n'est **jamais exposé** par `db_tools.py`. | Nécessaire pour « confirmer / rejeter » une détection. |
| Statut de revue | N'existe pas. | Nouvelle colonne `review_status` sur `DETECTIONS`. |
| Sessions | `user` / `state` sont des **variables globales de module** dans `app.py`. Pas d'isolation multi-utilisateur. | Passer à `flask.session` avant toute fonctionnalité par utilisateur. |
| Injections SQL | f-strings dans `check_user`, `get_files`, `get_detections`, `get_projects`, `get_categories`, `get_all_info`. | À passer en requêtes paramétrées (déjà signalé dans `relaunch_2026-08.md`). |
| Propriété projet/fichier | Aucune : `users` n'a aucune FK. | Ajouter `PROJECTS.id_user` (+ FK) si on veut cloisonner par utilisateur. |
| Inférence | **Synchrone dans `POST /upload`**, barre de progression = 9 étapes diffusées à **tous** les clients du namespace `/progress`. | Passer en tâche de fond, progression par fenêtre, ciblée par client (room/sid). |
| Front | Templates Jinja, CSS/JS vanilla, pas de build, pas de framework. | On peut garder Jinja pour les pages simples et n'ajouter du JS que pour le viewer. |

---

## Principes

- **Rétro-compatible avec la base existante** : migrations additives, la base peuplée
  doit continuer à tourner.
- **API JSON séparée du rendu** : nouvelles routes sous `/api/...`, versionnables et
  testables indépendamment du HTML.
- **Pas de réécriture front massive** : Jinja + un seul bundle CSS (design system) +
  un « îlot » JS pour le viewer interactif. Un framework SPA reste optionnel (voir
  *Décisions à trancher*).
- **Livrable de valeur minimale** = Phase 0 (partiel) + Phase 3 + Phase 4 : le viewer
  spectrogramme + revue. C'est le cœur de la demande.

---

## Phase 0 — Fondations techniques (prérequis, invisible)

Bloque les phases par utilisateur et la revue de détections.

- [x] Sessions Flask réelles : supprimer les globals `user`/`state`, utiliser
      `flask.session`, protéger les routes ; corriger la route `/<deconnexion>` qui
      masque toute URL à un segment.
- [x] Requêtes paramétrées dans `app/src/utils/db_tools.py` (toutes les méthodes en
      f-string).
- [x] Migration de schéma `DETECTIONS` :
      `freq_min FLOAT`, `freq_max FLOAT`,
      `review_status ENUM('pending','confirmed','rejected') NOT NULL DEFAULT 'pending'`,
      `reviewed_by INT NULL`, `reviewed_at TIMESTAMP NULL`.
- [x] Persister `fmin`/`fmax` : corriger la clé `"fmax:"` (`compute_pipline.py`),
      étendre `Database.add_detection`.
- [x] Exposer `id_detection` (`get_detections`, nouvelle `get_detection`,
      `update_detection_status`).
- [ ] (Optionnel, si cloisonnement) `PROJECTS.id_user INT` + FK `users(id)` ; filtrer
      `get_projects` / `get_files` par utilisateur.
- [x] Script de migration idempotent + note dans `docs/` (base déjà peuplée).
- [x] Squelette `/api/` (blueprint Flask, réponses JSON, gestion d'erreurs).

## Phase 1 — Shell applicatif & design system

- [x] Tokens de design : palette oklch (accent océan `#0b6a76`, corail détections
      `#e0623d`), typo IBM Plex Sans / Mono, espacements, rayons ; un seul
      `static/css/app.css` ; **dark mode** ; **responsive**.
- [x] Composants partagés : rail d'icônes (64 px), top bar + sélecteur de projet,
      boutons, champs, tableaux, pills de statut, dropzone.
- [x] `base.html` : navigation consciente de l'authentification (compte /
      déconnexion quand connecté), suppression du header commenté et du lien
      « Sign in » permanent.
- [x] Migrer `index`, `sign_in`, `sign_up`, `forgot-password` vers le nouveau style
      (cf. écran `SignIn.dc.html`).
- [x] Implémenter réellement `/forgot-password` (aujourd'hui le formulaire POST vers
      `/reset-password`, route inexistante) **ou** retirer le lien. — décision : pas
      de backend d'envoi d'email dans ce projet, donc le lien reste mais le
      formulaire est remplacé par un message explicite (voir
      `forgot-password.html`), plus de POST vers une route inexistante.

## Phase 2 — Dashboard & explorateur de records

- [x] `GET /api/projects/<id>/stats` : nb records, nb détections, heures d'audio,
      espèces, en attente.
- [x] Dashboard (`Dashboard.dc.html`) : cartes stats, records récents, détections par
      espèce, carte « modèle de détection ».
- [x] Explorateur (`Files.dc.html`) : recherche par nom, filtres espèce / statut /
      date, tri, **pagination côté serveur** (`get_files` avec `limit`/`offset`).
- [x] Vignettes spectrogramme par record : PNG basse résolution (320×90, 60
      premières secondes, bande 15-200Hz) stocké dans
      `bucket/spectrograms/<id_file>.png`, servi par
      `GET /api/records/<id>/thumbnail` (`app/src/api/projects.py`), généré
      paresseusement à la première requête si absent (+ pré-chauffage
      optionnel via `pipeline(..., id_file=...)` dans `compute_pipline.py`) et
      mis en cache sur disque. Chaque enregistrement renvoyé par
      `/api/projects/<id>/records` et `/api/records` porte désormais
      `has_thumbnail` pour que le client bascule `<img>`/placeholder CSS sans
      deviner. **Portée limitée à l'environnement actuel** : sur les 20
      fichiers en base, un seul (`id_file=32`, `test_20150318_110000.wav`) a un
      `.wav` réellement présent sur disque - c'est le seul à avoir une vraie
      vignette (vérifié) ; les 19 autres renvoient 404 proprement et le reste
      du dataset de démo garde donc le placeholder dégradé CSS
      (`.record-thumb--empty`) - limite de l'environnement, pas un bug. Script
      de backfill ponctuel : `app/src/utils/backfill_thumbnails.py`.

## Phase 3 — Endpoint spectrogramme + données de détection

- [x] `GET /api/records/<id>/spectrogram?start=&end=&fmin=&fmax=` : rend un PNG à la
      demande via la classe `Spectrogram` (`pixlabel.py`), **nom de fichier unique**
      (fin du `tmp.png` partagé), **cache** LRU/disque (clé = record + fenêtre).
      Renvoie aussi les bornes d'axes (échelle temps/fréquence) pour le client.
- [x] `GET /api/records/<id>/detections` : JSON
      `[{id, t_start, t_end, f_min, f_max, confidence, species, review_status}]`,
      temps en **secondes relatives** (conversion depuis `DETECTIONS.start` −
      `FILES.date`).
- [x] `PATCH /api/detections/<id>` : `{review_status: confirmed|rejected|pending}`,
      renseigne `reviewed_by` / `reviewed_at`.
- [x] `GET /api/records/<id>/detections.csv` enrichi : ajouter `f_min`, `f_max`,
      `species`, `review_status` (aujourd'hui `start,end,confidence` seulement).
- [x] Vérifier la calibration pixel → (temps, fréquence) : `Spectrogram.get_values`
      dépend du transform matplotlib `transData` ; figer la géométrie du rendu pour
      que le client puisse re-projeter sans matplotlib.

## Phase 4 — Viewer spectrogramme + revue (fonctionnalité phare)

Écran `Main.dc.html`.

- [x] Composant viewer : image spectrogramme en fond (canvas ou `<img>`), overlay
      SVG/canvas des boîtes de détection en coordonnées temps/fréquence.
      `templates/record_review.html` + `static/js/viewer.js` : `<img>` chargée via
      `fetch()` (pour lire les en-têtes `X-Axis-*`) puis affichée comme blob URL,
      overlay SVG positionné avec exactement la formule documentée dans
      `Spectrogram.axis_bounds()`. Vérifié pixel-perfect avec un fichier de test
      synthétique (3 tons à positions/fréquences connues, boîtes superposées
      correctement, cf. rapport de l'agent `osadec-viewer`).
- [x] Axes fréquence (Hz) et temps (mm:ss), grille, bande affichée 15–200 Hz (cf.
      `plt.ylim` actuel). Grille + graduations dessinées en pourcentage/`viewBox`
      à partir des mêmes bornes `X-Axis-*` (pas de recalcul matplotlib).
- [x] Lecture audio : `<audio>` sur le `.wav` (ou segment), playhead synchronisé,
      contrôle de vitesse. Réutilise la route existante `/account/wav/<file>`
      (supporte déjà les requêtes `Range`, vérifié).
- [x] Zoom temporel + plage de fréquence → recharge l'image via l'endpoint ;
      sélecteur de colormap. Zoom/plage de fréquence pleinement fonctionnels
      (fenêtre plafonnée à 300 s, voir note ci-dessous). Sélecteur de colormap
      **partiel** : filtre CSS côté client (approximation visuelle uniquement,
      le PNG reste rendu en `Greys` côté serveur) car changer le vrai cmap
      matplotlib aurait nécessité de toucher `records.py`/`pixlabel.py`, gelés
      ce tour-ci — voir rapport.
- [x] Panneau détections : liste synchronisée avec l'overlay (survol / sélection
      croisée), filtre **seuil de confiance** (client), filtre espèce.
- [x] Confirmer / rejeter par détection → `PATCH` ; compteur
      « X confirmées · Y en attente · Z rejetées » ; bouton « Enregistrer la revue ».
- [x] Statut du record calculé (`New` / `In review` / `Reviewed`).

## Phase 5 — Upload & analyse en temps réel

Écran `Upload.dc.html`.

- [x] Inférence en tâche de fond (`socketio.start_background_task`), la requête
      `POST /upload` répond immédiatement avec un id de job.
- [x] Progression **par fenêtre** (`fenêtre k/N`), émise dans une **room par client**
      (fin du broadcast global sur `/progress`). Implémenté via la room privée que
      Flask-SocketIO assigne automatiquement à chaque sid (le client renvoie son
      `socket.id` au `POST /upload`) ; cf. `_emit_progress`/`_run_analysis_job`
      dans `app.py`. Vérifié : un client « témoin » connecté en parallèle ne reçoit
      aucun événement de la progression d'un autre client.
- [x] UI : dropzone + formulaire métadonnées 2 colonnes, panneau d'analyse à étapes
      (upload → spectrogramme/détection → terminé), **sans reload de page** ;
      notification + lien direct vers le viewer quand la revue est prête.
      `templates/account.html` + `static/js/dropzone.js` (+ styles dans
      `static/css/account.css`) : formulaire métadonnées en grille 2 colonnes
      (projet en pleine largeur, puis date/profondeur, latitude/longitude),
      panneau à 3 étapes (`Uploaded` / `Spectrogram & detection` / `Done`,
      dérivées des événements `progress` existants — pas d'étape serveur
      distincte pour le spectrogramme seul, donc fusionnée avec la détection
      comme dans `Upload.dc.html`), plus de `window.location.href =
      window.location.href` sur `status:'complete'` : à la place un encart de
      succès avec un lien `/records/<id_file>/review` (URL construite côté
      client depuis un template Jinja `url_for`, jamais codée en dur) et un
      bouton « Upload another file ». Sur `status:'error'` (ou un rejet HTTP
      4xx synchrone de `POST /upload`), le message serveur est affiché dans un
      encart `role="alert"` avec un bouton qui réinitialise le panneau (sans
      reload) en conservant les métadonnées déjà saisies. Vérifié de bout en
      bout avec Playwright contre la stack Docker (upload réel d'un `.wav`
      synthétique signé + revue de l'erreur avec un fichier invalide), voir
      rapport de l'agent `osadec-frontend`.
- [x] Robustesse : appeler réellement `allowed_file`, définir `MAX_CONTENT_LENGTH`,
      gérer les fichiers < 300 s (la fenêtre de queue actuelle demande un offset
      négatif).

## Phase 6 — Finitions

- [x] Accessibilité : `account.html` — tabs réécrits selon le pattern WAI-ARIA
      (`static/js/script_tab.js`) : roving `tabindex` (seul l'onglet actif est
      dans l'ordre de tabulation), navigation clavier Flèche gauche/droite/
      Home/End, `aria-controls`/`id`/`aria-labelledby` reliant chaque
      `tab`/`tabpanel` (au lieu de l'`aria-expanded` précédent, incorrect pour
      ce pattern). Focus géré sur le panneau d'upload : premier champ (ou la
      dropzone) invalide reçoit le focus au submit, l'encart de succès/erreur
      reçoit le focus à l'affichage (`tabindex="-1"` + `.focus()`) pour que les
      utilisateurs clavier/lecteur d'écran soient notifiés de la fin de
      l'analyse sans dépendre de la seule perception visuelle. Nouvelles
      classes partagées `.notice-success`/`.notice-danger` dans `app.css`
      (mêmes tokens que `.notice-warning` existant) : contraste texte/fond
      vérifié visuellement (texte foncé sur fond pastel, cohérent avec le
      reste du design system). Non couvert par cet agent : le viewer
      (`record_review.html`/`viewer.js`, périmètre `osadec-viewer`) et le
      formulaire d'upload lui-même pour les attributs ARIA avancés au-delà de
      ce qui existait déjà (labels/required corrects, non retouchés).
- [x] i18n : `base.html` passé en `lang="en"` (hérité par toutes les pages via
      `{% extends %}`, y compris `app_base.html` et `record_review.html` — un
      seul point de correction) ; vérifié qu'aucun texte réellement français ne
      traîne dans `templates/`/`static/js/` (`grep` sur les accents
      français : aucune occurrence hors `charset`/attributs HTML). Traduction
      FR réelle toujours hors scope (décision produit déjà actée en Phase 1).
- [x] Responsive mobile complet (volet frontend) : vérifié à 390×844 (taille
      iPhone 12) avec Playwright + Chromium sur `index`, `sign_in`, `sign_up`,
      `forgot-password`, `account` (onglets Analyse/Explore, panneau d'upload
      à 3 états), `dashboard`, `files` — plus aucun `scrollWidth >
      clientWidth`. Deux bugs réels corrigés (pas seulement esthétiques) :
      (1) `.app-topbar` (rail + marque + sélecteur de projet + compte) ne
      tenait plus sur une ligne à 390 px → nouveau palier `@media (max-width:
      480px)` dans `app.css` qui masque la marque texte/le séparateur et
      réduit le sélecteur de projet ; (2) un nom d'utilisateur long sans
      espace (ex. `qa_responsive_1790882157`) forçait la largeur de
      `.user-table` au-delà du viewport (mot insécable) → `overflow-wrap:
      anywhere` ajouté sur `.user-table th/td` dans `account.css`. Le viewer
      (`record_review.html`) a été vérifié visuellement à 390 px sans le
      modifier (périmètre `osadec-viewer`) : pas de débordement horizontal
      constaté, mais `Could not load detections`/spectrogramme bloqué sur
      « Loading » observés pendant les tests (semble lié à l'état de travail
      en cours côté `osadec-viewer`/`records.py`, pas un problème CSS — à
      confirmer par cet agent).
- [x] Nettoyage de routes mortes (backend) : `/form` (`handle_form`) supprimée
      d'`app.py` — vestige confirmé inutilisé (`grep` sur templates/static : aucun
      formulaire ni JS ne postait dessus). `/reset-password` confirmé toujours
      absent (déjà nettoyé en Phase 1) et toujours non référencé nulle part.
      Volet frontend (fait par cet agent) : bloc entier de JS commenté retiré
      de `static/js/script_tab.js` (ancien duplicata du upload handling,
      jamais exécuté) ; `static/images/logo_white.png` supprimé (`grep`
      confirmé : aucune référence dans templates/CSS/JS/py) ; double binding
      des handlers d'upload corrigé — `account.html` avait à la fois
      `onsubmit="handleSubmit(event)"`/`onchange="handleFileSelect(this)"`
      inline **et** les mêmes handlers rebranchés par `dropzone.js`, donc
      chaque soumission déclenchait deux `POST /upload` (vérifié dans les logs
      serveur avant correction) ; les attributs inline ont été retirés,
      `dropzone.js` est la seule source de binding désormais. Bonus trouvé en
      testant : `uploadFile()` faisait aussi `formData.append('file', ...)`
      en plus du fichier déjà porté par `new FormData(form)`, envoyant deux
      fois les mêmes octets par requête — supprimé.
- [x] Tests : routes `/api`, conversion de coordonnées, statuts de revue —
      `app/tests/` (pytest, ajouté à `app/requirements.txt`), voir
      `docs/testing.md` pour l'exécution (doit tourner dans le conteneur
      `osadec`, `Database.__HOST` ne résout que sur le réseau docker-compose).
      23 tests, tous verts contre une vraie instance Flask + la base peuplée
      (`/api/health`, `/api/records/<id>/detections` + `.csv`,
      `/api/records/<id>/spectrogram` (200 + en-têtes `X-Axis-*`, 400, 404),
      `PATCH /api/detections/<id>` (401/400/404 + cycle complet
      pending→confirmed→rejected→pending avec `reviewed_by`/`reviewed_at`),
      `/api/records`, `/api/projects`, `/api/projects/<id>/stats`,
      `/api/projects/<id>/records`, `/api/species`, et la calibration pixel
      <-> (temps, fréquence) via `src/utils/verify_pixel_calibration.py`).
- [ ] Secrets dans le dépôt : `db/osadecdb/` et clés TLS privées versionnées
      (rappel de `relaunch_2026-08.md`) — à sortir de l'historique.

---

## Dépendances entre phases

```
Phase 0 ──┬─► Phase 1 ──► Phase 2
          ├─► Phase 3 ──► Phase 4        (chemin de valeur principal)
          └─► Phase 5
Phase 6 : transverse, en continu
```

Phase 4 dépend de Phase 3 qui dépend de Phase 0 (schéma + `id_detection`). Phases 1,
2 et 5 sont parallélisables une fois la Phase 0 faite.

## Décisions à trancher

1. **Stack front** : Jinja + îlot JS pour le viewer (recommandé, léger) **vs** SPA
   React/Vue sur l'API (plus lourd, utile seulement si l'app grossit beaucoup).
2. **Rendu du spectrogramme** : PNG calculé côté serveur (simple, réutilise
   l'existant) **vs** renvoyer la matrice PSD / des tuiles et rendre côté client
   (zoom fluide, plus de travail).
3. **Vignettes** : fichiers sur disque **vs** table dédiée **vs** génération à la
   volée avec cache.
4. **Cloisonnement par utilisateur** : nécessaire maintenant, ou tout le monde voit
   tous les projets (comme aujourd'hui) ?

## Risques

- Coût CPU du calcul de spectrogramme à la demande (modèle et DSP tournent déjà sur
  CPU) → cache indispensable, éventuellement pré-calcul à l'analyse.
- Fragilité de la conversion pixel → temps/fréquence (dépend du rendu matplotlib
  actuel) : à figer et couvrir par des tests avant de tracer des boîtes.
- Le jeu de données d'exemple ne contient que 2 espèces (baleine bleue, rorqual
  commun) et le modèle est à 2 classes : les maquettes montrent plus d'espèces à
  titre illustratif.
