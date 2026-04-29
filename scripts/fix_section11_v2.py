import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')

old = "sample = df_scaled[df_scaled['device'] == sample_device].sort_values('ts').head(500)"
new = "sample = df_scaled[df_scaled['device'] == sample_device].head(500)"

assert old in cells[idx]['source'], "Ligne non trouvée !"
cells[idx]['source'] = cells[idx]['source'].replace(old, new)
assert "sort_values('ts')" not in cells[idx]['source'], "Fix incomplet !"

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Fix v2 appliqué OK")
