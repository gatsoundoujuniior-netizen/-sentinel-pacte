import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

print("Chargement des données...")
df = pd.read_csv("iot_telemetry_data.csv~/iot_telemetry_data.csv")

# Nettoyage
df["datetime"] = pd.to_datetime(df["ts"], unit="s")
df = df.drop(columns=["ts"])
df = df.sort_values(["device", "datetime"]).reset_index(drop=True)
df["light"]  = df["light"].astype(int)
df["motion"] = df["motion"].astype(int)
df = df[["datetime", "device", "co", "humidity", "light", "lpg", "motion", "smoke", "temp"]]
df = df.drop_duplicates().reset_index(drop=True)

for device in df["device"].unique():
    mask = (df["device"] == device) & (df["temp"] == 0.0)
    median_temp = df[(df["device"] == device) & (df["temp"] != 0.0)]["temp"].median()
    df.loc[mask, "temp"] = median_temp

# Normalisation
features = ["co", "humidity", "light", "lpg", "motion", "smoke", "temp"]
scaler = StandardScaler()
df_scaled = df.copy()
df_scaled[features] = scaler.fit_transform(df[features])

# Injection anomalies
df_scaled["is_anomaly"] = 0
df_scaled["scenario"]   = "normal"

# Scénario 1 — Incendie
start_fire = 10000
for i, idx in enumerate(df_scaled.index[start_fire:start_fire+500]):
    ratio = i / 500
    df_scaled.loc[idx, "co"]    += ratio * 8.0
    df_scaled.loc[idx, "smoke"] += ratio * 7.0
    if i > 50:
        df_scaled.loc[idx, "temp"] += (i - 50) / 100 * 3.0
    df_scaled.loc[idx, "is_anomaly"] = 1
    df_scaled.loc[idx, "scenario"]   = "incendie_entrepot"

# Scénario 2 — Fuite LPG
idx_lpg = df_scaled.sample(n=300, random_state=7).index
df_scaled.loc[idx_lpg, "lpg"]       += 8.0
df_scaled.loc[idx_lpg, "is_anomaly"] = 1
df_scaled.loc[idx_lpg, "scenario"]   = "fuite_lpg"

# Scénario 3 — Surchauffe
start_heat = 20000
for i, idx in enumerate(df_scaled.index[start_heat:start_heat+600]):
    df_scaled.loc[idx, "temp"]       += i * 0.05
    df_scaled.loc[idx, "is_anomaly"] = 1
    df_scaled.loc[idx, "scenario"]   = "surchauffe_progressive"

# Scénario 4 — Fuite chimique lente
start_gas = 30000
for i, idx in enumerate(df_scaled.index[start_gas:start_gas+800]):
    df_scaled.loc[idx, "co"]         += i * 0.015
    df_scaled.loc[idx, "lpg"]        += i * 0.008
    df_scaled.loc[idx, "is_anomaly"] = 1
    df_scaled.loc[idx, "scenario"]   = "fuite_chimique_lente"

# Scénario 5 — Intrusion nocturne
mask_nuit = df_scaled["light"] < 0
idx_intru = df_scaled[mask_nuit].sample(n=60, random_state=13).index
df_scaled.loc[idx_intru, "motion"]     += 4.0
df_scaled.loc[idx_intru, "is_anomaly"] = 1
df_scaled.loc[idx_intru, "scenario"]   = "intrusion_nocturne"

# Scénario 6 — Panne capteur flatline
flat_val   = df_scaled["humidity"].mean()
start_flat = 50000
for idx in df_scaled.index[start_flat:start_flat+200]:
    df_scaled.loc[idx, "humidity"]    = flat_val
    df_scaled.loc[idx, "is_anomaly"] = 1
    df_scaled.loc[idx, "scenario"]   = "panne_capteur"

print(f"Anomalies injectées : {df_scaled['is_anomaly'].sum():,}")

# Feature Engineering
print("Feature engineering...")
WINDOW = 50
sensors = ["co", "humidity", "lpg", "smoke", "temp"]
for sensor in sensors:
    df_scaled[f"{sensor}_mean50"] = (
        df_scaled.groupby("device")[sensor]
        .transform(lambda x: x.rolling(WINDOW, min_periods=1).mean())
    )
    df_scaled[f"{sensor}_std50"] = (
        df_scaled.groupby("device")[sensor]
        .transform(lambda x: x.rolling(WINDOW, min_periods=1).std().fillna(0))
    )
    df_scaled[f"{sensor}_diff"] = (
        df_scaled.groupby("device")[sensor]
        .transform(lambda x: x.diff().fillna(0))
    )

# Isolation Forest
feat_cols_raw = ["co", "humidity", "light", "lpg", "motion", "smoke", "temp"]
feat_cols_eng = [f"{s}_{t}" for s in sensors for t in ["mean50", "std50", "diff"]]
all_features  = feat_cols_raw + feat_cols_eng

print("Entraînement Isolation Forest...")
df_clean = df_scaled[df_scaled["scenario"] == "normal"][all_features]
contamination = round(df_scaled["is_anomaly"].mean(), 4)
model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42, n_jobs=-1)
model.fit(df_clean)
df_scaled["anomaly_score"] = model.decision_function(df_scaled[all_features])
print("IF terminé.")

# =====================================================================
# SCORING — NOUVEAUX PARAMÈTRES
# =====================================================================
print("\nCalcul scoring (nouveaux paramètres)...")

normal_scores = df_scaled.loc[df_scaled["scenario"] == "normal", "anomaly_score"]
P10 = np.percentile(normal_scores, 10)
P5  = np.percentile(normal_scores, 5)
print(f"P5={P5:.6f}  P10={P10:.6f}")

# Étape 2 : Classification initiale
def classify_score(s):
    if s <= P5:   return 'CRITIQUE'
    elif s <= P10: return 'SUSPECT'
    return 'NORMAL'
df_scaled['risk_level'] = df_scaled['anomaly_score'].apply(classify_score)

# Étape 3 : Composite upgrade >= 3 capteurs (NOUVEAU)
sensor_cols = ['co', 'humidity', 'light', 'lpg', 'smoke', 'temp']
avail = [c for c in sensor_cols if c in df_scaled.columns]
df_scaled['nb_sensors_alert'] = (df_scaled[avail].abs() > 1.5).sum(axis=1)

level_order = {'NORMAL': 0, 'SUSPECT': 1, 'CRITIQUE': 2}
level_up    = {0: 'NORMAL', 1: 'SUSPECT', 2: 'CRITIQUE'}

def composite_upgrade(row):
    if row['nb_sensors_alert'] >= 3:  # FINAL : 3 au lieu de 2
        current = level_order[row['risk_level']]
        return level_up[min(current + 1, 2)]
    return row['risk_level']
df_scaled['risk_level'] = df_scaled.apply(composite_upgrade, axis=1)

# Étape 4 : Persistance temporelle 15 (NOUVEAU)
PERSISTENCE_WINDOW = 15  # NOUVEAU : 15 au lieu de 10
df_scaled = df_scaled.reset_index(drop=True)
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

# Étape 5 : Règle intrusion
if 'motion' in df_scaled.columns:
    is_motion = df_scaled['motion'].values > 0
    chem_cols = [c for c in ['co', 'lpg', 'smoke'] if c in df_scaled.columns]
    no_chem = (df_scaled[chem_cols].abs() <= 1.5).all(axis=1).values
    intrusion_mask = is_motion & no_chem
    for i in np.where(intrusion_mask)[0]:
        if risk_array[i] == 'NORMAL':
            risk_array[i] = 'SUSPECT'
    df_scaled['risk_level'] = risk_array
    print(f"Règle intrusion : {intrusion_mask.sum():,} points motion seul → SUSPECT")

# Étape 6 : Règle flatline std50 < 0.001 (CEI 61511 §11.2.4)
# Seuil 0.001 : détecte les capteurs figés sans sur-détecter les périodes stables naturelles
# Justification : std50 < 0.001 sur capteur continu = variabilité quasi nulle sur 50 points
std50_cols = [c + '_std50' for c in ['co', 'humidity', 'lpg', 'smoke', 'temp']
              if c + '_std50' in df_scaled.columns]
if std50_cols:
    flatline_mask = (df_scaled[std50_cols] < 0.001).any(axis=1).values
    for i in np.where(flatline_mask)[0]:
        risk_array[i] = 'CRITIQUE'
    df_scaled['risk_level'] = risk_array
    print(f"Règle flatline std50<0.001 (CEI §11.2.4) : {flatline_mask.sum():,} points → CRITIQUE")

# =====================================================================
# RÉSULTATS
# =====================================================================
dist  = df_scaled['risk_level'].value_counts()
total = len(df_scaled)

print()
print("=" * 60)
print("DISTRIBUTION GLOBALE (NOUVEAUX PARAMÈTRES)")
print("=" * 60)
for level in ['NORMAL', 'SUSPECT', 'CRITIQUE']:
    n = dist.get(level, 0)
    print(f"  {level:10s} : {n:8,}  ({100*n/total:.2f}%)")

print()
print("=" * 60)
print("RECALL PAR SCÉNARIO")
print("=" * 60)
scenarios_anomaly = df_scaled[df_scaled['scenario'] != 'normal']
for sc in sorted(scenarios_anomaly['scenario'].unique()):
    sub = scenarios_anomaly[scenarios_anomaly['scenario'] == sc]
    r_s = sub['risk_level'].isin(['SUSPECT', 'CRITIQUE']).mean() * 100
    r_c = (sub['risk_level'] == 'CRITIQUE').mean() * 100
    sil = 'SIL1 OK ✓' if r_s >= 90 else ('~SIL1' if r_s >= 70 else '⚠ INSUFFISANT')
    print(f"  {sc:30s}: SUSPECT+={r_s:5.1f}%  CRITIQUE={r_c:5.1f}%  [{sil}]")

fp = df_scaled[(df_scaled['scenario'] == 'normal') & (df_scaled['risk_level'] == 'CRITIQUE')]
print()
print(f"Faux positifs CRITIQUE : {len(fp):,}  ({100*len(fp)/total:.4f}%)")
print(f"  (données normales mal classées CRITIQUE)")
