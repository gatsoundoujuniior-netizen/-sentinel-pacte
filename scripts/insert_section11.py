import json, sys

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == '8704e623')
print(f"Cell 8704e623 found at index {idx}")

markdown_source = """# Section 11 — Système de Scoring : Classification NORMAL / SUSPECT / CRITIQUE

## 11.1 Objectif

Transformer le score brut de l'Isolation Forest (`anomaly_score`) en un niveau de risque opérationnel exploitable, conforme aux exigences réglementaires de la Section 10 :

| Niveau | Code ISPS | Directive ATEX | CEI 61511 |
|--------|-----------|----------------|-----------|
| **NORMAL** | Niveau 1 — risque minimal | Hors seuil LIE | En dessous de toute SIL |
| **SUSPECT** | Niveau 2 — risque accru | Approche du seuil | SIL 1 (Recall ≥ 90%) |
| **CRITIQUE** | Niveau 3 — imminence | Seuil ATEX atteint | SIL 2 (Recall ≥ 99%) |

## 11.2 Architecture du scoring (4 étapes)

### Étape 1 — Seuils dynamiques percentile (critère ISPS §4.1)
L'`anomaly_score` de l'Isolation Forest est **négatif pour les anomalies** (plus le score est bas, plus le point est anormal).
Les seuils sont calculés sur la distribution des données **normales uniquement** :

```
P10 = 10e percentile de anomaly_score sur données normales
P5  =  5e percentile de anomaly_score sur données normales

NORMAL   : anomaly_score > P10
SUSPECT  : P5 < anomaly_score ≤ P10
CRITIQUE : anomaly_score ≤ P5
```

### Étape 2 — Score composite multi-capteurs (corroboration ISPS §4.1)
Si **≥ 2 capteurs** d'un même device sont simultanément en anomalie (valeur normalisée > 1.5 σ), le niveau est **élevé d'un cran** :
- NORMAL → SUSPECT
- SUSPECT → CRITIQUE

### Étape 3 — Persistance temporelle (SIF CEI 61511 §3.2.71)
Si un point reste **SUSPECT pendant > 10 fenêtres consécutives**, il est automatiquement escaladé en **CRITIQUE**.
Cette règle garantit qu'une anomalie lente (fuite chimique, surchauffe progressive) ne passe pas sous le seuil de détection.

### Étape 4 — Journal de traçabilité (ISPS §10.1)
Chaque enregistrement contient : `timestamp + device + anomaly_score + risk_level + scenario`

## 11.3 Métriques de validation
- **Recall CRITIQUE** : % des scénarios critiques (incendie, fuite LPG) détectés au niveau CRITIQUE
- **Recall SUSPECT** : % des scénarios suspects (surchauffe, fuite lente, intrusion) détectés au niveau ≥ SUSPECT
- **Faux positifs CRITIQUE** : taux de points NORMAL élevés à CRITIQUE par erreur
- **Distribution globale** : répartition NORMAL / SUSPECT / CRITIQUE sur l'ensemble du dataset"""

code_source = r"""# =============================================================================
# SECTION 11 — SYSTÈME DE SCORING : NORMAL / SUSPECT / CRITIQUE
# =============================================================================
# Basé sur anomaly_score (Isolation Forest) + règles réglementaires Section 10
# Conforme : Code ISPS §4.1, Directive ATEX Art.2, CEI 61511 §3.2.71
# =============================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

# --- Guard : éviter la ré-exécution si déjà calculé ---
if 'risk_level' not in df_scaled.columns:

    # =========================================================================
    # ÉTAPE 1 : Seuils dynamiques percentile sur données normales
    # =========================================================================
    normal_scores = df_scaled.loc[df_scaled['scenario'] == 'normal', 'anomaly_score']
    P10 = np.percentile(normal_scores, 10)
    P5  = np.percentile(normal_scores, 5)

    print(f"Seuils dynamiques calculés sur {len(normal_scores):,} points normaux :")
    print(f"  P10 = {P10:.6f}  →  seuil NORMAL / SUSPECT")
    print(f"  P5  = {P5:.6f}  →  seuil SUSPECT / CRITIQUE")
    print()

    # =========================================================================
    # ÉTAPE 2 : Classification initiale par seuils
    # =========================================================================
    def classify_score(score):
        if score <= P5:
            return 'CRITIQUE'
        elif score <= P10:
            return 'SUSPECT'
        else:
            return 'NORMAL'

    df_scaled['risk_level'] = df_scaled['anomaly_score'].apply(classify_score)

    # =========================================================================
    # ÉTAPE 3 : Score composite multi-capteurs (ISPS §4.1 — corroboration)
    # =========================================================================
    # Capteurs disponibles après normalisation
    sensor_cols = ['co', 'humidity', 'light', 'lpg', 'smoke', 'temp']
    available_sensors = [c for c in sensor_cols if c in df_scaled.columns]

    # Nombre de capteurs dont la valeur normalisée dépasse 1.5 σ
    df_scaled['nb_sensors_alert'] = (
        df_scaled[available_sensors].abs() > 1.5
    ).sum(axis=1)

    # Élever d'un cran si >= 2 capteurs en alerte simultanée
    level_order = {'NORMAL': 0, 'SUSPECT': 1, 'CRITIQUE': 2}
    level_up    = {0: 'NORMAL', 1: 'SUSPECT', 2: 'CRITIQUE'}

    def composite_upgrade(row):
        if row['nb_sensors_alert'] >= 2:
            current = level_order[row['risk_level']]
            return level_up[min(current + 1, 2)]
        return row['risk_level']

    df_scaled['risk_level'] = df_scaled.apply(composite_upgrade, axis=1)

    # =========================================================================
    # ÉTAPE 4 : Persistance temporelle (CEI 61511 §3.2.71 — SIF escalade)
    # =========================================================================
    PERSISTENCE_WINDOW = 10  # fenêtres consécutives SUSPECT → CRITIQUE

    df_scaled = df_scaled.sort_values('ts').reset_index(drop=True)
    risk_array = df_scaled['risk_level'].values.copy()

    suspect_counter = 0
    for i in range(len(risk_array)):
        if risk_array[i] == 'SUSPECT':
            suspect_counter += 1
            if suspect_counter > PERSISTENCE_WINDOW:
                risk_array[i] = 'CRITIQUE'
        else:
            suspect_counter = 0

    df_scaled['risk_level'] = risk_array

    print("Classification TERMINÉE.")
    print(f"Fenêtre de persistance : {PERSISTENCE_WINDOW} points consécutifs SUSPECT → CRITIQUE")
    print()

else:
    print("risk_level déjà présent — ré-exécution ignorée.")
    normal_scores = df_scaled.loc[df_scaled['scenario'] == 'normal', 'anomaly_score']
    P10 = np.percentile(normal_scores, 10)
    P5  = np.percentile(normal_scores, 5)

# =============================================================================
# RÉSULTATS : Distribution et métriques de validation
# =============================================================================

dist  = df_scaled['risk_level'].value_counts()
total = len(df_scaled)

print("=" * 55)
print("DISTRIBUTION GLOBALE DU RISQUE")
print("=" * 55)
for level in ['NORMAL', 'SUSPECT', 'CRITIQUE']:
    n = dist.get(level, 0)
    print(f"  {level:10s} : {n:8,}  ({100*n/total:.3f}%)")
print(f"  {'TOTAL':10s} : {total:8,}")
print()

# Métriques par scénario
print("=" * 55)
print("RECALL PAR SCÉNARIO")
print("=" * 55)

scenarios_anomaly = df_scaled[df_scaled['scenario'] != 'normal'].copy()
scenario_results = []

for sc in scenarios_anomaly['scenario'].unique():
    subset = scenarios_anomaly[scenarios_anomaly['scenario'] == sc]
    total_sc = len(subset)
    det_suspect  = subset['risk_level'].isin(['SUSPECT', 'CRITIQUE']).sum()
    det_critique = (subset['risk_level'] == 'CRITIQUE').sum()
    r_suspect  = det_suspect  / total_sc * 100 if total_sc > 0 else 0
    r_critique = det_critique / total_sc * 100 if total_sc > 0 else 0
    sil = 'SIL 1 ✓' if r_suspect >= 90 else ('≈ SIL 1' if r_suspect >= 70 else '⚠ insuffisant')
    scenario_results.append({
        'Scénario': sc,
        'Total': total_sc,
        'Recall ≥ SUSPECT (%)': round(r_suspect, 1),
        'Recall CRITIQUE (%)': round(r_critique, 1),
        'CEI 61511': sil
    })

df_scoring_report = pd.DataFrame(scenario_results)
print(df_scoring_report.to_string(index=False))
print()

fp_critique = df_scaled[(df_scaled['scenario'] == 'normal') & (df_scaled['risk_level'] == 'CRITIQUE')]
print(f"Faux positifs CRITIQUE : {len(fp_critique):,}  ({100*len(fp_critique)/total:.4f}%)")

# =============================================================================
# VISUALISATION : 3 panels
# =============================================================================

color_map = {'NORMAL': '#2ecc71', 'SUSPECT': '#f39c12', 'CRITIQUE': '#e74c3c'}

fig, axes = plt.subplots(1, 3, figsize=(20, 6))
fig.suptitle(
    "Section 11 — Système de Scoring PACTE\nConformité Code ISPS · Directive ATEX · CEI 61511",
    fontsize=14, fontweight='bold'
)

# --- Panel 1 : Distribution globale ---
ax1 = axes[0]
levels = ['NORMAL', 'SUSPECT', 'CRITIQUE']
counts = [dist.get(l, 0) for l in levels]
colors = [color_map[l] for l in levels]
bars = ax1.bar(levels, counts, color=colors, edgecolor='white', linewidth=1.5)
ax1.set_title("Distribution globale des niveaux", fontweight='bold')
ax1.set_ylabel("Nombre de points")
for bar, count in zip(bars, counts):
    pct = 100 * count / total
    ax1.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() * 1.05,
             f'{count:,}\n({pct:.2f}%)',
             ha='center', va='bottom', fontsize=8)
ax1.set_yscale('log')
ax1.grid(axis='y', alpha=0.3)

# --- Panel 2 : Recall par scénario ---
ax2 = axes[1]
sc_names    = df_scoring_report['Scénario'].tolist()
r_suspects  = df_scoring_report['Recall ≥ SUSPECT (%)'].tolist()
r_critiques = df_scoring_report['Recall CRITIQUE (%)'].tolist()
x = np.arange(len(sc_names))
w = 0.35
ax2.bar(x - w/2, r_suspects,  w, label='Recall ≥ SUSPECT', color='#f39c12', edgecolor='white')
ax2.bar(x + w/2, r_critiques, w, label='Recall CRITIQUE',  color='#e74c3c', edgecolor='white')
ax2.axhline(90, color='navy',   linestyle='--', linewidth=1.5, label='SIL 1 (90%)')
ax2.axhline(99, color='purple', linestyle=':',  linewidth=1.5, label='SIL 2 (99%)')
ax2.set_title("Recall par scénario d'anomalie", fontweight='bold')
ax2.set_ylabel("Recall (%)")
ax2.set_xticks(x)
ax2.set_xticklabels([s.replace('_', '\n') for s in sc_names], rotation=30, ha='right', fontsize=8)
ax2.set_ylim(0, 115)
ax2.legend(fontsize=8)
ax2.grid(axis='y', alpha=0.3)

# --- Panel 3 : Série temporelle (1 device, 500 points) ---
ax3 = axes[2]
sample_device = df_scaled['device'].value_counts().index[0]
sample = df_scaled[df_scaled['device'] == sample_device].sort_values('ts').head(500)
level_num = {'NORMAL': 0, 'SUSPECT': 1, 'CRITIQUE': 2}
colors_ts = [color_map[l] for l in sample['risk_level']]
ax3.scatter(range(len(sample)), sample['risk_level'].map(level_num),
            c=colors_ts, s=8, alpha=0.8)
ax3.set_yticks([0, 1, 2])
ax3.set_yticklabels(['NORMAL', 'SUSPECT', 'CRITIQUE'])
ax3.set_title(f"Série temporelle — device {sample_device}\n(500 premiers points)", fontweight='bold')
ax3.set_xlabel("Index temporel")
ax3.set_ylabel("Niveau de risque")
patches = [mpatches.Patch(color=color_map[l], label=l) for l in ['NORMAL', 'SUSPECT', 'CRITIQUE']]
ax3.legend(handles=patches, fontsize=9)
ax3.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('section11_scoring.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nGraphique sauvegardé : section11_scoring.png")
"""

md_cell = {
    "cell_type": "markdown",
    "id": "sec11-markdown",
    "metadata": {},
    "source": markdown_source
}

code_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": "sec11-code",
    "metadata": {},
    "outputs": [],
    "source": code_source
}

# Insert after idx (cell 8704e623)
cells.insert(idx + 1, md_cell)
cells.insert(idx + 2, code_cell)
nb['cells'] = cells

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"OK — 2 cellules insérées à index {idx+1} et {idx+2}")
print(f"Total cellules : {len(nb['cells'])}")
