import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')
src = ''.join(cells[idx].get('source', [])) if isinstance(cells[idx].get('source',[]), list) else cells[idx].get('source','')

# Composite: >= 3 (meilleur compromis faux positifs vs rappel)
src = src.replace(
    'if row["nb_sensors_alert"] >= 4:',
    'if row["nb_sensors_alert"] >= 3:'
)

# Remplacer l'étape 6 flatline par la version std50 < 0.001 standard
start_marker = "    # =========================================================================\n    # ÉTAPE 6 : RÈGLE MÉTIER — Panne capteur / Flatline"
end_pos_marker = "        print(\"Colonnes _diff absentes — règle flatline ignorée (relancer Section 7 d'abord)\")"

start_pos = src.find(start_marker)
end_pos   = src.find(end_pos_marker)

if start_pos == -1:
    # Try alternate marker
    start_marker = "    # =========================================================================\n    # ÉTAPE 6 : RÈGLE MÉTIER — Panne capteur / Flatline (CEI 61511 §11.2.4)"
    start_pos = src.find(start_marker)

assert start_pos != -1, f"Début étape 6 introuvable"
assert end_pos != -1, f"Fin étape 6 introuvable"
end_pos += len(end_pos_marker)

new_step6 = '''    # =========================================================================
    # ÉTAPE 6 : RÈGLE MÉTIER — Panne capteur / Flatline (CEI 61511 §11.2.4)
    # =========================================================================
    # L'IF considère un capteur en panne (valeur constante) comme "normal"
    # car les valeurs flatline sont très groupées → faible isolation score.
    # Règle : std50 < 0.001 sur au moins 1 capteur continu → CRITIQUE
    # Note : en production, watchdog hardware complémente cette détection algo
    #        (CEI 61511 §11.2.4 — SIF failure detection)
    # =========================================================================

    continuous = ['co', 'humidity', 'light', 'lpg', 'smoke', 'temp']
    std50_cols = [c + '_std50' for c in ['co', 'humidity', 'lpg', 'smoke', 'temp']
                  if c + '_std50' in df_scaled.columns]

    if std50_cols:
        flatline_mask = (df_scaled[std50_cols] < 0.001).any(axis=1).values

        for i in np.where(flatline_mask)[0]:
            risk_array[i] = 'CRITIQUE'

        df_scaled['risk_level'] = risk_array
        n_flatline = flatline_mask.sum()
        print(f"Règle flatline/panne capteur (CEI §11.2.4)  : {n_flatline:,} points → CRITIQUE")
    else:
        print("Colonnes std50 absentes — règle flatline ignorée (relancer Section 7 d'abord)")'''

src = src[:start_pos] + new_step6 + src[end_pos:]

cells[idx]['source'] = src
with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("Paramètres finaux appliqués dans le notebook :")
print("  - Composite upgrade : >= 3 capteurs")
print("  - Persistance       : 15 fenêtres")
print("  - Flatline          : std50 < 0.001 any()")
