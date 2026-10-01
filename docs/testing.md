# Lancer les tests

Phase 6 du redesign (`docs/redesign/ROADMAP.md`). La suite vit sous
`app/tests/` et utilise `pytest`.

## Pourquoi dans le conteneur

`Database.__HOST` (dans `app/src/utils/db_tools.py`) est le littéral `"db"` :
ça ne résout que sur le réseau docker-compose de la stack. Les tests ouvrent
donc une vraie connexion MySQL via `Database.open_connexion()` et doivent
tourner **dans le conteneur `osadec`**, pas sur la machine hôte.

## Pré-requis

`pytest` est listé dans `app/requirements.txt`. L'image `osadec` ne le
contient que si elle a été reconstruite après l'ajout de cette ligne :

```
docker compose build app && docker compose up -d app
```

Attention : `app/Dockerfile` fait `COPY requirements.txt` *avant* de compiler
`mmcv-full` depuis les sources — toute modification de `requirements.txt`
invalide le cache Docker de cette étape et déclenche une recompilation
complète (déjà signalée comme pénible dans `CLAUDE.md`/`relaunch_2026-08.md`).
Ce n'est pas spécifique à l'ajout de `pytest` : c'est vrai pour n'importe quel
changement de `requirements.txt` avec l'ordre actuel des étapes du
`Dockerfile`. Si vous voulez éviter ce coût au quotidien, une solution simple
est d'installer `pytest` à la volée dans un conteneur déjà construit plutôt
que de reconstruire l'image à chaque fois :

```
docker exec osadec pip install pytest
```

(installation perdue au prochain `docker compose up --build`, mais suffisante
pour lancer la suite ponctuellement sans attendre une recompilation de
`mmcv-full`).

## Lancer la suite

Depuis la racine du dépôt :

```
docker exec -it osadec python -m pytest tests -v
```

(`pytest` est invoqué avec `python -m` plutôt que directement pour garantir
que `/osadec` — le `WORKDIR` du conteneur, où vivent `app.py` et `src/` — est
sur `sys.path` ; `app/tests/conftest.py` fait de toute façon le nécessaire
pour que l'import de `app` fonctionne quel que soit le répertoire courant.)

## Ce que couvre la suite

- `test_api_health.py` : `/api/health`, 404 JSON générique sur `/api/...`.
- `test_api_detections.py` : `GET /api/records/<id>/detections` (temps
  relatifs en secondes, pas de datetime absolu exposé), export CSV enrichi,
  404 sur un id de record inexistant.
- `test_api_spectrogram.py` : `GET /api/records/<id>/spectrogram` — 200 +
  en-têtes `X-Axis-*` sur le seul enregistrement de cet environnement qui a un
  vrai `.wav` sur disque (`id_file=32`, fixture partagée avec les autres
  agents pour la revue manuelle — ce test ne fait que des `GET`, jamais
  d'écriture), 400 sur une plage temps/fréquence invalide, 404 sur un id
  inexistant *et* sur un record dont le fichier audio est absent du disque.
- `test_api_detection_review.py` : `PATCH /api/detections/<id>` — 401 sans
  session, 400 sur un statut invalide, 404 sur un id inexistant, cycle complet
  `pending -> confirmed -> rejected -> pending` avec vérification de
  `reviewed_by`/`reviewed_at`.
- `test_api_projects.py` : `/api/projects`, `/api/projects/<id>/stats`,
  `/api/projects/<id>/records`, `/api/records` (recherche, tri/filtre
  invalides -> 400), `/api/species`.
- `test_pixel_calibration.py` : fait tourner
  `src/utils/verify_pixel_calibration.py` (script de vérification manuelle
  préexistant, non modifié) et vérifie qu'il réussit — couvre la conversion
  pixel <-> (temps, fréquence) documentée dans `Spectrogram.axis_bounds()`.

## Données

La suite ne touche jamais aux 19-20 fichiers / 5200+ détections déjà en base,
ni au projet `test_toto` / `id_file=32` utilisé par les autres agents pour la
revue manuelle (lecture seule dessus, pour le test de spectrogramme qui a
besoin d'un vrai fichier audio). Elle crée son propre projet/fichier/
détections isolés (`pytest_fixture_project` / `pytest_fixture_record.wav`,
voir `app/tests/conftest.py`) et les supprime en fin de session de test.
