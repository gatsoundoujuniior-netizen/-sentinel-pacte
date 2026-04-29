import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == '8704e623')

mvp_source = """## Synthèse MVP — Ce que PACTE doit produire concrètement

> Cette section traduit les exigences réglementaires de la Section 10 en **livrables concrets** pour le projet PACTE.
> Tout ce qui est listé ici est **strictement nécessaire** pour le MVP — rien de plus.

---

### Ce que nous devons produire

| # | Livrable | Norme source | Critère de validation |
|---|----------|-------------|----------------------|
| 1 | **3 niveaux d'alerte** : NORMAL / SUSPECT / CRITIQUE | Code ISPS §2.1.9-11 | Les 3 niveaux existent et sont distincts |
| 2 | **Recall ≥ 90%** sur les scénarios dangereux (incendie, fuite LPG) | CEI 61511 — SIL 1 | Calculé sur les scénarios injectés |
| 3 | **Alerte CRITIQUE déclenchée avant les seuils LIE** (LPG < 1,8% vol., CO < 12,5% vol.) | Directive ATEX Art. 2 | Vérifiable via les seuils P5 du scoring |
| 4 | **Log horodaté** de chaque événement : timestamp + score + niveau + scénario | Code ISPS §10.1 | Fichier CSV ou DataFrame exportable |
| 5 | **Latence < 50 ms** par point classifié | Livrable 2 §3.3.2 | Mesuré sur la cellule de scoring |

---

### Ce que nous N'avons PAS à produire (hors MVP)

- ❌ Certification matérielle ATEX (concerne les équipements physiques, pas le logiciel)
- ❌ Atteindre SIL 2 (Recall ≥ 99%) — SIL 1 suffit pour un MVP académique
- ❌ Implémenter MQTT / InfluxDB en production (architecture décrite dans Livrable 2 comme perspective)
- ❌ Respecter la norme CEI 61511 dans son intégralité (seul §3.2.71 SIF + §10.3 SIL nous concerne)

---

### Traduction en métriques de code

```
Recall scénario incendie ≥ 90%      → CEI 61511 SIL 1 ✓
Recall scénario fuite LPG ≥ 90%     → CEI 61511 SIL 1 ✓
Seuils P5 / P10 sur données normales → ISPS §4.1 (critère d'imminence) ✓
3 colonnes : risk_level + anomaly_score + scenario → ISPS §10.1 (traçabilité) ✓
Score calculé en < 50 ms par point   → Livrable 2 §3.3.2 (latence) ✓
```"""

mvp_cell = {
    "cell_type": "markdown",
    "id": "mvp-summary",
    "metadata": {},
    "source": mvp_source
}

# Insert AFTER 8704e623 (Section 10), BEFORE sec11-markdown
cells.insert(idx + 1, mvp_cell)

nb['cells'] = cells
with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"OK — cellule MVP insérée à index {idx+1}")
print(f"Total cellules : {len(nb['cells'])}")
