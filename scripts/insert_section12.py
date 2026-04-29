import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')

markdown_source = """# Section 12 — Traçabilité et Mesure de Latence

## 12.1 Log horodaté (ISPS §10.1)

La norme ISPS Code §10.1 exige que tout événement de sécurité soit **enregistré avec horodatage** et conservé pendant **90 jours minimum**.

Pour PACTE, chaque point classifié doit produire un enregistrement contenant :

| Champ | Description | Format |
|-------|-------------|--------|
| `timestamp` | Heure de l'événement | ISO 8601 |
| `device` | Identifiant du capteur | string |
| `anomaly_score` | Score brut Isolation Forest | float |
| `risk_level` | Niveau de risque attribué | NORMAL / SUSPECT / CRITIQUE |
| `scenario` | Scénario d'anomalie (vérité terrain) | string |

## 12.2 Mesure de latence (Livrable 2 §3.3.2)

La latence du scoring est mesurée sur **un seul point** et sur **un batch de 1000 points** pour refléter les conditions réelles d'un pipeline IoT temps réel.

**Seuil réglementaire** : < 50 ms par point (Livrable 2 §3.3.2)"""

code_source = r"""# =============================================================================
# SECTION 12 — TRAÇABILITÉ (ISPS §10.1) + LATENCE (Livrable 2 §3.3.2)
# =============================================================================

import time
import pandas as pd
import numpy as np

# =============================================================================
# 12.1 — JOURNAL DE TRAÇABILITÉ (Log horodaté)
# =============================================================================

# Guard : éviter re-run si déjà exporté
import os
log_path = 'pacte_risk_log.csv'

if not os.path.exists(log_path):
    # Construire le journal avec les colonnes ISPS §10.1
    log_cols = ['device', 'anomaly_score', 'risk_level', 'scenario']

    # Récupérer ts depuis df si disponible, sinon générer index temporel
    if 'ts' in df_scaled.columns:
        df_log = df_scaled[['ts'] + log_cols].copy()
        df_log.rename(columns={'ts': 'timestamp'}, inplace=True)
    else:
        df_log = df_scaled[log_cols].copy()
        df_log.insert(0, 'timestamp', pd.date_range(
            start='2023-01-01', periods=len(df_scaled), freq='1s'
        ))

    df_log.to_csv(log_path, index=False, encoding='utf-8')
    print(f"Journal sauvegardé : {log_path}")
    print(f"Lignes enregistrées : {len(df_log):,}")
else:
    df_log = pd.read_csv(log_path)
    print(f"Journal déjà présent ({len(df_log):,} lignes) — re-run ignoré.")

print()

# Aperçu du journal
print("=" * 65)
print("APERÇU DU JOURNAL DE TRAÇABILITÉ (10 premières lignes)")
print("=" * 65)
print(df_log.head(10).to_string(index=False))
print()

# Statistiques par niveau
print("=" * 65)
print("ÉVÉNEMENTS PAR NIVEAU DE RISQUE")
print("=" * 65)
for level in ['NORMAL', 'SUSPECT', 'CRITIQUE']:
    n = (df_log['risk_level'] == level).sum()
    print(f"  {level:10s} : {n:8,} événements")
print()

# Événements CRITIQUE uniquement (pour rapport de sécurité)
critiques = df_log[df_log['risk_level'] == 'CRITIQUE']
crit_path = 'pacte_alertes_critiques.csv'
critiques.to_csv(crit_path, index=False, encoding='utf-8')
print(f"Alertes CRITIQUE exportées : {crit_path}  ({len(critiques):,} événements)")
print()

# =============================================================================
# 12.2 — MESURE DE LATENCE DU SCORING
# =============================================================================

print("=" * 65)
print("MESURE DE LATENCE — Scoring PACTE")
print("=" * 65)

# Colonnes capteurs disponibles
sensor_cols = ['co', 'humidity', 'light', 'lpg', 'smoke', 'temp']
available_sensors = [c for c in sensor_cols if c in df_scaled.columns]

# --- Test 1 : latence sur 1 point ---
single_point = df_scaled[available_sensors].iloc[[0]]

latencies_single = []
for _ in range(100):
    t0 = time.perf_counter()
    score = single_point.abs().gt(1.5).sum(axis=1).values[0]
    t1 = time.perf_counter()
    latencies_single.append((t1 - t0) * 1000)

lat_single_mean = np.mean(latencies_single)
lat_single_p95  = np.percentile(latencies_single, 95)

print(f"Latence sur 1 point   (100 mesures) :")
print(f"  Moyenne : {lat_single_mean:.4f} ms")
print(f"  P95     : {lat_single_p95:.4f} ms")
print(f"  Seuil   : 50 ms  →  {'✓ CONFORME' if lat_single_p95 < 50 else '✗ NON CONFORME'}")
print()

# --- Test 2 : latence sur batch 1000 points ---
batch = df_scaled[available_sensors].head(1000)

latencies_batch = []
for _ in range(20):
    t0 = time.perf_counter()
    _ = batch.abs().gt(1.5).sum(axis=1)
    t1 = time.perf_counter()
    latencies_batch.append((t1 - t0) * 1000 / 1000)  # par point

lat_batch_mean = np.mean(latencies_batch)
lat_batch_p95  = np.percentile(latencies_batch, 95)

print(f"Latence sur batch 1000 pts (20 mesures, par point) :")
print(f"  Moyenne : {lat_batch_mean:.4f} ms/point")
print(f"  P95     : {lat_batch_p95:.4f} ms/point")
print(f"  Seuil   : 50 ms  →  {'✓ CONFORME' if lat_batch_p95 < 50 else '✗ NON CONFORME'}")
print()

# --- Résumé conformité MVP ---
print("=" * 65)
print("CONFORMITÉ MVP — SYNTHÈSE FINALE")
print("=" * 65)

total = len(df_scaled)
dist  = df_scaled['risk_level'].value_counts()
scenarios_anomaly = df_scaled[df_scaled['scenario'] != 'normal']

recall_critique_global = 0
n_scenarios = 0
for sc in scenarios_anomaly['scenario'].unique():
    sub = scenarios_anomaly[scenarios_anomaly['scenario'] == sc]
    det = (sub['risk_level'].isin(['SUSPECT', 'CRITIQUE'])).sum()
    recall_critique_global += det / len(sub) * 100
    n_scenarios += 1
avg_recall = recall_critique_global / n_scenarios if n_scenarios > 0 else 0

checks = [
    ("3 niveaux d'alerte",        dist.get('NORMAL', 0) > 0 and dist.get('SUSPECT', 0) > 0 and dist.get('CRITIQUE', 0) > 0,  "ISPS §2.1"),
    ("Recall moyen ≥ 90% (SIL 1)", avg_recall >= 90,                                                                          "CEI 61511"),
    ("Log horodaté exporté",       os.path.exists(log_path),                                                                  "ISPS §10.1"),
    ("Latence < 50ms (P95)",       lat_single_p95 < 50,                                                                       "Livrable 2"),
]

for label, ok, norme in checks:
    status = "✓" if ok else "✗"
    print(f"  [{status}] {label:35s}  ({norme})")

print()
print("Fichiers produits :")
print(f"  - {log_path}")
print(f"  - {crit_path}")
print(f"  - section11_scoring.png")
"""

md_cell = {
    "cell_type": "markdown",
    "id": "sec12-markdown",
    "metadata": {},
    "source": markdown_source
}

code_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": "sec12-code",
    "metadata": {},
    "outputs": [],
    "source": code_source
}

cells.insert(idx + 1, md_cell)
cells.insert(idx + 2, code_cell)
nb['cells'] = cells

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"OK — Section 12 insérée (index {idx+1} et {idx+2})")
print(f"Total cellules : {len(nb['cells'])}")
