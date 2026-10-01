# OSADEC

Détecteur d'appels de mammifères marins dans des fichiers `.wav` : app Flask +
MySQL (docker-compose), inférence Faster R-CNN (mmdet/mmcv) sur spectrogramme.
Projet 2023, relancé en 2026, **redesign terminé le 2026-10-01** (voir plus bas).

## Faire tourner le projet

```
sh init.sh                       # build + lance la stack (docker compose)
docker exec -it osadec bash
python src/utils/db_tools.py     # vérifie la validité de la base
```
App servie sur `http://localhost:5001` (socket.io sur le même process Flask).
Tests : `docker exec osadec python -m pytest tests -v` (voir `docs/testing.md`).

**Docker build** : `app/Dockerfile` compile `mmcv-full` depuis les sources (pas de
wheel py3.11, voir `docs/relaunch_2026-08.md`) — c'est l'étape lente/fragile.
`COPY requirements.txt` + `pip install -r requirements.txt` sont placés **après**
cette compilation exprès : ne jamais les remettre avant, sous peine de recompiler
`mmcv-full` à chaque modification de `requirements.txt`.

## Architecture

| Chemin | Rôle |
|---|---|
| `app/app.py` | Routes Flask (pages + upload) + handler Socket.IO (`/progress`, room par client) + montage du blueprint `/api`. Auth via `flask.session`. Upload : tâche de fond (`socketio.start_background_task`), progression par fenêtre ciblée par client. |
| `app/src/api/` | Blueprint `/api` : `__init__.py` (squelette, erreurs JSON), `records.py` (spectrogramme à la demande, détections, revue, CSV enrichi), `projects.py` (stats, listing/recherche/pagination, vignettes). |
| `app/src/utils/db_tools.py` | `Encryptor` (AES, paramétré) + `Database`, 100% requêtes paramétrées (les f-strings restantes n'interpolent que des noms de colonnes figés par le code, jamais une valeur utilisateur). |
| `app/src/utils/pixlabel.py` | Classe `Spectrogram` : STFT/PSD, rendu matplotlib, `axis_bounds()` fige la conversion pixel ↔ (temps, fréquence) pour le client (testé, voir `app/tests/test_pixel_calibration.py`). |
| `app/src/utils/compute_pipline.py` | Pipeline d'inférence (fenêtrage, `fmin`/`fmax` persistés) + génération de vignettes spectrogramme. |
| `app/templates/*.html` | Jinja. `base.html` (auth-aware) / `app_base.html` (rail + top bar, écrans connectés) / `record_review.html` (viewer). |
| `app/static/{css,js}` | `app.css` = design system (tokens, dark mode, composants partagés) ; `viewer.css`/`viewer.js` = viewer ; `dashboard.js`/`files.js`/`app_shell.js` = dashboard/explorateur ; `dropzone.js`/`script_tab.js` = upload. |
| `app/tests/` | Suite pytest (23 tests : `/api`, calibration pixel↔temps/fréquence, statuts de revue). Voir `docs/testing.md`. |
| `db/db_files/init_db.sql` | Schéma : `FILES`, `DETECTIONS` (+ `freq_min`/`freq_max`/`review_status`/`reviewed_by`/`reviewed_at`), `PROJECTS`, `SPECIES`, `users` (aucune FK sur `users`). |
| `db/db_files/migrations/` | Migrations additives/idempotentes (voir `docs/db_migrations.md` pour les appliquer sur une base déjà peuplée). |
| `docs/redesign/` | Maquette + roadmap du redesign (voir section suivante). |

## Redesign (terminé)

La demande initiale : une interface moderne où l'utilisateur **visualise le
spectrogramme et les détections dans le navigateur** et les valide
(confirmer/rejeter), au lieu du flux d'origine (upload → CSV uniquement).

**Toutes les phases du plan sont faites** — voir
[`docs/redesign/ROADMAP.md`](docs/redesign/ROADMAP.md) pour le détail (cases
cochées) : sessions réelles + SQL paramétré (Phase 0), design system + dark mode
(Phase 1), dashboard + explorateur + vignettes (Phase 2), endpoint spectrogramme +
détections + revue (Phase 3), viewer spectrogramme + overlay de détections +
lecture audio synchronisée (Phase 4, fonctionnalité phare), upload en tâche de
fond avec progression par fenêtre et UI sans reload (Phase 5), accessibilité/i18n
anglais partout/responsive mobile/nettoyage/tests (Phase 6).

Seuls deux points restent **volontairement** non faits, ce sont des décisions
produit/risque, pas des oublis :
- **Cloisonnement par utilisateur** (`PROJECTS.id_user` + FK) : personne n'a
  demandé de séparer les projets par utilisateur, tout le monde voit tout
  aujourd'hui, comme avant le redesign.
- **Secrets dans l'historique git** (`db/osadecdb/`, clés TLS privées) : nécessite
  une réécriture d'historique sur `main` — ne jamais le faire sans confirmation
  explicite de l'utilisateur à ce moment précis.

- **Maquette (pour référence visuelle)** : [`docs/redesign/mockup.html`](docs/redesign/mockup.html).

### Sous-agents dédiés au redesign

Agents définis dans `.claude/agents/` (visibles après redémarrage de session) :
`osadec-backend` (Flask/db_tools/API/pipeline), `osadec-frontend`
(templates/CSS/JS hors viewer), `osadec-viewer` (fonctionnalité spectrogramme +
revue, transverse), `osadec-qa` (sécurité/accessibilité/non-régression). Utiles
pour toute évolution future du projet, pas seulement ce redesign.

**Travail concurrent** : plusieurs de ces agents ont régulièrement tourné en
parallèle sur ce projet. Pour que ça marche sans collision, partitionner
explicitement les fichiers/sections de fichiers touchés par chaque agent (en
particulier `app/app.py`, édité par plusieurs phases : donner à chacun une zone
d'insertion disjointe, ex. "insère ta route juste après la fonction X").
`git stash -u` s'est révélé dangereux en cours de route (a supprimé des fichiers
non suivis d'agents concurrents avant d'échouer à les nettoyer) — éviter, préférer
la plumbing git (`git read-tree`/`commit-tree`) pour toute réécriture d'historique
qui doit laisser l'arbre de travail intact.

## Contraintes connues à respecter (ne pas réintroduire)

- **Secrets versionnés** : `db/osadecdb/` (datadir MySQL complet) et des clés TLS
  privées sont dans l'historique git (`main`). `app/.env` est gitignored mais
  fragile (`init.sh` l'a déjà corrompu par le passé). Toujours pas corrigé —
  risque de réécriture d'historique, cf. ci-dessus.
- **Base déjà peuplée** (19 fichiers d'origine + ceux uploadés depuis, 2 espèces
  réellement détectées sur les 7 enregistrées) : toute migration doit être
  additive et idempotente.
- **`app/bucket`/`app/tmp` sont vides par défaut** dans un environnement de dev
  frais (gitignorés) : la plupart des enregistrements de démo n'ont pas de `.wav`
  réel sur disque (spectrogramme/vignette/audio → 404 propre, pas un bug) ; seuls
  les fichiers réellement uploadés en ont.
- **Piège CSS `[hidden]`** : si un élément togglé par `.hidden = true/false` en JS
  a aussi une règle CSS `display: ...` sur sa classe, cette règle l'emporte sur le
  `[hidden]` natif — toujours ajouter `.ma-classe[hidden] { display: none; }`
  (rencontré et corrigé deux fois dans ce projet : `viewer.css`, `account.css`).

## Conventions

- Suite de tests : `app/tests/` (pytest), voir `docs/testing.md`.
- Messages de commit courts, à l'impératif, parfois avec `Fix #<issue>` (voir
  `git log`).
- `lang="en"` partout (tout le texte de l'app est en anglais, pas de FR/EN réel).
