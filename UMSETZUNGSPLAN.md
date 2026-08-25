# Umsetzungsplan: RTMPose als ROS2-Node

Lebendes Arbeitsdokument. Phasen nacheinander abarbeiten. Checkboxen in dieser Datei mitführen.

- **Aktuelle Phase:** 6 — Tests und Dokumentation
- **Zieltermin erste Version:** Mitte/Ende September 2026
- **Hardware zuerst:** Workstation (x86), Webcam lokal
- **Später:** Prüfstand (Azure Kinect), optional Jetson Orin (ARM)

---

## Ziel der ersten Version

Eine Python-Node für ROS2 Jazzy, die **einen** RGB-Kamerastream empfängt, mit **RTMPose** 2D-Posen schätzt und die Ergebnisse im ROS-Netzwerk veröffentlicht.

Dieselbe Node muss **mehrfach parallel** laufen können (eine Instanz pro Kamera). Gemeinsame Einstellungen kommen aus YAML; Input/Output nur über Namespace, Remapping und Parameter.

---

## Technische Vorgaben

- [x] ROS2 Jazzy, Ubuntu 24.04, Python
- [x] Docker als Entwicklungsumgebung (zuerst Tutorial-/eigenes Image, später Prüfstand-Image)
- [x] MMPose / RTMPose als Estimator (erst ab Phase 2)
- [x] Ein RGB-Stream pro Node-Instanz
- [x] Keine fest codierten absoluten Topic-Namen
- [x] Konfiguration über ROS-Parameter, YAML, Namespaces, Remappings
- [x] Modell und Detektor nur einmal beim Start laden
- [x] Alle Abhängigkeiten und Modellgewichte mit Version und Lizenz dokumentieren
- [x] RTMPose-Inferenz von ROS trennen (`inference.py` ohne Publisher/Subscriber)

---

## Arbeitsweise

- Immer nur **eine Phase** implementieren.
- Vor Änderungen die vorhandene Repo-Struktur prüfen. Keine Dateien ohne Grund überschreiben.
- Nach jeder Phase: Build + Tests, dann kurzen Status in dieser Datei abhaken.
- Keine Features aus späteren Phasen vorziehen.
- Neue Dependencies nur mit Begründung, fester Version und Lizenz.
- Unsicherheiten nicht erraten — unten unter [Offene Punkte](#offene-punkte) eintragen.

**Nächster Arbeitsschritt:** Phase 6 lokal mit Webcam + Browser-Preview getestet (CPU Tiny ~4–5 FPS). Als Nächstes: Phase-6-Abnahme mit Nils klären, dann Phase 7 (Prüfstand) oder GPU-Image für höhere FPS.

---

## Vorgesehene Projektstruktur

Erst in Phase 1 anlegen. Spätere Phasen ergänzen, nicht vorwegbauen.

```text
pose_estimation_ros/
├── src/
│   ├── human_pose_msgs/          # Phase 4
│   │   └── msg/
│   │       ├── Keypoint2D.msg
│   │       ├── BoundingBox2D.msg
│   │       ├── PersonPose2D.msg
│   │       └── PersonPose2DArray.msg
│   └── rtmpose_ros/
│       ├── rtmpose_ros/
│       │   ├── node.py
│       │   ├── inference.py
│       │   ├── inference_worker.py   # Phase 3, MMPose-Prozess
│       │   ├── estimator_bridge.py   # Phase 3
│       │   ├── frame_slot.py         # Phase 3
│       │   ├── models.py
│       │   ├── visualization.py      # Phase 3
│       │   └── message_converter.py  # Phase 4

│       ├── config/
│       ├── launch/
│       └── test/
├── docker/                       # Phase 1
├── docs/
├── THIRD_PARTY_LICENSES.md       # Phase 2
├── UMSETZUNGSPLAN.md
└── README.md                     # Phase 6, grob schon in 1
```

---

## Phase 1 — Entwicklungsumgebung und ROS-Grundgerüst

**Status:** abgenommen (2026-08-24)  
**Ziel:** Docker + Colcon-Workspace + durchschleifende Image-Node. Noch kein MMPose.

### Todos

- [x] Docker-Umgebung für ROS2 Jazzy und Ubuntu 24.04
- [x] Colcon-Workspace anlegen
- [x] Python-Package `rtmpose_ros` erstellen
- [x] Einfache Node: `sensor_msgs/Image` empfangen
- [x] `cv_bridge`: ROS-Image → OpenCV/NumPy
- [x] Bild unverändert auf Debug-Topic zurückveröffentlichen
- [x] Eingangs-Header (`stamp`, `frame_id`) übernehmen
- [x] Topics nur relativ: Input `image`, Debug-Output `debug_image`
- [x] Launch-Datei + gemeinsame YAML-Konfiguration
- [x] Mock-Input: Testbild, Video, Webcam oder ROS-Bag
- [x] Einfacher Integrationstest (Empfang + Ausgabe)

### Abnahme

- [x] Docker baut reproduzierbar
- [x] `colcon build` läuft fehlerfrei
- [x] Node startet über Launch-Datei
- [x] Ein Bild wird empfangen und wieder veröffentlicht
- [x] Zeitstempel und `frame_id` bleiben erhalten
- [x] Input/Output über Remappings änderbar
- [x] Keine MMPose-Abhängigkeit

### Kurzstatus nach Abschluss

- Geänderte Dateien:
  - `docker/Dockerfile`, `docker/docker-compose.yml`, `docker/entrypoint.sh`, `docker/run-phase1.sh`
  - `src/rtmpose_ros/` (Node, Mock-Kamera, Launch, Config, Tests)
  - `README.md`, `LICENSE`, `.gitignore`
- Entscheidungen:
  - Colcon-Workspace liegt im Repo-Root (`src/`), nicht in einem Extra-Ordner.
  - QoS: `sensor_data` (BEST_EFFORT), passend zu späteren Kameratreibern.
  - YAML mit `/**:`, damit dieselbe Config unter Namespaces funktioniert.
  - Mock-Kamera unterstützt `synthetic`, `image`, `video`, `webcam`.
- Befehle:
  - `docker compose -f docker/docker-compose.yml build`
  - `docker compose -f docker/docker-compose.yml run --rm dev bash /ws/docker/run-phase1.sh`
- Tests:
  - Docker-Image `hiwi-pose-tracking:jazzy` gebaut (ROS2 Jazzy / Ubuntu 24.04).
  - `colcon build --packages-select rtmpose_ros` erfolgreich (6.4 s).
  - `colcon test`: 5/5 bestanden (Launch, Passthrough, Integration inkl. Namespace).
  - Launch-Smoke: `/image_source`, `/pose_estimator`, Topics `/image` und `/debug_image`.
- Offene Probleme:
  - `ros2 topic echo` ohne `--qos-reliability best_effort` verliert Frames, weil die Node `sensor_data` (BEST_EFFORT) nutzt. Das ist erwartet, kein Abnahmefehler.

---

## Phase 2 — RTMPose-Kompatibilität prüfen

**Status:** abgenommen (2026-08-24)  
**Ziel:** Estimator unabhängig von ROS lauffähig, Versionen und Lizenzen fest.

### Todos

- [x] Kompatible Versionen pinnen: Python, PyTorch, MMCV, MMEngine, MMDetection, MMPose
- [x] RTMPose außerhalb von ROS auf einem Testbild ausführen
- [x] Zuerst CPU; GPU-Unterstützung separat prüfen
- [x] Interne Datenmodelle: `Keypoint2D`, `PersonPose2D`, `PoseEstimationResult`
- [x] Abstrakte Estimator-Schnittstelle
- [x] `MockPoseEstimator` und `RTMPoseEstimator`
- [x] Modell/Detektor nur im Konstruktor initialisieren
- [x] Modell, Checkpoint, Detektor, Device konfigurierbar
- [x] Lizenzen und Herkunft dokumentieren (`THIRD_PARTY_LICENSES.md`)

### Abnahme

- [x] Testbild unabhängig von ROS verarbeitbar
- [x] Keypoints, Scores, Bounding-Boxes in interne Struktur übersetzt
- [x] Mock-Estimator für Tests nutzbar
- [x] Anderes RTMPose-Modell ohne Änderung an der ROS-Node eintragbar

### Kurzstatus nach Abschluss

- Geänderte Dateien:
  - `src/rtmpose_ros/rtmpose_ros/models.py`, `inference.py`
  - `src/rtmpose_ros/test/test_mock_estimator.py`, `test_rtmpose_estimator.py`
  - `scripts/run_rtmpose.py`, `docker/install-mmpose.sh`, `docker/run-phase2.sh`, `Dockerfile`
  - `THIRD_PARTY_LICENSES.md`, `README.md`
- Entscheidungen:
  - MMPose liegt in einem eigenen venv `/opt/rtmpose`, ROS bleibt auf System-Python.
  - Default-Alias `human` (RTMPose-m + RTMDet-m Person). Wechsel über `PoseEstimatorConfig` / CLI, ohne ROS-Node.
  - `chumpy` weggelassen (kein Python 3.12, nicht nötig für 2D).
  - `mmdet` mmcv-Obergrenze auf 2.3.0 gepatcht, weil für torch 2.4/cp312 nur mmcv 2.2.0 als CPU-Wheel existiert.
- Befehle:
  - `docker compose -f docker/docker-compose.yml build`
  - `docker compose -f docker/docker-compose.yml run --rm dev bash /ws/docker/run-phase2.sh`
- Tests:
  - colcon: 10 passed, 1 skipped (echte Inferenz nur im venv).
  - Phase-2-Skript: COCO-Sample 640x425, 1 Person, 17 Keypoints, BBox-Score ~0.93, CPU.
  - `torch.cuda.is_available() == False` in diesem Image (kein GPU-Passthrough).
- Offene Probleme:
  - Kommerzielle Nutzung der COCO-trainierten OpenMMLab-Gewichte rechtlich prüfen.
  - GPU-Inferenz ist vorbereitet (`device=cuda`), aber hier nicht ausgeführt.

---

## Phase 3 — RTMPose in die ROS-Node integrieren

**Status:** abgenommen (Phase 4 gestartet)  
**Ziel:** Kamera → Estimator → Debug-Visualisierung, ohne wachsende Queue.

### Todos

- [x] Node an Estimator-Schnittstelle anbinden
- [x] Eingehende Bilder an RTMPose übergeben
- [x] Ergebnisse loggen, dann veröffentlichen
- [x] Latest-frame-wins: max. ein unverarbeitetes Bild, ältere verwerfen
- [x] Parameter: `device`, `pose_model`, `pose_weights`, `detector_model`, `detector_weights`, `keypoint_threshold`, `detection_threshold`, `publish_debug_image`
- [x] Fehlerfälle: keine Person, ungültiges Bild, fehlender Checkpoint, kein CUDA, Inferenzfehler

### Abnahme

- [x] Kamerabild wird mit RTMPose verarbeitet
- [x] Node bleibt bei fehlenden Erkennungen stabil
- [x] Modell wird nicht pro Frame neu geladen
- [x] Keine wachsende Bildwarteschlange
- [x] Debug-Bild zeigt Personen und Skelette

### Kurzstatus nach Abschluss

- Geänderte Dateien:
  - `src/rtmpose_ros/rtmpose_ros/node.py`, `inference_worker.py`, `estimator_bridge.py`, `frame_slot.py`, `visualization.py`, `models.py`
  - `src/rtmpose_ros/config/rtmpose.yaml`
  - Tests, `scripts/run_rtmpose.py`, `docker/run-phase3.sh`, `README.md`
- Entscheidungen:
  - ROS bleibt auf System-Python; RTMPose läuft in einem Subprocess (`/opt/rtmpose/bin/python -m rtmpose_ros.inference_worker`).
  - Mock-Backend bleibt im ROS-Prozess (Tests). Launch-YAML setzt `backend: rtmpose`.
  - Latest-frame-wins über `LatestFrameSlot` (ein Slot, `put` überschreibt).
  - Phase 3 veröffentlicht nur `debug_image` plus Logs, noch keine Pose-Messages.
- Befehle:
  - `docker compose -f docker/docker-compose.yml run --rm dev bash /ws/docker/run-phase3.sh`
- Tests:
  - colcon: 23 passed, 1 skipped (echte Inferenz nicht im ROS-Prozess).
  - Worker-Smoke: COCO 640×425, 1 Person, 17 Keypoints; Load ~26 s, Inferenzen 1075 ms / 786 ms (Modell bleibt geladen).
  - ROS+RTMPose-Smoke: `debug_image` 640×425, Header (`stamp`/`frame_id`) erhalten, 1 Person, Infer ~1180 ms.
- Offene Probleme:
  - GPU-Inferenz im aktuellen CPU-Image nicht verfügbar.
  - Im Smoke-Test kann `dropped_frames` hoch sein, weil der Publisher in einer engen Schleife sendet, während eine Inferenz läuft. Das ist latest-frame-wins, keine undichte Queue.

---

## Phase 4 — ROS-Ausgabeformat

**Status:** abgenommen (Phase 5 gestartet)  
**Ziel:** Strukturierte Pose-Messages. Eigenes Paket `human_pose_msgs`.

Recherche (kein Prüfstand-Format vorgegeben; Hinweis: variable Keypoints für unterschiedliche Quellen):

- `geometry_msgs/PoseArray`: 3D-Posen ohne Keypoints, ungeeignet.
- `vision_msgs/Detection2D`: Box + Klasse, kein Skelett. `BoundingBox2D` dort ist Center+Größe, nicht Top-Left.
- OpenPose-/proprietäre Msgs: feste Topologie (z. B. BODY_25), neue Quellen brauchen ein neues Message-Typ.
- Entscheidung: eigenes `human_pose_msgs` mit **unbeschränktem** `Keypoint2D[]`, plus `skeleton_type` und `keypoint_names` als Schema pro Frame.

```text
Keypoint2D
- uint16 id
- string name
- float32 x
- float32 y
- float32 score

BoundingBox2D          # eigenes Format, Top-Left in Pixeln (nicht vision_msgs)
- float32 x
- float32 y
- float32 width
- float32 height
- float32 score

PersonPose2D
- int32 person_id      # nur innerhalb dieser Message eindeutig, kein Tracking
- float32 score
- bool has_bounding_box
- BoundingBox2D bounding_box
- Keypoint2D[] keypoints   # variable Länge, kein festes [17]

PersonPose2DArray
- std_msgs/Header header
- uint32 image_width
- uint32 image_height
- string skeleton_type
- string model_name
- string[] keypoint_names  # Schema der Quelle, Index = Keypoint2D.id
- PersonPose2D[] poses     # leeres Array = keine Person, trotzdem gültig
```

Koordinaten: Bildpixel, Ursprung oben links, x nach rechts, y nach unten. Header = Kamerabild.

### Todos

- [x] Recherche bestehender ROS-Pose-Message-Formate und Lizenzen
- [x] Package `human_pose_msgs` anlegen
- [x] Converter interne Struktur → ROS-Messages
- [x] Pixelkoordinaten und Koordinatensystem dokumentieren
- [x] Leeres Ergebnis (keine Person) korrekt publizieren

### Abnahme

- [x] Personen strukturiert veröffentlicht
- [x] Keypoints und Confidence pro Person
- [x] Header entspricht dem Kamerabild
- [x] Leeres Array ist gültige Ausgabe
- [x] Tracking-Limitierung dokumentiert

### Kurzstatus nach Abschluss

- Geänderte Dateien:
  - `src/human_pose_msgs/` (msg, CMake, package.xml)
  - `src/rtmpose_ros/rtmpose_ros/message_converter.py`, `node.py`, `models.py`, `inference.py`
  - Tests, Launch, `config/rtmpose.yaml`, `docker/run-phase4.sh`, `README.md`
- Entscheidungen:
  - Kein `vision_msgs`; eigene Box mit Top-Left, damit Pixelkonvention eindeutig bleibt.
  - Variable Keypoints über ROS-Arrays, nicht über einen festen 17er-Satz. Schema in `keypoint_names`.
  - Topic relativ `poses`, QoS `sensor_data`.
- Befehle:
  - `docker compose -f docker/docker-compose.yml run --rm dev bash /ws/docker/run-phase4.sh`
- Tests:
  - colcon: 29 passed, 1 skipped.
  - Converter: COCO-17, 21-Hand, custom 4er-Skelett mit 2 publizierten Joints, leeres Array.
  - Node: `poses` mit Image-Header; leeres `poses[]` bei keiner Person.
- Offene Probleme:
  - Ob der Prüfstand später ein anderes Format erwartet, bleibt offen (eigenes Paket ist die bewusste Wahl).

---

## Phase 5 — Parallelbetrieb

**Status:** abgenommen (Phase 6 gestartet)  
**Ziel:** Variante 1 — eine Node-Instanz pro Kamera, gemeinsame YAML, eigene Topics.

Beispiel:

```text
/camera_1/pose_estimator
/camera_2/pose_estimator
/webcam/pose_estimator
```

### Todos

- [x] Node mehrfach mit unterschiedlichen Namespaces starten
- [x] Gemeinsame Modellparameter aus einer YAML
- [x] Kamera-Topics nur über Remappings
- [x] Keine globalen mutablen Zustände
- [x] Keine gemeinsam beschriebenen Temp-Dateien
- [x] Modellgewichte nur lesend von mehreren Instanzen
- [x] Launch: eine Kamera
- [x] Launch: drei Kameras
- [x] GPU-Speicherbedarf pro Instanz messen

### Abnahme

- [x] Zwei oder mehr Instanzen gleichzeitig
- [x] Eigene Input-/Output-Topics pro Instanz
- [x] Keine vermischten Ergebnisse
- [x] Gemeinsame Settings nur einmal pflegen

### Kurzstatus nach Abschluss

- Geänderte Dateien:
  - `config/cameras.yaml`, `launch/multi_camera.launch.py`, `camera_inventory.py`
  - Launch-Dateien (gemeinsame YAML + `backend`-Override)
  - `test/test_parallel_nodes.py`, `test/test_camera_inventory.py`, `conftest.py`
  - `scripts/report_instance_memory.py`, `docker/run-phase5.sh`
- Entscheidungen:
  - Eine Instanz = ein Namespace. Modellparameter nur in `rtmpose.yaml`.
  - Kamera-Inventar in `cameras.yaml` (Namespaces, `frame_id`, optionale Remaps).
  - Kein Shared-Memory, keine gemeinsamen Temp-Dateien; Worker per Instanz. Checkpoints nur lesen.
  - GPU-VRAM skaliert grob linear mit der Instanzzahl. Im aktuellen Image kein CUDA — Skript hält die Messung fest.
- Befehle:
  - `docker compose -f docker/docker-compose.yml run --rm dev bash /ws/docker/run-phase5.sh`
  - `ros2 launch rtmpose_ros multi_camera.launch.py backend:=mock`
- Tests:
  - colcon: 33 passed, 1 skipped.
  - Zwei Nodes parallel: Bild nur an `camera_1` erzeugt keine Pose auf `camera_2`; `frame_id` bleibt getrennt.
  - Launch-Smoke: 6 Nodes (`camera_1`/`camera_2`/`webcam` × image_source + pose_estimator), eigene Topics, gemeinsame `rtmpose.yaml`.
  - Mock-RSS ~175 MB pro pose_estimator (kein MMPose). GPU: `cuda_available False`.
- Offene Probleme:
  - GPU-Speicher pro Instanz hier nicht messbar (kein `nvidia-smi`). Skript ist vorbereitet.

---

## Phase 6 — Tests und Dokumentation

**Status:** implementiert, Docker-Tests grün (Abnahme durch Nutzer)

### Tests

- [x] RTMPose-Ergebnis → ROS-Message
- [x] 0 / 1 / n Personen
- [x] Confidence-Werte
- [x] Übernahme von `stamp` und `frame_id`
- [x] Paralleler Start von zwei Nodes
- [x] Fehlerhafter Modellpfad
- [x] CPU-Fallback oder klare Fehlermeldung
- [x] Sauberes Beenden von Node und Worker-Thread

### Messungen

- [x] Eingangsauflösung, Kamera-FPS, Ausgabe-FPS
- [x] Mittlere Inferenzzeit, Ende-zu-Ende-Latenz
- [x] Anzahl verworfener Frames
- [x] CPU-, GPU-, Speicherverbrauch
- [x] GPU-Speicher pro Node

### README

- [x] Systemvoraussetzungen
- [x] Docker-Build
- [x] Start mit Testbild / Video / Webcam
- [x] Eine Node / mehrere Nodes
- [x] Parameter-, Topic- und Message-Übersicht
- [x] Modell und Keypoint-Schema
- [x] Bekannte Einschränkungen

### Kurzstatus nach Abschluss

- Geänderte Dateien:
  - `node.py` (Stats, sauberes Beenden), `image_source.py` (SIGINT)
  - Tests: 0/1/n Personen, CUDA-Fehler, Worker-Close, Shutdown
  - `scripts/measure_runtime.py`, `docker/run-phase6.sh`, `README.md`
- Entscheidungen:
  - Messungen über ein Skript, das Frames publisht und `poses` + `snapshot_stats()` auswertet.
  - GPU-Zahlen nur, wenn CUDA da ist; sonst explizit `cuda_available False`.
- Befehle:
  - `docker compose -f docker/docker-compose.yml run --rm dev bash /ws/docker/run-phase6.sh`
- Tests:
  - colcon: 40 passed, 1 skipped.
  - Neu: 0/1/3 Personen inkl. Scores, CUDA-Fehler ohne GPU, System-Python ohne MMPose, Worker-`close`, `destroy_node` beendet den Infer-Thread.
  - Messung Mock 640×480: ~10 FPS in/out, Infer 0.1 ms, e2e ~7 ms, 0 Drops, RSS ~183 MB.
  - Messung RTMPose CPU 640×425: Infer ~390 ms, e2e ~511 ms, Ausgabe ~2.1 FPS bei 5 FPS Anforderung, 19/40 Frames gedroppt (latest-frame-wins).
  - GPU: `cuda_available False`.
- Offene Probleme:
  - GPU-Speicher pro Node hier nicht messbar. Skript ist vorbereitet.

---

## Phase 7 — Deployment am Prüfstand

**Status:** gesperrt bis Phase 6 fertig  
Hängt von Nils ab: Docker-Image, Topic-Namen, Netzwerk, Schlüssel.

### Todos

- [ ] Image auf der x86-Workstation bauen
- [ ] Verbindung zum bestehenden ROS-Netzwerk
- [ ] Echte Topic-Namen und QoS klären
- [ ] Einen Azure-Kinect-RGB-Stream anschließen
- [ ] Kurze Rosbag-Aufnahme für reproduzierbare Tests
- [ ] Mehrere Kameras mit mehreren Node-Instanzen
- [ ] Performance dokumentieren
- [ ] Danach erst Jetson-Orin/ARM bewerten

### Kurzstatus nach Abschluss

- Geänderte Dateien:
- Entscheidungen:
- Befehle:
- Tests:
- Offene Probleme:

---

## Nicht in der ersten Version

Architektur darf das später zulassen, jetzt **nicht** implementieren:

- [ ] Tiefenbilder / 3D-Punkte aus Kinect
- [ ] 2D-Keypoints nach 3D umrechnen
- [ ] RTMPose3D als Node
- [ ] Kamerakalibrierung und Referenzierung (Kameras, Roboter, MoCap)
- [ ] TF zwischen Kameras
- [ ] Sync mehrerer Videostreams
- [ ] Fusion mehrerer Pose Estimates (Variante 2 bzw. Merge nach Variante 1)
- [ ] Kamerübergreifendes Personentracking
- [ ] TensorRT-Optimierung
- [ ] Jetson-Deployment

---

## Spätere Erweiterungen (nach erster Version)

Nur zur Einordnung, nicht jetzt umsetzen:

1. Kalibrierung und Referenzierung der Kameras zueinander, zum Roboter und zum Motion-Capture-System
2. RTMPose-3D als zusätzliche Node
3. Mergen mehrerer Pose Estimates zu einem Estimate

---

## Offene Punkte

Nicht raten. Sobald etwas geklärt ist, hier die Entscheidung eintragen und die Checkbox setzen.

- [x] Welches ROS-Message-Format am Prüfstand erwartet wird — dort nichts vorgegeben; eigenes `human_pose_msgs` mit variablem `Keypoint2D[]`
- [x] Ob `vision_msgs` dort bereits genutzt wird — unbekannt; hier nicht verwendet (eigene BoundingBox2D, Top-Left in Pixeln)
- [ ] Welches Docker-Image vom Prüfstand als Basis dient (vorerst eigenes Jazzy-Image)
- [ ] Konkrete Topic-Namen und `frame_id`s der Azure Kinects / Webcam
- [ ] QoS der Kamerapublisher
- [x] Welches RTMPose-Modell (`human` als vorläufige Annahme)
- [x] Lizenzlage MMPose / RTMPose / Checkpoints für kommerzielle Verwertung
- [x] Ob GPU auf der Workstation für lokale Tests verfügbar ist
- [ ] Domain-ID / ROS-Netzwerk am Prüfstand

---

## Vorläufige Annahmen

Solange nichts anderes feststeht:

- RTMPose über MMPose-Standardkonfiguration `human`
- Modell, Checkpoint und Detektor müssen austauschbar bleiben
- Keine feste Echtzeitanforderung; FPS und Latenz werden gemessen
- Eigenes Message-Paket `human_pose_msgs`
- Lokale Tests mit Webcam, Video oder ROS-Bag
- Variante 1 (eine Node pro Kamera) für Multi-Kamera
