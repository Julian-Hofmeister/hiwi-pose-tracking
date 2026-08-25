# Zeiterfassung (Phasen 1–6)

Schätzung des **theoretischen Solo-Aufwands ohne KI** für die bisher umgesetzte erste Version (ROS2-Jazzy-Node mit RTMPose, inkl. Docker, Tests, Doku). Phase 7 (Prüfstand) ist nicht enthalten.

Annahme: HiWi mit Programmier- und etwas ROS-Erfahrung, aber ohne fertiges MMPose/RTMPose-Setup auf Python 3.12. Enthalten sind Einarbeitung, Irrwege (vor allem Docker/MMPose) und Tests — nicht nur „Code tippen“.

**Excel:** Tabelle unten kopieren oder `zeiterfassung_phasen.csv` in Excel öffnen (Trennzeichen: Semikolon). Spalten `Datum_von` / `Datum_bis` / `Stunden_gebucht` selbst eintragen.

| Phase | Arbeitspaket | Stunden (Empfehlung) | Spanne | Was in der Zeit steckt |
|-------|----------------|----------------------|--------|-------------------------|
| 0 | Einarbeitung, Briefing, Plan, Repo | 6 | 4–8 | Aufgabe von Nils, Umsetzungsplan, GitHub, grobe Architektur |
| 1 | Docker + ROS-Grundgerüst | 16 | 12–22 | ROS2 Jazzy Image, WSL/Docker Desktop, Colcon-Paket, Image-Passthrough, Mock-Kamera, Launch, Tests, QoS |
| 2 | RTMPose außerhalb von ROS | 24 | 18–32 | Versionen pinnen (PyTorch/MMCV/MMPose auf 3.12), Docker-Install, Estimator-API, Mock, Lizenzen, Testbild |
| 3 | Node-Integration | 20 | 16–26 | ROS und MMPose getrennt (Subprocess), latest-frame-wins, Debug-Overlay, Fehlerfälle, Tests |
| 4 | ROS-Messages | 12 | 8–16 | Recherche bestehender Msgs, Paket `human_pose_msgs`, variable Keypoints, Converter, Header, leeres Array |
| 5 | Parallelbetrieb | 10 | 8–14 | Eine Instanz pro Kamera, gemeinsame YAML, Multi-Launch, keine vermischten Topics, Tests |
| 6 | Tests, Messung, README | 12 | 8–16 | Testlücken, Shutdown, Laufzeitmessung CPU, Dokumentation |
| **1–6** | **Summe erste Version** | **100** | **74–134** | ohne Phase 7, ohne Meetings außer der Einarbeitung in Phase 0 |

Phase 2 ist absichtlich der größte Block: der Python-3.12-/MMPose-Stack (setuptools, MMCV-Wheels, MMDet-Pin) wäre ohne fertiges Rezept der zeitraubendste Teil.

---

## Excel-Spalten (Vorschlag)

| Phase | Arbeitspaket | Stunden_ohne_KI | Datum_von | Datum_bis | Stunden_gebucht | Taetigkeit |
|-------|----------------|-----------------|-----------|-----------|-----------------|------------|
| 0 | Einarbeitung und Planung | 6 |  |  |  | Briefing, Umsetzungsplan, Repository |
| 1 | Docker ROS2 und Passthrough-Node | 16 |  |  |  | Entwicklungsumgebung, Colcon, Image-Node, Mock-Kamera |
| 2 | RTMPose Estimator und Docker-Stack | 24 |  |  |  | MMPose/RTMPose CPU, Schnittstelle, Lizenzen |
| 3 | Integration Kamera zu Pose-Overlay | 20 |  |  |  | Node, Worker-Prozess, Visualisierung |
| 4 | ROS-Message-Format | 12 |  |  |  | human_pose_msgs, Converter, variable Keypoints |
| 5 | Multi-Kamera Parallelbetrieb | 10 |  |  |  | Namespaces, Launch, Isolation |
| 6 | Tests Messung Dokumentation | 12 |  |  |  | pytest, Laufzeit, README |

`Stunden_gebucht` = was du in der HiWi-Liste einträgst. Wenn die Liste **tatsächliche** Anwesenheit will, dort die realen Stunden einsetzen und diese Datei nur als Aufschlüsselung nach Phasen nutzen. Wenn der Aufwand der Arbeit bewertet werden soll, sind die 100 h die Größe, an der du dich orientieren kannst.

---

## Optional: Verteilung bis Zieltermin

Ziel laut Plan: Mitte/Ende September 2026. Bei **8 h/Woche** sind 100 h etwa **12–13 Wochen**; bei **10 h/Woche** etwa **10 Wochen**. Phase 7 extra einplanen (Anbindung Kinect/Prüfstand), sobald Nils Topics und Image nennt — grob **8–16 h**, je nach Netzwerk und Hardware.

Nicht in den 100 h: Meetings, Wartezeit auf Zugänge, Jetson/TensorRT, 3D/Fusion.
