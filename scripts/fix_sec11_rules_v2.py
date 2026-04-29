import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-code')

# ─── FIX ÉTAPE 5 : Intrusion — utiliser scénario simulé car timestamps pas nocturnes ───
old_step5 = """    if 'motion' in df_scaled.columns:
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
        is_motion = df_scaled['motion'].values == 1

        intrusion_mask = is_night & is_motion

        # Appliquer : NORMAL → SUSPECT si intrusion nocturne
        for i in np.where(intrusion_mask)[0]:
            if risk_array[i] == 'NORMAL':
                risk_array[i] = 'SUSPECT'

        df_scaled['risk_level'] = risk_array
        n_intrusion = intrusion_mask.sum()
        print(f"Règle intrusion nocturne (ISPS §16.1) : {n_intrusion:,} points reclassifiés")
    else:
        print("Colonne 'motion' absente — règle intrusion ignorée")"""

new_step5 = """    if 'motion' in df_scaled.columns:
        # Règle intrusion : motion=1 isolé (sans anomalie chimique simultanée)
        # → signal typique d'une intrusion physique sans incendie/fuite associée
        # Note : les timestamps du dataset de collecte ne couvrent pas d'heures
        # nocturnes réelles. En production, la condition heure (22h-6h) s'ajouterait.
        # Ici on détecte motion=1 avec 0 capteur chimique en alerte (ISPS §16.1).

        is_motion   = df_scaled['motion'].values == 1
        # Capteurs chimiques : co, lpg, smoke — s'ils sont tous normaux c'est une intrusion pure
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

# ─── FIX ÉTAPE 6 : Flatline — seuil plus strict, capteurs continus seulement ───
old_step6 = """    std50_cols = [c for c in df_scaled.columns if c.endswith('_std50')]

    if std50_cols:
        # Flatline si AU MOINS 1 capteur a std50 quasi nulle
        flatline_mask = (df_scaled[std50_cols] < 0.01).any(axis=1).values

        for i in np.where(flatline_mask)[0]:
            risk_array[i] = 'CRITIQUE'  # panne capteur = toujours CRITIQUE

        df_scaled['risk_level'] = risk_array
        n_flatline = flatline_mask.sum()
        print(f"Règle flatline/panne capteur (CEI §11.2.4)  : {n_flatline:,} points → CRITIQUE")
    else:
        print("Colonnes std50 absentes — règle flatline ignorée (relancer Section 7 d'abord)")"""

new_step6 = """    # Capteurs continus uniquement (exclure motion qui est binaire et naturellement flat)
    continuous = ['co', 'humidity', 'light', 'lpg', 'smoke', 'temp']
    std50_cols = [c + '_std50' for c in continuous if c + '_std50' in df_scaled.columns]

    if std50_cols:
        # Flatline = TOUS les capteurs continus ont std50 < 0.001 simultanément
        # (seuil très strict : évite de confondre faible variance normale avec panne)
        # En cas de panne capteur, std50 ≈ 0 sur TOUS les capteurs (valeur figée)
        flatline_mask = (df_scaled[std50_cols] < 0.001).all(axis=1).values

        for i in np.where(flatline_mask)[0]:
            risk_array[i] = 'CRITIQUE'

        df_scaled['risk_level'] = risk_array
        n_flatline = flatline_mask.sum()
        print(f"Règle flatline/panne capteur (CEI §11.2.4)  : {n_flatline:,} points → CRITIQUE")
        print(f"  (seuil : std50 < 0.001 sur TOUS les capteurs continus simultanément)")
    else:
        print("Colonnes std50 absentes — règle flatline ignorée (relancer Section 7 d'abord)")"""

src = cells[idx]['source']
assert old_step5 in src, "Étape 5 introuvable"
assert old_step6 in src, "Étape 6 introuvable"
src = src.replace(old_step5, new_step5)
src = src.replace(old_step6, new_step6)
cells[idx]['source'] = src

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Fix règles métier v2 appliqué OK")
