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

- [ ] `GET /api/projects/<id>/stats` : nb records, nb détections, heures d'audio,
      espèces, en attente.
- [ ] Dashboard (`Dashboard.dc.html`) : cartes stats, records récents, détections par
      espèce, carte « modèle de détection ».
- [ ] Explorateur (`Files.dc.html`) : recherche par nom, filtres espèce / statut /
      date, tri, **pagination côté serveur** (`get_files` avec `limit`/`offset`).
- [ ] Vignettes spectrogramme par record : générer un PNG basse résolution à
      l'analyse, stocker dans `bucket/spectrograms/<id>.png`, servir via route
      statique (`send_from_directory`).

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

- [ ] Composant viewer : image spectrogramme en fond (canvas ou `<img>`), overlay
      SVG/canvas des boîtes de détection en coordonnées temps/fréquence.
- [ ] Axes fréquence (Hz) et temps (mm:ss), grille, bande affichée 15–200 Hz (cf.
      `plt.ylim` actuel).
- [ ] Lecture audio : `<audio>` sur le `.wav` (ou segment), playhead synchronisé,
      contrôle de vitesse.
- [ ] Zoom temporel + plage de fréquence → recharge l'image via l'endpoint ;
      sélecteur de colormap.
- [ ] Panneau détections : liste synchronisée avec l'overlay (survol / sélection
      croisée), filtre **seuil de confiance** (client), filtre espèce.
- [ ] Confirmer / rejeter par détection → `PATCH` ; compteur
      « X confirmées · Y en attente · Z rejetées » ; bouton « Enregistrer la revue ».
- [ ] Statut du record calculé (`New` / `In review` / `Reviewed`).

## Phase 5 — Upload & analyse en temps réel

Écran `Upload.dc.html`.

- [ ] Inférence en tâche de fond (`socketio.start_background_task`), la requête
      `POST /upload` répond immédiatement avec un id de job.
- [ ] Progression **par fenêtre** (`fenêtre k/N`), émise dans une **room par client**
      (fin du broadcast global sur `/progress`).
- [ ] UI : dropzone + formulaire métadonnées 2 colonnes, panneau d'analyse à étapes
      (upload → spectrogramme → détection → sauvegarde), **sans reload de page** ;
      notification + lien direct vers le viewer quand la revue est prête.
- [ ] Robustesse : appeler réellement `allowed_file`, définir `MAX_CONTENT_LENGTH`,
      gérer les fichiers < 300 s (la fenêtre de queue actuelle demande un offset
      négatif).

## Phase 6 — Finitions

- [ ] Accessibilité : `role="tab"`/`tabpanel`, gestion du focus, contrastes.
- [ ] i18n FR / EN (les templates déclarent `lang="fr"` mais tout le texte est en
      anglais).
- [ ] Responsive mobile complet (aujourd'hui : zéro `@media`).
- [ ] Nettoyage : routes mortes (`/form`, `/reset-password`), JS commenté
      (`script_tab.js`, `dropzone.js`), `logo_white.png` inutilisé, double binding
      des handlers d'upload.
- [ ] Tests : routes `/api`, conversion de coordonnées, statuts de revue.
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
