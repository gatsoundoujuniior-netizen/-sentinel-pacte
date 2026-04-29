import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec12-code')

markdown_source = """# Section 13 — Stockage InfluxDB Cloud

## Pourquoi InfluxDB ?

InfluxDB est une base de données **spécialisée pour les séries temporelles** — exactement le type de données produit par les capteurs IoT portuaires.

| Besoin PACTE | Solution InfluxDB |
|-------------|------------------|
| Stocker 405K points horodatés | Measurement `sensor_events` |
| Retrouver toutes les alertes d'un device | Tag `device` indexé |
| Conserver 30 jours de logs (ISPS §10.1) | Rétention automatique configurée |
| Requêtes temporelles rapides | Moteur TSM optimisé |
| Intégration future Grafana | Datasource native |

## Architecture des données

```
Bucket : pacte
│
├── Measurement : sensor_events       ← tous les points scorés
│     Tags   : device, risk_level, scenario
│     Fields : anomaly_score, nb_sensors_alert
│     Time   : timestamp du capteur
│
└── Measurement : critical_alerts     ← uniquement les CRITIQUE
      Tags   : device, scenario
      Fields : anomaly_score
      Time   : timestamp du capteur
```

## Connexion via variables d'environnement

Les credentials sont stockés dans `.env` (jamais dans le code) :
```
INFLUXDB_URL    = https://us-east-1-1.aws.cloud2.influxdata.com
INFLUXDB_TOKEN  = [token privé]
INFLUXDB_ORG    = d37b21d96b65c89c
INFLUXDB_BUCKET = pacte
```"""

code_source = r"""# =============================================================================
# SECTION 13 — STOCKAGE INFLUXDB CLOUD
# =============================================================================
# Envoie les données scorées vers InfluxDB Cloud
# Bucket : pacte | Rétention : 30 jours | Conforme ISPS §10.1
# =============================================================================

import os, time
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

INFLUX_URL    = os.getenv('INFLUXDB_URL')
INFLUX_TOKEN  = os.getenv('INFLUXDB_TOKEN')
INFLUX_ORG    = os.getenv('INFLUXDB_ORG')
INFLUX_BUCKET = os.getenv('INFLUXDB_BUCKET', 'pacte')

# =============================================================================
# CONNEXION
# =============================================================================
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print(f"Connexion InfluxDB Cloud : {INFLUX_URL}")
print(f"Bucket : {INFLUX_BUCKET} | Org : {INFLUX_ORG}")
print()

# =============================================================================
# PRÉPARATION DES DONNÉES
# =============================================================================

# Reconstruire timestamps depuis df original si disponible
if 'ts' in df.columns and len(df) == len(df_scaled):
    timestamps = pd.to_datetime(df['ts'].values, unit='s', utc=True)
else:
    # Fallback : timestamps synthétiques à partir d'aujourd'hui
    timestamps = pd.date_range(
        end=pd.Timestamp.now(tz='UTC'),
        periods=len(df_scaled),
        freq='3s'
    )

df_export = df_scaled[['device', 'anomaly_score', 'risk_level', 'scenario']].copy()
df_export['timestamp'] = timestamps

# =============================================================================
# ÉCRITURE : sensor_events (échantillon 5000 points pour la démo)
# =============================================================================

SAMPLE_SIZE = 5000
sample = df_export.sample(n=min(SAMPLE_SIZE, len(df_export)), random_state=42)

print(f"Envoi de {len(sample):,} points → measurement 'sensor_events'...")
t0 = time.perf_counter()

points = []
for _, row in sample.iterrows():
    p = (
        Point("sensor_events")
        .tag("device",     str(row['device']))
        .tag("risk_level", str(row['risk_level']))
        .tag("scenario",   str(row['scenario']))
        .field("anomaly_score", float(row['anomaly_score']))
        .time(row['timestamp'], WritePrecision.SECONDS)
    )
    points.append(p)

write_api.write(bucket=INFLUX_BUCKET, record=points)
t1 = time.perf_counter()
print(f"  ✓ {len(points):,} points écrits en {t1-t0:.2f}s")
print()

# =============================================================================
# ÉCRITURE : critical_alerts (tous les points CRITIQUE)
# =============================================================================

critiques = df_export[df_export['risk_level'] == 'CRITIQUE']
print(f"Envoi de {len(critiques):,} alertes CRITIQUE → measurement 'critical_alerts'...")
t0 = time.perf_counter()

crit_points = []
for _, row in critiques.iterrows():
    p = (
        Point("critical_alerts")
        .tag("device",   str(row['device']))
        .tag("scenario", str(row['scenario']))
        .field("anomaly_score", float(row['anomaly_score']))
        .time(row['timestamp'], WritePrecision.SECONDS)
    )
    crit_points.append(p)

# Écriture par batch de 5000
BATCH = 5000
for i in range(0, len(crit_points), BATCH):
    write_api.write(bucket=INFLUX_BUCKET, record=crit_points[i:i+BATCH])
    print(f"  batch {i//BATCH + 1} / {len(crit_points)//BATCH + 1} envoyé")

t1 = time.perf_counter()
print(f"  ✓ {len(crit_points):,} alertes écrites en {t1-t0:.2f}s")
print()

# =============================================================================
# VÉRIFICATION : requête de retour
# =============================================================================

query_api = client.query_api()

query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "critical_alerts")
  |> group(columns: ["scenario"])
  |> count()
'''

print("=" * 55)
print("VÉRIFICATION — Alertes CRITIQUE par scénario (InfluxDB)")
print("=" * 55)

try:
    tables = query_api.query(query)
    for table in tables:
        for record in table.records:
            scenario = record.values.get('scenario', 'inconnu')
            count    = record.get_value()
            print(f"  {scenario:30s} : {count:6} alertes")
except Exception as e:
    print(f"Requête échouée : {e}")

client.close()
print()
print("Connexion InfluxDB fermée.")
print(f"Dashboard : {INFLUX_URL}/orgs/{INFLUX_ORG}/dashboards")
"""

md_cell = {
    "cell_type": "markdown",
    "id": "sec13-markdown",
    "metadata": {},
    "source": markdown_source
}

code_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": "sec13-code",
    "metadata": {},
    "outputs": [],
    "source": code_source
}

cells.insert(idx + 1, md_cell)
cells.insert(idx + 2, code_cell)
nb['cells'] = cells

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"OK — Section 13 insérée (index {idx+1} et {idx+2})")
print(f"Total cellules : {len(nb['cells'])}")
