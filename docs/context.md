# CONTEXT — Projet PACTE / SENTINEL
Mis à jour : 21 avril 2026

## Identité
Junior Stevy Gatsoundou, 4e année IA & Big Data, HESTIM Casablanca
Projet : Système intelligent de détection précoce d'anomalies environnementales
en zones logistiques portuaires (inspiré Port of Rotterdam)

---

## Stack technique actuelle
| Couche | Technologie |
|---|---|
| Dashboard | Flask (Python) — remplacé Streamlit |
| Base de données | InfluxDB Cloud (gratuit, TSM engine) |
| ML | Isolation Forest (scikit-learn) |
| Protocole IoT | MQTT → Raspberry Pi |
| Capteurs | ESP32 (simulation) |

---

## Dataset
- Source : `data/pacte_risk_log.csv` — 405 171 lignes, 9 capteurs
- Capteurs : co, humidity, light, lpg, motion, smoke, temp
- 3 devices (entrepôts) : A=111 815 mes., B=105 913 mes., C=187 443 mes.
- Distribution réelle :
  - NORMAL  : 297 060 (73.3%)
  - CRITIQUE : 79 574 (19.6%)
  - SUSPECT  : 28 537 (7.1%)
- Par entrepôt :
  - A : 44.4% d'anomalies (le plus actif)
  - B : 48.0% d'anomalies (le plus dangereux 🚨)
  - C :  4.1% d'anomalies (le plus sûr ✅)

---

## 6 Scénarios d'anomalies portuaires
1. Incendie entrepôt
2. Fuite LPG
3. Surchauffe progressive
4. Fuite chimique lente
5. Intrusion nocturne
6. Panne capteur (flatline)

---

## Paramètres ML
- Isolation Forest : n_estimators=100, contamination=0.1
- Normalisation : StandardScaler (mean=0, std=1)
- Seuils calculés sur 405 184 lignes :
  - P5  = −0.099 → CRITIQUE (score < P5)
  - P10 = −0.027 → SUSPECT  (P5 ≤ score < P10)
  - NORMAL si score ≥ P10
- Norme : IEC 61511 SIL 1 — recall ≥ 90%
- Recall par scénario : Fuite LPG=100%, Intrusion=100%, Incendie=97.2%, Chimique=95.8%, Panne=91.0%

---

## InfluxDB Cloud
- Compte gratuit (30 jours de rétention)
- Organisation : pacte-sentinel / Bucket : pacte
- 3 measurements :
  - `sensor_events`    : 9 953 points (replayed avril 2026)
  - `critical_alerts`  : 57 213 points
  - `simulations`      : scénarios injectés
- Limitation : timestamps 2023 supprimés → replay avec timestamps actuels
- Flux query language

---

## Architecture fichiers
```
pacte/
├── app/                    # Flask dashboard (routes, templates, static)
├── data/
│   ├── pacte_risk_log.csv  # 405 171 lignes — dataset principal
│   └── pacte_alertes_critiques.csv
├── notebooks/
│   └── pacte.ipynb         # Notebook ML principal
├── scripts/
│   ├── query_influxdb.py
│   └── validate_scoring.py
├── docs/
│   ├── context.md          # Ce fichier
│   ├── auth_config.yaml
│   └── SENTINEL_Documentation_Technique.html
└── assets/                 # Diagrammes SVG
    ├── architecture_sentinel.svg
    ├── software_architecture.svg
    ├── pipeline_donnees.svg
    ├── scoring_seuils.svg
    └── distribution_risques.svg
```

---

## Notebook — Cellules principales
| ID | Contenu |
|---|---|
| 90e35251 | Imports + load CSV + description |
| 33b63d1c | Correlation heatmap |
| f4a96933 | Data cleaning (idempotent) |
| 5f9da0b9 | Normalisation StandardScaler |
| 89b8994f | Injection 6 scénarios |
| 93196783 | Visualisation anomalies |
| 9cd4879b | Feature Engineering (mean50, std50, diff) |
| deb21ca5 | Visualisation FE |
| 2688e27a | Isolation Forest — entraînement |
| 12c1a8de | Évaluation — recall par scénario |
| 69261fe4 | Markdown — benchmark 5 modèles |
| c04cfcdf | Benchmark code — IF vs LOF vs SVM vs EE vs Seuil fixe |
| bbf7017a | Markdown — 3 graphiques comparatifs |
| 9765d8de | Benchmark visualisation |

---

## Règles de travail
- Toujours expliquer le code AVANT d'exécuter
- Attendre validation avant chaque action
- Cellules idempotentes (guard clauses)
- Diagrams SVG : fond blanc (#f7f8fc), design propre, pas de dark theme
- Memory : `C:\Users\pc\.claude\projects\c--Users-pc-Downloads-pacte\memory\`

---

## Fichiers supprimés (obsolètes Streamlit)
- `.streamlit/config.toml`, `config.app/`, `dashboard.py`
- `design_app/sentinel_app.py`, `design_app/config.toml`
- `sentinel.db`, `iot_telemetry_data.csv~`
