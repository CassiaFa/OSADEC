# OSADEC

Détecteur d'appels de mammifères marins dans des fichiers `.wav` : app Flask +
MySQL (docker-compose), inférence Faster R-CNN (mmdet/mmcv) sur spectrogramme.
Projet 2023, relancé en 2026, actuellement en cours de **redesign** (voir plus bas).

## Faire tourner le projet

```
sh init.sh                       # build + lance la stack (docker compose)
docker exec -it osadec bash
python src/utils/db_tools.py     # vérifie la validité de la base
```
App servie sur `http://localhost:5001` (socket.io sur le même process Flask).

## Architecture

| Chemin | Rôle |
|---|---|
| `app/app.py` | Toutes les routes Flask + le handler Socket.IO (`/progress`) + montage du blueprint `/api`. Auth via `flask.session` (`/logout` explicite). |
| `app/src/utils/db_tools.py` | `Encryptor` (AES, paramétré, OK) + `Database` (toutes les méthodes en requêtes paramétrées `%s` ; les f-strings restantes n'interpolent que des noms de colonnes/conditions figés par le code, jamais une valeur utilisateur). |
| `app/src/api/__init__.py` | Squelette du blueprint `/api` (`GET /api/health`, erreurs 404/400/500 en JSON). Pas encore d'endpoint métier. |
| `app/src/utils/pixlabel.py` | Classe `Spectrogram` : STFT/PSD, rendu matplotlib, conversion pixel ↔ (temps, fréquence) via `transData.inverted()`. |
| `app/src/utils/compute_pipline.py` | Pipeline d'inférence : charge le modèle, génère le spectrogramme (`./tmp/tmp.png`, supprimé après usage), convertit les bbox pixel en (start, end, fmin, fmax, confidence) — fmin/fmax désormais persistés. |
| `app/templates/*.html` | Jinja, CSS/JS vanilla, pas de build, pas de framework. |
| `app/static/{css,js}` | `style.css`, `account.css`, `sign_in.css` ; `dropzone.js`, `script_tab.js`. |
| `db/db_files/init_db.sql` | Schéma : `FILES`, `DETECTIONS`, `PROJECTS`, `SPECIES`, `users` (aucune FK sur `users`). |
| `db/db_files/migrations/` | Migrations additives/idempotentes appliquées après `init_db.sql`/`load_data.sql` (voir `docs/db_migrations.md` pour les appliquer sur une base déjà peuplée). |
| `docs/redesign/` | Maquette + roadmap du redesign (voir section suivante). |

## Redesign en cours

La demande : une interface moderne où l'utilisateur **visualise le spectrogramme et
les détections dans le navigateur** et les valide (confirmer/rejeter), au lieu du
flux actuel (upload → CSV uniquement, spectrogramme jamais envoyé au client).

- **Plan de référence : [`docs/redesign/ROADMAP.md`](docs/redesign/ROADMAP.md)** —
  Phase 0 (fondations : sessions réelles, requêtes paramétrées, schéma, API JSON)
  → Phase 3+4 (endpoint spectrogramme + viewer de revue, cœur de la demande)
  → Phase 1/2/5 (shell, dashboard, upload temps réel) → Phase 6 (finitions).
  Coche les cases au fur et à mesure.
- **Maquette : [`docs/redesign/mockup.html`](docs/redesign/mockup.html)** (ouvrir
  dans un navigateur) + écrans sources `*.dc.html` / `canvas.json`.
- La Phase 0 (fondations) est faite (voir plus bas) ; les écrans eux-mêmes
  (dashboard, explorateur, viewer, upload) restent à implémenter.

### Sous-agents dédiés au redesign

Utiliser les agents définis dans `.claude/agents/` plutôt que de tout traiter dans
le fil principal — chacun porte le contexte technique spécifique à son périmètre :

- **`osadec-backend`** — routes Flask, `db_tools.py`, migrations SQL, blueprint
  `/api`, auth/session, pipeline d'inférence. Phases 0, 3 (partie données), 5.
- **`osadec-frontend`** — templates Jinja, design system CSS, écrans non-viewer
  (dashboard, explorateur, upload, auth). Phases 1, 2, 5 (UI), 6.
- **`osadec-viewer`** — fonctionnalité phare : endpoint spectrogramme + overlay de
  détections + lecture audio synchronisée. Phases 3 (API) et 4 (UI), transverse
  backend/frontend.
- **`osadec-qa`** — sécurité, accessibilité, nettoyage, non-régression. À lancer
  après chaque lot de changements et avant de cocher une phase comme terminée.

## État de la Phase 0 (fondations) — fait au 2026-10-01

Sessions réelles (`flask.session`), requêtes paramétrées dans `db_tools.py`,
colonnes `freq_min`/`freq_max`/`review_status`/`reviewed_by`/`reviewed_at` sur
`DETECTIONS`, persistance de `fmin`/`fmax` (clé `"fmax:"` corrigée), exposition de
`id_detection` (`get_detection`, `update_detection_status`), squelette `/api` :
**faits, vérifiés en conditions réelles contre la base peuplée** (19 fichiers,
5211 détections). Détail dans `docs/redesign/ROADMAP.md` (cases cochées) et
`docs/db_migrations.md`. Seul le cloisonnement par utilisateur
(`PROJECTS.id_user`) reste volontairement non fait (décision produit à trancher).

## Contraintes connues à respecter (ne pas réintroduire / corriger si on y touche)

- **Secrets versionnés** : `db/osadecdb/` (datadir MySQL complet) et des clés TLS
  privées sont dans l'historique git. `app/.env` est gitignored mais fragile
  (`init.sh` l'a déjà corrompu par le passé). Toujours pas corrigé.
- **`/upload` et les routes de téléchargement** ne sont pas protégées par session
  (elles ne dépendaient pas des anciens globals `user`/`state` non plus — pas une
  régression du redesign, mais à traiter si on veut un vrai cloisonnement).
- **Spectrogramme** : un seul fichier partagé `./tmp/tmp.png`, écrit puis supprimé
  à chaque inférence — ne pas réutiliser ce chemin pour l'endpoint à la demande du
  redesign (fichiers uniques + cache). Toujours vrai, à traiter en Phase 3.
- **Base déjà peuplée** (19 fichiers, 5211 détections, 2 espèces réellement
  détectées sur les 7 enregistrées) : toute migration doit être additive et
  idempotente.

## Conventions

- Pas de suite de tests actuellement.
- Messages de commit courts, à l'impératif, parfois avec `Fix #<issue>` (voir
  `git log`).
- Les templates déclarent `lang="fr"` mais le texte est en anglais — l'i18n est
  traitée en Phase 6 du redesign, ne pas mélanger les langues entre-temps dans un
  même écran.
