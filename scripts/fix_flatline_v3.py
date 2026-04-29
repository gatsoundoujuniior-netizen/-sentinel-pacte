import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')
src = ''.join(cells[idx].get('source', [])) if isinstance(cells[idx].get('source',[]), list) else cells[idx].get('source','')

# Composite upgrade: 4 (déjà fait mais on s'assure)
src = src.replace(
    'if row["nb_sensors_alert"] >= 3:',
    'if row["nb_sensors_alert"] >= 4:'
)

# Remplacer toute la section flatline (étape 6)
# On cherche le début et la fin du bloc
start_marker = "    # =========================================================================\n    # ÉTAPE 6 : RÈGLE MÉTIER — Panne capteur / Flatline"
end_marker = "        print(\"Colonnes std50 absentes — règle flatline ignorée (relancer Section 7 d'abord)\")"

start_pos = src.find(start_marker)
end_pos   = src.find(end_marker) + len(end_marker)

assert start_pos != -1, "Début bloc étape 6 introuvable"
assert end_pos   > start_pos, "Fin bloc étape 6 introuvable"

new_step6 = '''    # =========================================================================
    # ÉTAPE 6 : RÈGLE MÉTIER — Panne capteur / Flatline (CEI 61511 §11.2.4)
    # =========================================================================
    # L'IF considère un capteur en panne (valeur constante) comme "normal"
    # car les valeurs flatline sont très groupées → faible isolation score.
    # Approche consécutive : >= 20 lectures identiques (diff ≈ 0) = capteur bloqué
    # Plus fiable que std50 seul (données naturellement stables = faux positifs)
    # =========================================================================

    FLAT_MIN_CONSEC = 20   # 20 lectures identiques consécutives → panne (CEI 61511 §11.2.4)
    FLAT_DIFF_THR   = 1e-6 # précision flottante — valeur vraiment figée

    diff_sensors = ['co', 'humidity', 'lpg', 'smoke', 'temp']
    diff_cols    = [f'{s}_diff' for s in diff_sensors if f'{s}_diff' in df_scaled.columns]

    def consec_flat(series, thr=FLAT_DIFF_THR):
        is_flat = series.abs() < thr
        groups  = (is_flat != is_flat.shift()).cumsum()
        counter = is_flat.groupby(groups).cumcount() + 1
        return (counter * is_flat).values

    flatline_any = np.zeros(len(df_scaled), dtype=bool)
    for dc in diff_cols:
        consec = df_scaled.groupby('device')[dc].transform(
            lambda x: pd.Series(consec_flat(x), index=x.index)
        )
        flatline_any |= (consec >= FLAT_MIN_CONSEC).values

    if diff_cols:
        for i in np.where(flatline_any)[0]:
            risk_array[i] = 'CRITIQUE'
        df_scaled['risk_level'] = risk_array
        n_flatline = flatline_any.sum()
        print(f"Règle flatline/panne capteur (CEI §11.2.4)  : {n_flatline:,} points → CRITIQUE")
    else:
        print("Colonnes _diff absentes — règle flatline ignorée (relancer Section 7 d'abord)")'''

src = src[:start_pos] + new_step6 + src[end_pos:]

cells[idx]['source'] = src
with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("Fix v3 appliqué dans le notebook OK")
