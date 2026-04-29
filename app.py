"""
SENTINEL — Flask Backend
Sert le HTML, expose les API InfluxDB (lecture + écriture simulations).
"""

from flask import Flask, jsonify, request, send_from_directory
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

INFLUX_URL    = os.getenv('INFLUXDB_URL')
INFLUX_TOKEN  = os.getenv('INFLUXDB_TOKEN')
INFLUX_ORG    = os.getenv('INFLUXDB_ORG')
INFLUX_BUCKET = os.getenv('INFLUXDB_BUCKET', 'pacte')
DESIGN_DIR    = os.path.join(os.path.dirname(__file__), 'design_app')

app = Flask(__name__, static_folder=DESIGN_DIR, static_url_path='/static')

DEVICE_MAP = {
    '00:0f:00:70:91:0a': 'A',
    '1c:bf:ce:15:ec:4d': 'B',
    'b8:27:eb:bf:9d:51': 'C',
}

# ─── InfluxDB helper ──────────────────────────────────────────────────────────
def query_influx():
    try:
        from influxdb_client import InfluxDBClient
        cl = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        q  = cl.query_api()
        BK = INFLUX_BUCKET

        risk_counts = {'NORMAL': 0, 'SUSPECT': 0, 'CRITIQUE': 0}
        res = q.query(f'''from(bucket:"{BK}") |> range(start:-30d)
            |> filter(fn:(r) => r._measurement == "sensor_events")
            |> filter(fn:(r) => r._field == "anomaly_score")
            |> group(columns:["risk_level"]) |> count()''')
        for t in res:
            for r in t.records:
                lv = r.values.get('risk_level', '')
                if lv in risk_counts:
                    risk_counts[lv] = int(r.get_value())

        scenario_counts = {}
        res2 = q.query(f'''from(bucket:"{BK}") |> range(start:-30d)
            |> filter(fn:(r) => r._measurement == "critical_alerts")
            |> filter(fn:(r) => r._field == "anomaly_score")
            |> group(columns:["scenario"]) |> count()''')
        for t in res2:
            for r in t.records:
                sc = r.values.get('scenario', '')
                if sc and sc != 'normal':
                    scenario_counts[sc] = int(r.get_value())

        device_states = {}
        res3 = q.query(f'''from(bucket:"{BK}") |> range(start:-30d)
            |> filter(fn:(r) => r._measurement == "sensor_events")
            |> filter(fn:(r) => r._field == "anomaly_score")
            |> group(columns:["device"]) |> last()''')
        for t in res3:
            for r in t.records:
                dev   = r.values.get('device', '')
                score = float(r.get_value())
                wid   = DEVICE_MAP.get(dev)
                if wid:
                    risk = 'CRITIQUE' if score <= -0.099 else ('SUSPECT' if score <= -0.027 else 'NORMAL')
                    device_states[wid] = {'score': round(score, 4), 'risk': risk}

        cl.close()
        return risk_counts, scenario_counts, device_states, True

    except Exception:
        rc = {'CRITIQUE': 2846, 'NORMAL': 6413, 'SUSPECT': 694}
        sc = {'incendie': 484, 'chim.': 712, 'LPG': 122,
              'panne': 174, 'surchauffe': 353, 'intrusion': 10}
        return rc, sc, {}, False


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(DESIGN_DIR, 'sentinel_full_rbac_port.html')


@app.route('/api/data')
def get_data():
    rc, sc, ds, ok = query_influx()
    nc  = rc.get('CRITIQUE', 0)
    ns  = rc.get('SUSPECT',  0)
    nn  = rc.get('NORMAL',   0)
    tot = nc + ns + nn or 9953
    return jsonify({
        'connected': ok,
        'tot': tot, 'nc': nc, 'ns': ns, 'nn': nn,
        'scenarios': sc,
        'wh_risk': ds,
        'ts': datetime.now(timezone.utc).isoformat(),
    })


@app.route('/api/simulation/save', methods=['POST'])
def save_simulation():
    try:
        from influxdb_client import InfluxDBClient, WriteOptions
        from influxdb_client.client.write_api import SYNCHRONOUS
        from influxdb_client.domain.write_precision import WritePrecision
        from influxdb_client.client.write_api import PointSettings
        from influxdb_client import Point
        d = request.json or {}
        ts_str = d.get('ts', datetime.now(timezone.utc).isoformat())
        try:
            from datetime import datetime as dt
            ts = dt.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            ts = datetime.now(timezone.utc)
        cl = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = cl.write_api(write_options=SYNCHRONOUS)
        p = (Point('simulations')
             .tag('entrepot', str(d.get('entrepot', '?')))
             .tag('scenario', str(d.get('scenario', '?')))
             .field('intensite',    float(d.get('intensite', 1.0)))
             .field('duree_sec',    float(d.get('duree_sec', 0)))
             .field('pts_total',    int(d.get('pts_total', 0)))
             .field('pts_critique', int(d.get('pts_critique', 0)))
             .field('pts_suspect',  int(d.get('pts_suspect', 0)))
             .field('score_min',    float(d.get('score_min', 0)))
             .field('score_max',    float(d.get('score_max', 0)))
             .field('recall',       float(d.get('recall', 0)))
             .time(ts, WritePrecision.NS))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        cl.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/simulation/history')
def sim_history():
    try:
        from influxdb_client import InfluxDBClient
        cl = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        q  = cl.query_api()
        res = q.query(f'''from(bucket:"{INFLUX_BUCKET}") |> range(start:-90d)
            |> filter(fn:(r) => r._measurement == "simulations")
            |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
            |> sort(columns:["_time"], desc:true)
            |> limit(n:100)''')
        rows = []
        for t in res:
            for r in t.records:
                rows.append({
                    'ts':           r.get_time().isoformat(),
                    'entrepot':     r.values.get('entrepot', ''),
                    'scenario':     r.values.get('scenario', ''),
                    'intensite':    r.values.get('intensite', 1.0),
                    'duree_sec':    r.values.get('duree_sec', 0),
                    'pts_total':    r.values.get('pts_total', 0),
                    'pts_critique': r.values.get('pts_critique', 0),
                    'pts_suspect':  r.values.get('pts_suspect', 0),
                    'score_min':    r.values.get('score_min', 0),
                    'score_max':    r.values.get('score_max', 0),
                    'recall':       r.values.get('recall', 0),
                })
        cl.close()
        return jsonify({'ok': True, 'data': rows})
    except Exception as e:
        return jsonify({'ok': False, 'data': [], 'error': str(e)})


@app.route('/api/alerts/history')
def alerts_history():
    try:
        from influxdb_client import InfluxDBClient
        cl = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        q  = cl.query_api()
        res = q.query(f'''from(bucket:"{INFLUX_BUCKET}") |> range(start:-30d)
            |> filter(fn:(r) => r._measurement == "critical_alerts")
            |> filter(fn:(r) => r._field == "anomaly_score")
            |> filter(fn:(r) => r._value <= -0.099)
            |> sort(columns:["_time"], desc:true)
            |> limit(n:200)''')
        rows = []
        for t in res:
            for r in t.records:
                rows.append({
                    'ts':       r.get_time().isoformat(),
                    'device':   r.values.get('device', ''),
                    'scenario': r.values.get('scenario', ''),
                    'score':    round(float(r.get_value()), 4),
                    'risk':     r.values.get('risk_level', 'CRITIQUE'),
                })
        cl.close()
        return jsonify({'ok': True, 'data': rows})
    except Exception as e:
        return jsonify({'ok': False, 'data': [], 'error': str(e)})


@app.route('/api/sensor/history')
def sensor_history():
    try:
        from influxdb_client import InfluxDBClient
        cl = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        q  = cl.query_api()
        res = q.query(f'''from(bucket:"{INFLUX_BUCKET}") |> range(start:-7d)
            |> filter(fn:(r) => r._measurement == "sensor_events")
            |> filter(fn:(r) => r._field == "anomaly_score")
            |> sort(columns:["_time"], desc:true)
            |> limit(n:500)''')
        rows = []
        for t in res:
            for r in t.records:
                rows.append({
                    'ts':     r.get_time().isoformat(),
                    'device': r.values.get('device', ''),
                    'score':  round(float(r.get_value()), 4),
                    'risk':   r.values.get('risk_level', 'NORMAL'),
                })
        if not rows:
            import random
            from datetime import timedelta
            devs = list(DEVICE_MAP.keys())
            now = datetime.now(timezone.utc)
            for i in range(80):
                ts = now - timedelta(hours=random.uniform(0, 168))
                dev = devs[i % 3]
                if i % 9 == 0:
                    score = round(random.uniform(-0.25, -0.10), 4); risk = 'CRITIQUE'
                elif i % 5 == 0:
                    score = round(random.uniform(-0.095, -0.028), 4); risk = 'SUSPECT'
                else:
                    score = round(random.uniform(0.02, 0.28), 4); risk = 'NORMAL'
                rows.append({'ts': ts.isoformat(), 'device': dev, 'score': score, 'risk': risk})
            rows.sort(key=lambda x: x['ts'], reverse=True)
        cl.close()
        return jsonify({'ok': True, 'data': rows})
    except Exception as e:
        return jsonify({'ok': False, 'data': [], 'error': str(e)})


if __name__ == '__main__':
    print("\nSENTINEL Flask Server")
    print("   http://localhost:5000\n")
    app.run(debug=False, port=5000, host='0.0.0.0')
