import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')

src = cells[idx]['source']
if isinstance(src, list):
    src = ''.join(src)

# ─── FIX ÉTAPE 5 : remplacer le bloc intrusion nocturne (hours-based) ───
old5_marker = "    if 'motion' in df_scaled.columns:\n        # Reconstruire l'heure depuis le df original"
new5 = """    if 'motion' in df_scaled.columns:
        # Règle intrusion : motion=1 sans alerte chimique simultanée
        # En production, on ajouterait la condition heure (22h-6h) via timestamps réels.
        # Le dataset de collecte ne couvre pas d'heures nocturnes — on détecte donc
        # motion=1 isolé (sans co/lpg/smoke en anomalie) comme signature d'intrusion pure.
        # Justification : Code ISPS §16.1 — zones d'accès restreint hors heures d'activité.

        is_motion   = df_scaled['motion'].values == 1
        chem_cols   = [c for c in ['co', 'lpg', 'smoke'] if c in df_scaled.columns]
        if chem_cols:
            no_chem_alert = (df_scaled[chem_cols].abs() <= 1.5).all(axis=1).values
        else:
            no_chem_alert = np.ones(len(df_scaled), dtype=bool)

        intrusion_mask = is_motion & no_chem_alert

        for i in np.where(intrusion_mask)[0]:
            if risk_array[i] == 'NORMAL':
                risk_array[i] = 'SUSPECT'

        df_scaled['risk_level'] = risk_array
        n_intrusion = intrusion_mask.sum()
        print(f"Règle intrusion (ISPS §16.1) : {n_intrusion:,} points motion seul → SUSPECT")
    else:
        print("Colonne 'motion' absente — règle intrusion ignorée")"""

# ─── FIX ÉTAPE 6 : seuil strict sur capteurs continus uniquement ───
old6 = "    std50_cols = [c for c in df_scaled.columns if c.endswith('_std50')]\n\n    if std50_cols:\n        # Flatline si AU MOINS 1 capteur a std50 quasi nulle\n        flatline_mask = (df_scaled[std50_cols] < 0.01).any(axis=1).values"
new6 = """    continuous = ['co', 'humidity', 'light', 'lpg', 'smoke', 'temp']
    std50_cols = [c + '_std50' for c in continuous if c + '_std50' in df_scaled.columns]

    if std50_cols:
        # Flatline = TOUS les capteurs continus ont std50 < 0.001 simultanément
        # Seuil très strict : évite de confondre faible variance normale avec panne
        # En panne capteur réelle, std50 ≈ 0 sur TOUS les capteurs (valeur figée)
        flatline_mask = (df_scaled[std50_cols] < 0.001).all(axis=1).values"""

# Apply fix 5
if old5_marker in src:
    # Find end of old block (next # === block)
    start5 = src.find(old5_marker)
    end5 = src.find("\n    # =========", start5 + 50)
    old5_block = src[start5:end5]
    src = src.replace(old5_block, new5 + "\n\n")
    print(f"Fix étape 5 appliqué (bloc de {len(old5_block)} chars)")
else:
    print("ERREUR : marker étape 5 introuvable")

# Apply fix 6
if old6 in src:
    src = src.replace(old6, new6)
    print("Fix étape 6 appliqué")
else:
    print("ERREUR : marker étape 6 introuvable")
    # Show what's there
    i6 = src.find('std50_cols = [c for c in df_scaled')
    print(f"Trouvé à {i6}: {repr(src[i6:i6+200])}")

cells[idx]['source'] = src

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Notebook sauvegardé OK")
