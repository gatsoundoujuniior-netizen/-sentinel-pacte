import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec13-code')
src = cells[idx]['source']
if isinstance(src, list):
    src = ''.join(src)

# Remplacer le bloc critical_alerts : limiter à 3000 points + délai entre batches
old = """critiques = df_export[df_export['risk_level'] == 'CRITIQUE']
print(f"Envoi de {len(critiques):,} alertes CRITIQUE → measurement 'critical_alerts'...")
t0 = time.perf_counter()

crit_points = []
for _, row in critiques.iterrows():
    p = (
        Point("critical_alerts")
        .tag("device",   str(row['device']))
        .tag("scenario", str(row['scenario']))
        .field("anomaly_score", float(row['anomaly_score']))
        .time(row['timestamp'], WritePrecision.S)
    )
    crit_points.append(p)

# Écriture par batch de 5000
BATCH = 5000
for i in range(0, len(crit_points), BATCH):
    write_api.write(bucket=INFLUX_BUCKET, record=crit_points[i:i+BATCH])
    print(f"  batch {i//BATCH + 1} / {len(crit_points)//BATCH + 1} envoyé")

t1 = time.perf_counter()
print(f"  ✓ {len(crit_points):,} alertes écrites en {t1-t0:.2f}s")"""

new = """# Plan gratuit InfluxDB : limite de débit appliquée → échantillon représentatif
CRIT_SAMPLE = 3000
critiques_all = df_export[df_export['risk_level'] == 'CRITIQUE']
critiques = critiques_all.sample(n=min(CRIT_SAMPLE, len(critiques_all)), random_state=42)
print(f"Alertes CRITIQUE totales : {len(critiques_all):,}")
print(f"Envoi échantillon : {len(critiques):,} → measurement 'critical_alerts' (plan free)")
t0 = time.perf_counter()

crit_points = []
for _, row in critiques.iterrows():
    p = (
        Point("critical_alerts")
        .tag("device",   str(row['device']))
        .tag("scenario", str(row['scenario']))
        .field("anomaly_score", float(row['anomaly_score']))
        .time(row['timestamp'], WritePrecision.S)
    )
    crit_points.append(p)

# Écriture par batch de 1000 avec délai (évite 429)
BATCH = 1000
for i in range(0, len(crit_points), BATCH):
    write_api.write(bucket=INFLUX_BUCKET, record=crit_points[i:i+BATCH])
    print(f"  batch {i//BATCH + 1} / {-(-len(crit_points)//BATCH)} envoyé")
    time.sleep(1)  # respecter le rate limit plan free

t1 = time.perf_counter()
print(f"  ✓ {len(crit_points):,} alertes écrites en {t1-t0:.1f}s")"""

assert old in src, "Bloc critical_alerts introuvable"
src = src.replace(old, new)
cells[idx]['source'] = src

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Fix rate limit OK")
