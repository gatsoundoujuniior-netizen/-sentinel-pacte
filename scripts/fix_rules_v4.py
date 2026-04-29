import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')
src = cells[idx]['source']
if isinstance(src, list):
    src = ''.join(src)

# ─── FIX ÉTAPE 5 : motion après StandardScaler n'est plus == 1 mais > 0 ───
old5 = "        is_motion   = df_scaled['motion'].values == 1"
new5 = "        # Après StandardScaler, motion=1 original → valeur positive (pas == 1)\n        is_motion   = df_scaled['motion'].values > 0"

# ─── FIX ÉTAPE 6 : any() au lieu de all() — la panne peut ne toucher qu'1 capteur ───
old6 = "        flatline_mask = (df_scaled[std50_cols] < 0.001).all(axis=1).values"
new6 = "        # any() : 1 seul capteur en flatline suffit (panne partielle possible)\n        flatline_mask = (df_scaled[std50_cols] < 0.001).any(axis=1).values"

assert old5 in src, f"marker5 introuvable"
assert old6 in src, f"marker6 introuvable"

src = src.replace(old5, new5)
src = src.replace(old6, new6)
cells[idx]['source'] = src

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Fix v4 appliqué OK")
