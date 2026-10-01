# Relance du projet — août 2026

Notes de dépannage rédigées le 2026-08-26, après plusieurs années sans exécuter le projet.
Objectif : retrouver un `docker compose up` fonctionnel et garder une trace des causes.

## État final

Stack lancé et vérifié :

```
app | running | 0.0.0.0:5001->5000/tcp
db  | running | 0.0.0.0:3307->3306/tcp
```

Application accessible sur **http://localhost:5001**.

Vérifications OK :

- routes `/`, `/sign_in`, `/sign_up`, `/forgot-password`, `/account` → HTTP 200
- handshake Socket.IO (`/socket.io/?EIO=4&transport=polling`) → 200
- `python src/utils/db_tools.py` dans le conteneur → base connectée, données présentes
  (5211 détections, 19 fichiers, 7 projets, 7 espèces, 1 utilisateur)
- chargement du modèle Faster-RCNN (`mmdet` / `mmcv-full`) → OK
- cycle inscription puis connexion → page compte rendue

## Problèmes trouvés et corrigés

### 1. Build Docker cassé (blocage principal)

`app/requirements.txt` demande `mmcv-full==1.7.1`, sans wheel pour Python 3.11 → pip le
compile depuis les sources. Son `setup.py` fait `import pkg_resources`, que les versions
récentes de `setuptools` / `pip` (dans l'image `python:3.11` actuelle) n'exposent plus.

```
ERROR: Failed to build 'mmcv-full' when getting requirements to build wheel
ModuleNotFoundError: No module named 'pkg_resources'
```

En 2023 l'image de base embarquait un `setuptools` compatible ; l'image en cache
`osadec_app` (3 ans) datait de cette époque.

**Correctif — `app/Dockerfile` :**

- `pip install --upgrade "pip<24.1" "setuptools<70" wheel` (outils de build « d'époque »)
- `pip install "numpy<2"` puis torch/vision/audio en versions CPU exactes
  (`torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2`)
- `pip install --no-build-isolation "mmcv-full==1.7.1"` **avant** `requirements.txt`,
  pour que la compilation voie `torch` / `numpy` / `setuptools` de l'environnement

### 2. `app/.env` corrompu

Fichier généré par `init.sh` puis abîmé au fil des relances :

```
UPLOAD_FOLDER="./bucket"ENCRYPT_KEY=<valeur réelle, redacted>   <- deux variables collées, sans newline
```

- `ENCRYPT_KEY` définie deux fois (valeurs différentes) → déchiffrement des mots de passe
  non déterministe
- `SOCKET_KEY` absente → `app.config['SECRET_KEY'] = None` → sessions Flask / Socket.IO KO

**Correctif :** `.env` réécrit proprement, `SOCKET_KEY` ajoutée, `ENCRYPT_KEY` gardée à sa
première valeur (celle qu'utilisait l'image en cache — voir `app/.env`, non versionné). Si
un compte créé auparavant ne se connecte plus, le recréer via *sign up*.

Contenu attendu de `app/.env` (fichier non versionné, valeurs réelles à ne jamais commiter) :

```
ENCRYPT_KEY=<valeur réelle dans app/.env, ne pas versionner>
ENCODING=latin-1
SOCKET_KEY=<chaîne aléatoire>
UPLOAD_FOLDER=./bucket
```

### 3. Incohérence de port (5000 / 5001)

- `docker-compose.yml` publiait `5001:5001`
- le `Dockerfile` lançait `python -m flask run` → écoute sur **5000**, et **ignore
  Socket.IO** (pas de websocket, pas de barre de progression)
- `app.py` et `init.sh` parlent de **5000**

Résultat : rien ne répondait sur le port publié.

**Correctif :**

- `app/Dockerfile` : `CMD ["python", "app.py"]` → `socketio.run()` sur 5000
- `app/app.py` : `socketio.run(app, ..., allow_unsafe_werkzeug=True)`
  (obligatoire avec Flask-SocketIO 5.3 hors production), et `socketio.run(app, ...)`
  au lieu de `socketio.run(app=app, ...)`
- `app/requirements.txt` : ajout de `simple-websocket==0.10.1` (transport WebSocket
  avec le serveur Werkzeug)
- `docker-compose.yml` : `ports: "5001:5000"` (le port hôte 5000 est déjà pris sur la
  machine — `mlflow_server`)
- `init.sh` : message final `http://localhost:5000` au lieu de l'IP interne du conteneur

### 4. `docker-compose.yml` : `image: mysql` (= latest)

Au prochain `docker pull`, `mysql:latest` = 9.x, qui ne démarre pas proprement sur le
répertoire de données MySQL 8.0 commité dans `db/osadecdb/`.

**Correctif :** épinglé `image: mysql:8.0`. Attribut obsolète `version:` retiré,
`links:` remplacé par `depends_on:`.

### 5. `init.sh` : téléchargement du modèle destructeur

La commande `wget` (astuce Google Drive, cassée depuis des années) :

- contenait `id=FILEID` littéral dans la sous-commande
- était chaînée en `&&` → tout échec empêchait `docker compose up`
- en cas de « succès », écrasait le `.pth` valide (330 Mo) par une page d'erreur HTML

**Correctif :** téléchargement uniquement si le fichier est absent, sans faire échouer le
script ; passage à `docker compose` (v2) avec repli sur `docker-compose` (v1).

### 6. `app/app.py` — plantage sur l'export CSV

Ligne 88 : `pd.DataFrame(data, columns=[...], index=False)` — `index=False` n'est pas un
argument valide du constructeur `DataFrame` → `TypeError` → HTTP 500 sur
`/account/csv/...`.

**Correctif :** `pd.DataFrame(data, columns=['start', 'end', 'confidence'])` puis
`df.to_csv(index=False)`.

## Fichiers modifiés

`app/Dockerfile`, `app/app.py`, `app/requirements.txt`, `app/.env` (non versionné),
`docker-compose.yml`, `init.sh`.

## Points non corrigés (à traiter)

- **Injections SQL** — `app/src/utils/db_tools.py` construit ses requêtes par f-strings
  avec les entrées utilisateur, y compris l'authentification (`check_user`,
  `get_files`, `get_projects`, `get_categories`, `get_all_info`). Exploitable. À reprendre
  en requêtes paramétrées.
- **Absence de vraie session** — `user` et `state` sont des variables globales du module
  `app.py`. Une fois quelqu'un connecté, toute requête (même avec un mauvais mot de passe,
  constaté au test) voit le dernier utilisateur connecté, jusqu'à un appel à
  `/deconnected`. À refaire avec `flask.session`.
- **Secrets dans le dépôt Git** — `db/osadecdb/` (répertoire de données MySQL complet,
  clés TLS privées incluses : `private_key.pem`, `ca-key.pem`, `server-key.pem`) et
  `__pycache__/` sont versionnés. `.gitignore` exclut `models/` et `.env`, donc un
  `git clone` neuf ne contient ni le modèle ni le `.env` : le README (« cloner puis
  `sh init.sh` ») ne suffit pas en l'état.
- **`db/db_files/load_data.sql`** ne s'exécute que sur une base vierge. Aujourd'hui la
  base est peuplée depuis le répertoire de données commité.

## Comment relancer

```sh
sh init.sh
# ou directement :
docker compose up -d --build
```

Puis ouvrir http://localhost:5001.
