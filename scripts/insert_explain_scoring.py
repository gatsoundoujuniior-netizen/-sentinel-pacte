import json

with open('pacte.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']
idx = next(i for i, c in enumerate(cells) if c.get('id') == 'sec11-markdown')

source = """# Section 11 — Système de Scoring : Classification NORMAL / SUSPECT / CRITIQUE

---

## Avant de commencer : comprendre P5 et P10

### L'analogie de la classe

Imagine une classe de 100 élèves. Chaque élève a une note.
Tu veux savoir qui est "en difficulté" sans avoir de seuil fixe défini à l'avance.

Tu fais simple : tu **tries les notes du plus bas au plus haut**, et tu regardes :

- Le **10ème élève en partant du bas** → c'est le **P10** (10e percentile)
- Le **5ème élève en partant du bas** → c'est le **P5** (5e percentile)

Tout élève dont la note est **en dessous du P10** est considéré "à surveiller".
Tout élève dont la note est **en dessous du P5** est considéré "en grande difficulté".

---

### Appliqué à PACTE

À la place des élèves, on a **402 711 points de données normaux** (aucune anomalie).
Chacun a un `anomaly_score` produit par l'Isolation Forest.

On trie ces scores du plus bas au plus haut :

```
Rang 1        →  score le plus bas  (point le plus "limite" parmi les normaux)
...
Rang 20 135   →  score = 0.0991   ← P5  (5% des normaux sont en dessous)
...
Rang 40 271   →  score = 0.1277   ← P10 (10% des normaux sont en dessous)
...
Rang 402 711  →  score le plus haut (point le plus clairement normal)
```

---

### La règle de classification

Quand un nouveau point arrive, on compare son `anomaly_score` à ces deux lignes :

```
score > 0.1277              →  NORMAL    il ressemble aux 90% des points normaux
0.0991 < score ≤ 0.1277    →  SUSPECT   il ressemble aux 10% les plus limites
score ≤ 0.0991              →  CRITIQUE  il est plus anormal que 95% des normaux
```

> **En une phrase** : P5 et P10 sont des lignes de référence calculées sur les données normales.
> Tout ce qui tombe en dessous de ces lignes est considéré comme anormal.

---

### Pourquoi cette méthode et pas un seuil fixe ?

| Seuil fixe (ex. score < 0.1) | Seuil dynamique P5/P10 |
|------------------------------|------------------------|
| Dépend du dataset actuel | S'adapte à n'importe quel dataset |
| Si les données changent, le seuil devient faux | Le seuil se recalcule automatiquement |
| Arbitraire — difficile à justifier | Justifiable : "5% les plus extrêmes des normaux" |
| ✗ Fragile | ✓ Robuste |

---

## 11.1 Objectif du scoring

Transformer le score brut de l'Isolation Forest (`anomaly_score`) en un **niveau de risque opérationnel**, conforme aux exigences réglementaires de la Section 10 :

| Niveau | Code ISPS | Directive ATEX | CEI 61511 |
|--------|-----------|----------------|-----------|
| **NORMAL** | Niveau 1 — risque minimal | Hors seuil LIE | En dessous de toute SIL |
| **SUSPECT** | Niveau 2 — risque accru | Approche du seuil | SIL 1 (Recall ≥ 90%) |
| **CRITIQUE** | Niveau 3 — imminence | Seuil ATEX atteint | SIL 2 (Recall ≥ 99%) |

---

## 11.2 Architecture du scoring (4 étapes)

### Étape 1 — Seuils dynamiques percentile (ISPS §4.1)
Calcul de P5 et P10 sur les données normales uniquement → seuils adaptatifs.

### Étape 2 — Score composite multi-capteurs (ISPS §4.1)
Si **≥ 2 capteurs** du même device dépassent 1.5 σ simultanément → niveau élevé d'un cran.
- NORMAL → SUSPECT
- SUSPECT → CRITIQUE

### Étape 3 — Persistance temporelle (CEI 61511 §3.2.71)
Si un point reste **SUSPECT pendant > 10 fenêtres consécutives** → escalade automatique en **CRITIQUE**.
Cela permet de détecter les anomalies lentes (surchauffe progressive, fuite chimique lente).

### Étape 4 — Journal de traçabilité (ISPS §10.1)
Chaque point enregistre : `timestamp + device + anomaly_score + risk_level + scenario`

## 11.3 Métriques de validation
- **Recall CRITIQUE** : % des scénarios critiques (incendie, fuite LPG) détectés au niveau CRITIQUE
- **Recall SUSPECT** : % des scénarios suspects détectés au niveau ≥ SUSPECT
- **Faux positifs CRITIQUE** : taux de points normaux élevés à CRITIQUE par erreur
- **Distribution globale** : répartition NORMAL / SUSPECT / CRITIQUE sur l'ensemble du dataset"""

cells[idx]['source'] = source

with open('pacte.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("OK — cellule sec11-markdown mise à jour")
