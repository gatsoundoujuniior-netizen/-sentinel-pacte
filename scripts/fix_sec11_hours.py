import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')

old = """    if 'motion' in df_scaled.columns:
        # Reconstruire l'heure depuis le df original (df conserve ts)
        if 'ts' in df.columns:
            hours = pd.to_datetime(df['ts'], unit='s').dt.hour
        elif 'ts' in df_scaled.columns:
            hours = pd.to_datetime(df_scaled['ts'], unit='s').dt.hour
        else:
            # Fallback : heure simulée depuis l'index (dataset couvre ~24h)
            hours = (df_scaled.index % 86400) // 3600

        is_night  = hours.isin(range(22, 24)).values | hours.isin(range(0, 7)).values
        is_motion = df_scaled['motion'].values == 1"""

new = """    if 'motion' in df_scaled.columns:
        # Reconstruire l'heure depuis le df original (df conserve ts)
        if 'ts' in df.columns and len(df) == len(df_scaled):
            hours = pd.to_datetime(df['ts'].values, unit='s').astype('datetime64[h]').astype(int) % 24
        elif 'ts' in df_scaled.columns:
            hours = pd.to_datetime(df_scaled['ts'].values, unit='s').astype('datetime64[h]').astype(int) % 24
        else:
            # Fallback : heure simulée depuis l'index
            hours = (np.arange(len(df_scaled)) % 86400) // 3600

        # Utiliser comparaisons numpy (fonctionne sur ndarray ET Series)
        hours = np.array(hours)
        is_night  = (hours >= 22) | (hours < 7)
        is_motion = df_scaled['motion'].values == 1"""

assert old in cells[idx]['source'], "Bloc introuvable dans la cellule !"
cells[idx]['source'] = cells[idx]['source'].replace(old, new)

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Fix hours appliqué OK")
