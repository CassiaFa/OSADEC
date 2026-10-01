# Migrations de la base `DATA`

Le schéma initial vit dans `db/db_files/init_db.sql` (+ `load_data.sql` pour les
données d'exemple). Ces deux fichiers sont montés dans l'image `mysql:8.0` comme
scripts `docker-entrypoint-initdb.d` (`docker-compose.yml`) : **MySQL ne les
exécute qu'une seule fois, au tout premier démarrage d'un datadir vide**
(`db/osadecdb/`). Une fois la base initialisée (ce qui est déjà le cas ici — 19
fichiers, 5211 détections), ces scripts ne sont plus rejoués automatiquement.

Pour faire évoluer le schéma sans perdre les données existantes, on ajoute des
scripts de migration additifs et idempotents dans `db/db_files/migrations/`,
numérotés (`0001_...sql`, `0002_...sql`, ...).

## Comment une migration est appliquée

- **Nouvelle installation** (datadir vide) : chaque migration est aussi montée
  dans `docker-compose.yml` sous `/docker-entrypoint-initdb.d/<n>_migration_....sql`
  (numérotée après `1_schema.sql` et `2_load_data.sql`), donc elle s'exécute
  automatiquement avec le reste au premier `docker compose up`.
- **Installation existante** (datadir déjà initialisé, comme la base actuelle) :
  il faut l'appliquer à la main une fois, pendant que le conteneur `osadecdb`
  tourne :

  ```sh
  docker exec -i osadecdb mysql -uroot -pgodofdb29 DATA < db/db_files/migrations/0001_detection_review.sql
  ```

  (adapter le mot de passe s'il a été changé dans `docker-compose.yml`). Chaque
  script vérifie l'`INFORMATION_SCHEMA` avant d'altérer la table, donc le relancer
  par erreur (ou au prochain démarrage sur un datadir déjà migré) est sans danger.

## Migration 0001 — `0001_detection_review.sql`

Ajoute à `DETECTIONS` :

| Colonne | Type | Rôle |
|---|---|---|
| `freq_min` | `FLOAT NULL` | Borne basse (Hz) de la boîte de détection, calculée par `compute_pipline.py` mais jusqu'ici non persistée. |
| `freq_max` | `FLOAT NULL` | Borne haute (Hz), idem. |
| `review_status` | `ENUM('pending','confirmed','rejected') NOT NULL DEFAULT 'pending'` | Statut de revue humaine d'une détection. Toutes les lignes existantes passent à `'pending'` par défaut. |
| `reviewed_by` | `INT NULL` | Id de l'utilisateur ayant revu la détection (pas de FK vers `users` pour l'instant). |
| `reviewed_at` | `TIMESTAMP NULL` | Date de la revue. |

Ajoute aussi un index `idx_detections_review_status` sur `review_status` (utile
pour les filtres de la Phase 2 du redesign).

Rien n'est supprimé ni réécrit : les 5211 détections déjà en base gardent leurs
`start`/`stop`/`confidence`/`id_species`, et se retrouvent avec
`freq_min`/`freq_max` à `NULL` et `review_status='pending'` jusqu'à la prochaine
analyse ou revue.
