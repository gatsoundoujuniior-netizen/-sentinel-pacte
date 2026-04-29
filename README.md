# SENTINEL — Système Intelligent de Détection d'Anomalies Portuaires

> Projet PACTE · 4ème année IA & Big Data · HESTIM Casablanca  
> Inspiré du Port of Rotterdam

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-black?logo=flask)](https://flask.palletsprojects.com)
[![InfluxDB](https://img.shields.io/badge/InfluxDB-Cloud-orange?logo=influxdb)](https://cloud2.influxdata.com)
[![IEC 61511](https://img.shields.io/badge/IEC%2061511-SIL%201%20%E2%9C%85-green)](docs/)
[![Recall](https://img.shields.io/badge/Recall%20moyen-96.8%25-brightgreen)]()

---

## Vue d'ensemble

**SENTINEL** est un système de détection précoce d'anomalies environnementales dans des zones logistiques portuaires, développé dans un cadre académique avec des **capteurs et scénarios simulés**. Il analyse les données de 9 capteurs (CO, LPG, fumée, température, humidité, lumière, mouvement) répartis sur 3 entrepôts via un algorithme d'apprentissage non-supervisé **Isolation Forest**, conforme à la norme de sécurité industrielle **IEC 61511 SIL 1**.

> **Note :** Les capteurs ESP32 fonctionnent en mode simulation. Les 6 scénarios d'anomalies (fuite LPG, incendie, intrusion…) sont injectés synthétiquement dans le dataset réel pour valider les performances du modèle. Les données sont rejouées depuis un dataset Kaggle IoT Telemetry (405 171 mesures) vers InfluxDB Cloud.

### Architecture

```
ESP32 (simulation) ──MQTT──► Raspberry Pi ──► Isolation Forest ──► InfluxDB Cloud
                                                                           │
                                                               Flask Dashboard ◄─ Navigateur
```

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| Détection d'anomalies | Score d'anomalie Isolation Forest par entrepôt |
| 3 niveaux de risque | NORMAL / SUSPECT / CRITIQUE avec seuils P5 et P10 |
| 6 scénarios simulés | Fuite LPG, Incendie, Intrusion, Surchauffe, Fuite chimique, Panne capteur |
| Dashboard Flask | Tableaux de bord, alertes, simulations, visualisations SVG |
| Conformité SIL 1 | Recall moyen 96.8% sur scénarios injectés — norme IEC 61511 respectée |
| RBAC | 3 rôles : Admin / Opérateur / Public |

---

## Scoring et Seuils

L'Isolation Forest produit un score entre **−1.0** et **+0.5** :

| Score | Niveau | Seuil |
|---|---|---|
| `< −0.099` | 🔴 CRITIQUE | Percentile 5 (P5) |
| `−0.099 → −0.027` | 🟡 SUSPECT | Percentile 10 (P10) |
| `> −0.027` | 🟢 NORMAL | — |

Les seuils sont calculés sur 405 184 mesures et garantissent un recall ≥ 90% (SIL 1).

---

## Stack Technique

| Couche | Technologie |
|---|---|
| Dashboard | Flask (Python) |
| Base de données | InfluxDB Cloud (TSM engine, Flux query) |
| ML | Isolation Forest — scikit-learn |
| Protocole IoT | MQTT → Raspberry Pi |
| Capteurs | ESP32 (simulation) |
| Normalisation | StandardScaler (mean=0, std=1) |

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/gatsoundoujuniior/sentinel-pacte.git
cd sentinel-pacte
```

### 2. Environnement virtuel

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configuration InfluxDB

```bash
cp .env.example .env
# Éditez .env avec vos propres credentials InfluxDB Cloud
```

### 4. Dataset

Le dataset principal (`pacte_risk_log.csv` — 405 171 lignes, 29 MB) n'est pas inclus dans le dépôt.

**Téléchargement :** [Kaggle — IoT Telemetry Dataset](https://www.kaggle.com/datasets/garystafford/environmental-sensor-telemetry-data)

Placez le fichier dans `data/pacte_risk_log.csv`.

### 5. Lancer le dashboard

```bash
python app.py
# Ouvrez http://localhost:5000
```

---

## Structure du projet

```
sentinel-pacte/
├── app.py                          # Backend Flask (routes + API InfluxDB)
├── requirements.txt                # Dépendances Python
├── .env.example                    # Template de configuration
│
├── notebooks/
│   └── pacte.ipynb                 # Notebook ML — entraînement + validation SIL 1
│
├── scripts/
│   ├── query_influxdb.py           # Requêtes Flux vers InfluxDB
│   ├── validate_scoring.py         # Validation recall par scénario
│   └── ...                         # Scripts d'injection et correction notebook
│
├── design_app/
│   └── sentinel_full_rbac_port.html # Dashboard complet (RBAC, visualisations)
│
├── assets/                         # Diagrammes SVG
│   ├── architecture_sentinel.svg
│   ├── software_architecture.svg
│   ├── pipeline_donnees.svg
│   ├── scoring_seuils.svg
│   └── distribution_risques.svg
│
├── data/
│   └── pacte_alertes_critiques.csv # Alertes critiques exportées (57 213 points)
│
└── docs/
    ├── context.md                  # Contexte technique du projet
    ├── SENTINEL_Documentation_Technique.html
    ├── Livrables 1.pdf             # Livrable académique — Phase 1
    ├── Livrable 2.pdf              # Livrable académique — Phase 2
    ├── PACTE_Architecture_UML.pdf
    └── PACTE_Sequence_Activite_UML.pdf
```

---

## Conformité Normative

| Norme | Niveau appliqué | Application dans SENTINEL |
|---|---|---|
| **IEC 61511** | SIL 1 | Seuils P5/P10, recall ≥ 90% sur 6 scénarios |
| **Code ISPS 2003** | Référence | Contexte sécurité portuaire / cas d'usage |
| **Directive ATEX 2014/34/UE** | Référence | Scénarios LPG, fuite chimique, zones explosibles |
| **UML 2.5** | Conformité | Diagrammes classes, séquences, activités |

### Recall par scénario (IEC 61511 SIL 1 — seuil ≥ 90%)

| Scénario | Recall | Statut |
|---|---|---|
| Fuite LPG | 100.0% | ✅ |
| Intrusion nocturne | 100.0% | ✅ |
| Incendie entrepôt | 97.2% | ✅ |
| Fuite chimique lente | 95.8% | ✅ |
| Panne capteur | 91.0% | ✅ |
| **Moyenne** | **96.8%** | **✅ SIL 1 atteint** |

---

## Dataset

- **Source :** [IoT Telemetry Dataset — Kaggle](https://www.kaggle.com/datasets/garystafford/environmental-sensor-telemetry-data) · 3 devices (entrepôts A, B, C)
- **Volume :** 405 171 lignes · 9 capteurs
- **Distribution après injection des scénarios :** NORMAL 73.3% · CRITIQUE 19.6% · SUSPECT 7.1%
- **Anomalies :** 6 scénarios synthétiques injectés (`notebooks/pacte.ipynb` — cellule `89b8994f`)
- **Paramètres ML :** `n_estimators=100`, `contamination=0.1`
- **Replay InfluxDB :** 9 953 points sensor_events · 57 213 alertes critiques (avril 2026)

---

## Auteur

**Junior Stevy Gatsoundou**  
4ème année IA & Big Data — HESTIM Casablanca  
[gatsoundoujuniior@gmail.com](mailto:gatsoundoujuniior@gmail.com)

---

*Avril 2026 · Flask + InfluxDB Cloud + Isolation Forest*
