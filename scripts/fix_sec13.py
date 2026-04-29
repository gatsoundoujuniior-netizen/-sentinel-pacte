import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec13-code')
src = cells[idx]['source']
if isinstance(src, list):
    src = ''.join(src)

# WritePrecision.SECONDS → WritePrecision.S (influxdb-client >= 1.x)
src = src.replace('WritePrecision.SECONDS', 'WritePrecision.S')

cells[idx]['source'] = src
with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Fix WritePrecision OK")
