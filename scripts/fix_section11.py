import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')

# Fix: replace sort_values('ts') with index-based sort (ts not in df_scaled after normalization)
old = "    df_scaled = df_scaled.sort_values('ts').reset_index(drop=True)"
new = "    # ts not in df_scaled after StandardScaler — keep existing order (already chronological)\n    df_scaled = df_scaled.reset_index(drop=True)"

cells[idx]['source'] = cells[idx]['source'].replace(old, new)

if old not in cells[idx]['source'].replace(new, old):
    # verify replacement worked
    assert "sort_values('ts')" not in cells[idx]['source'], "Fix failed!"

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Fix applied OK")
