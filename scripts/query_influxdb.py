import os, sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv()

client = InfluxDBClient(
    url=os.getenv('INFLUXDB_URL'),
    token=os.getenv('INFLUXDB_TOKEN'),
    org=os.getenv('INFLUXDB_ORG')
)
q = client.query_api()
BUCKET = os.getenv('INFLUXDB_BUCKET', 'pacte')

print("=" * 60)
print("REQUÊTES INFLUXDB CLOUD — PACTE")
print("=" * 60)

# ─── 1. Alertes CRITIQUE par scénario ───────────────────────
query1 = f'''
from(bucket: "{BUCKET}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "critical_alerts")
  |> filter(fn: (r) => r._field == "anomaly_score")
  |> group(columns: ["scenario"])
  |> count()
'''
tables1 = q.query(query1)
print("\n1. ALERTES CRITIQUE PAR SCÉNARIO")
print("-" * 40)
scenario_counts = {}
for table in tables1:
    for record in table.records:
        sc = record.values.get('scenario', 'inconnu')
        n  = record.get_value()
        scenario_counts[sc] = n
        print(f"  {sc:30s} : {n:6,} alertes")

# ─── 2. Distribution risk_level dans sensor_events ──────────
query2 = f'''
from(bucket: "{BUCKET}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "sensor_events")
  |> filter(fn: (r) => r._field == "anomaly_score")
  |> group(columns: ["risk_level"])
  |> count()
'''
tables2 = q.query(query2)
print("\n2. DISTRIBUTION NIVEAUX DE RISQUE (sensor_events)")
print("-" * 40)
risk_counts = {}
for table in tables2:
    for record in table.records:
        lvl = record.values.get('risk_level', 'inconnu')
        n   = record.get_value()
        risk_counts[lvl] = n
        print(f"  {lvl:10s} : {n:6,} points")

# ─── 3. Score moyen par scénario ────────────────────────────
query3 = f'''
from(bucket: "{BUCKET}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "critical_alerts")
  |> filter(fn: (r) => r._field == "anomaly_score")
  |> group(columns: ["scenario"])
  |> mean()
'''
tables3 = q.query(query3)
print("\n3. SCORE MOYEN PAR SCÉNARIO (critical_alerts)")
print("-" * 40)
score_means = {}
for table in tables3:
    for record in table.records:
        sc  = record.values.get('scenario', 'inconnu')
        val = record.get_value()
        if val is not None:
            score_means[sc] = round(val, 4)
            print(f"  {sc:30s} : {val:.4f}")

client.close()

# ─── VISUALISATION ───────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle(
    "PACTE — Données InfluxDB Cloud\nBucket: pacte | Org: d37b21d96b65c89c",
    fontsize=13, fontweight='bold'
)

color_map = {'NORMAL': '#2ecc71', 'SUSPECT': '#f39c12', 'CRITIQUE': '#e74c3c'}

# Panel 1 : Alertes CRITIQUE par scénario
ax1 = axes[0]
if scenario_counts:
    sc_names = list(scenario_counts.keys())
    sc_vals  = list(scenario_counts.values())
    colors   = ['#e74c3c' if s != 'normal' else '#95a5a6' for s in sc_names]
    bars = ax1.barh(sc_names, sc_vals, color=colors, edgecolor='white')
    ax1.set_title("Alertes CRITIQUE par scénario\n(critical_alerts)", fontweight='bold')
    ax1.set_xlabel("Nombre d'alertes")
    for bar, val in zip(bars, sc_vals):
        ax1.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
                 f'{val:,}', va='center', fontsize=8)
    ax1.grid(axis='x', alpha=0.3)

# Panel 2 : Distribution risk_level
ax2 = axes[1]
if risk_counts:
    levels = ['NORMAL', 'SUSPECT', 'CRITIQUE']
    vals   = [risk_counts.get(l, 0) for l in levels]
    cols   = [color_map.get(l, '#95a5a6') for l in levels]
    bars2  = ax2.bar(levels, vals, color=cols, edgecolor='white', linewidth=1.5)
    ax2.set_title("Distribution niveaux de risque\n(sensor_events)", fontweight='bold')
    ax2.set_ylabel("Nombre de points")
    total = sum(vals)
    for bar, val in zip(bars2, vals):
        if val > 0:
            ax2.text(bar.get_x() + bar.get_width()/2,
                     bar.get_height() + total * 0.01,
                     f'{val:,}\n({100*val/total:.1f}%)',
                     ha='center', fontsize=8)
    ax2.grid(axis='y', alpha=0.3)

# Panel 3 : Score moyen par scénario
ax3 = axes[2]
if score_means:
    sc2     = [s for s in score_means if s != 'normal']
    vals2   = [score_means[s] for s in sc2]
    cols3   = ['#e74c3c'] * len(sc2)
    ax3.barh(sc2, vals2, color=cols3, edgecolor='white')
    ax3.axvline(0.0991, color='navy', linestyle='--', linewidth=1.5, label='P5 (seuil CRITIQUE)')
    ax3.axvline(0.1277, color='orange', linestyle=':', linewidth=1.5, label='P10 (seuil SUSPECT)')
    ax3.set_title("Anomaly score moyen\npar scénario CRITIQUE", fontweight='bold')
    ax3.set_xlabel("anomaly_score moyen")
    ax3.legend(fontsize=8)
    ax3.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('influxdb_dashboard.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nGraphique sauvegardé : influxdb_dashboard.png")
print(f"\nDashboard web : https://us-east-1-1.aws.cloud2.influxdata.com/orgs/d37b21d96b65c89c/dashboards")
