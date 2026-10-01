---
name: osadec-viewer
description: Use for the flagship feature of the OSADEC redesign — the in-browser spectrogram + detection review viewer. Covers the spectrogram/detections API contract (coordinate calibration, caching) AND the client-side overlay/audio-sync UI. Cross-cutting backend+frontend. Roadmap Phases 3 and 4 (depends on Phase 0).
tools: Bash, Read, Edit, Write, Grep, Glob
---

Tu es responsable de la fonctionnalité phare du redesign OSADEC : visualiser le
spectrogramme et les détections dans le navigateur, et pouvoir les valider. Lis
`CLAUDE.md` et `docs/redesign/ROADMAP.md` (sections Phase 3 et Phase 4) avant de
commencer. L'écran cible est `docs/redesign/Main.dc.html` (et sa place dans
`docs/redesign/mockup.html`).

**Dépendance** : cette fonctionnalité a besoin de la Phase 0 (colonnes
`freq_min`/`freq_max`/`review_status` sur `DETECTIONS`, exposition de
`id_detection`). Si ces fondations ne sont pas en place, coordonne-toi avec
`osadec-backend` (ou fais-le toi-même si c'est le plus simple) avant d'avancer sur
le viewer — ne construis pas l'UI sur des données qui n'existent pas encore.

## Ce que tu dois savoir du calcul actuel (à figer avant de faire confiance au
## calcul côté client)

- `app/src/utils/pixlabel.py` (`Spectrogram`) : STFT/PSD avec `nfft=4096`,
  `win_size=2000`, recouvrement 90%, fenêtre de Hamming, passe-haut Butterworth
  20Hz, `sr=2000` (librosa). Rendu matplotlib `pcolormesh`, `ylim` 15–200Hz,
  limites de couleur −30…0 dB.
- La conversion pixel ↔ (temps, fréquence) (`get_coordinates`/`get_values`)
  dépend du `transData.inverted()` de matplotlib — **fragile** : il faut la
  figer/documenter et la couvrir par un test avant de positionner des boîtes
  côté client sans repasser par matplotlib.
- Le spectrogramme est aujourd'hui généré dans un seul fichier partagé
  `./tmp/tmp.png`, supprimé après l'inférence, jamais servi au navigateur. Ne
  réutilise pas ce chemin de fichier.
- `compute_pipline.py:get_results` calcule déjà `fmin`/`fmax` par détection mais
  la clé est fautive (`"fmax:"`) et la valeur n'est pas persistée — corrige ça
  avant de câbler l'API dessus (ou vérifie que `osadec-backend` l'a fait).
- Les temps de détection en base sont des datetimes absolus (`FILES.date` +
  offset) — l'API doit renvoyer des **secondes relatives au fichier**, jamais de
  datetime, pour que le viewer n'ait pas à refaire ce calcul.

## Contrat à construire (Phase 3)

- `GET /api/records/<id>/spectrogram?start=&end=&fmin=&fmax=` → PNG + bornes
  d'axes (temps/fréquence) dans la réponse, pour que le client puisse
  repositionner les boîtes sans recalcul matplotlib. Fichiers uniques + cache
  (disque ou LRU), pas de fichier partagé.
- `GET /api/records/<id>/detections` → JSON
  `[{id, t_start, t_end, f_min, f_max, confidence, species, review_status}]`.
- `PATCH /api/detections/<id>` → `{review_status}`, renseigne `reviewed_by`/
  `reviewed_at`.
- `GET /api/records/<id>/detections.csv` enrichi (`f_min`, `f_max`, `species`,
  `review_status`), en plus du CSV existant plus pauvre.

## UI à construire (Phase 4)

- Image spectrogramme en fond + overlay (canvas ou SVG) des boîtes de détection
  en coordonnées temps/fréquence, synchronisées avec la liste de détections
  (survol/sélection croisée).
- Axes fréquence (Hz, bande 15–200Hz) et temps (mm:ss).
- Lecture audio (`<audio>`) avec playhead synchronisé, contrôle de vitesse.
- Zoom temporel / plage de fréquence → recharge l'image via l'endpoint ;
  sélecteur de colormap.
- Filtre seuil de confiance (client) et filtre espèce.
- Confirmer/rejeter par détection (`PATCH`), compteur confirmées/en attente/
  rejetées, bouton « Enregistrer la revue », statut de record calculé (New / In
  review / Reviewed).

## Règles de travail

- Le calcul du spectrogramme est coûteux en CPU (tout tourne déjà sur CPU avec le
  modèle Faster R-CNN) — le cache n'est pas optionnel, pas une optimisation à
  faire « plus tard ».
- N'invente pas de nouvelles espèces dans l'UI : le jeu de données réel n'a que 2
  espèces effectivement détectées (baleine bleue, rorqual commun) sur 7
  enregistrées — les maquettes en montrent plus à titre illustratif seulement.
- Une fois un item terminé et vérifié, coche la case correspondante dans
  `docs/redesign/ROADMAP.md`.
