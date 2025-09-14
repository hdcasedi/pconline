# Changelog - Sélection Centralisée et Déduplication

## Résumé des modifications

### ✅ Objectifs atteints

1. **Service de sélection centralisé** : `generator/services/selection.py`
   - Bundle unique avec déduplication des variantes QCM
   - RNG déterministe basé sur seed + ID d'item
   - Clés de variante stables pour éviter les doublons

2. **Cohérence Preview/PDF** : Même sélection garantie
   - `qcm_preview` utilise le service et stocke le bundle en session
   - `pdf_build` consomme le bundle en session (pas de recalcul)
   - Nouvelles routes `qcm_pdf_enonce` et `qcm_pdf_correction`

3. **Sections TeX complètes** :
   - `section_flashcards.tex` : Questions/réponses avec mode correction
   - `section_exercices.tex` : Exercices avec énoncé/correction
   - `main.tex` inclut automatiquement les sections si contenu présent

4. **Interface utilisateur** :
   - Boutons "Générer PDF Énoncé" et "Générer PDF Correction" dans la preview
   - Affichage du seed avec bouton de copie
   - Liens avec paramètre `?seed=` pour garantir la même sélection

## Fichiers modifiés

### Nouveaux fichiers
- `generator/services/__init__.py`
- `generator/services/selection.py` - Service central de sélection
- `generator/templates/generator/pdf/section_flashcards.tex`
- `generator/templates/generator/pdf/section_exercices.tex`

### Fichiers modifiés
- `generator/views.py` :
  - Ajout import du service de sélection
  - Nouvelle fonction `qcm_preview` utilisant le service
  - Nouvelles fonctions `qcm_pdf_enonce` et `qcm_pdf_correction`
  - Refactorisation de `pdf_build` pour utiliser le bundle en session
  - Ajout helper `_image_abspath_from_url`

- `generator/urls.py` :
  - Ajout routes `qcm/pdf/enonce/` et `qcm/pdf/correction/`

- `generator/templates/generator/qcm_preview.html` :
  - Ajout boutons de génération PDF avec seed
  - Script de copie de seed

- `generator/templates/generator/pdf/main.tex` :
  - Inclusion conditionnelle des nouvelles sections

## Fonctionnement

### 1. Sélection déterministe
```python
# Clé de variante stable pour éviter les doublons
variant_key = _variant_key_for_qcmA(page_id, statement, options, correct_index)

# RNG déterministe par item
rng = _rng_from_seed(base_seed, f"QA-{q.id}")
```

### 2. Bundle en session
```python
# Stockage en session pour cohérence
bundle = build_selection_bundle(payload, seed)
request.session["selection_bundle"] = bundle.to_jsonable()
request.session["selection_seed"] = seed
```

### 3. Réutilisation dans PDF
```python
# pdf_build consomme le bundle (pas de recalcul)
bundle_json = request.session.get("selection_bundle")
qcms_data = bundle_json.get("qcms", [])
```

## Points d'intégration

### Branchement sur la compilation PDF existante
Les nouvelles vues `qcm_pdf_enonce` et `qcm_pdf_correction` appellent directement `pdf_build(request, mode)` qui :
1. Récupère le bundle en session
2. Adapte les données pour les templates LaTeX
3. Rend tous les templates (main, header, sections)
4. Compile avec `pdflatex` (2 passes)
5. Retourne le PDF généré

### Filtres LaTeX
Les nouvelles sections utilisent le filtre `html2tex` existant pour la conversion HTML → LaTeX, garantissant la cohérence avec les QCM.

## Tests manuels

1. **Wizard → Preview** : Vérifier sélection sans doublons
2. **Boutons PDF** : Même sélection dans énoncé et correction
3. **Seed identique** : Cohérence entre preview et PDF
4. **Sections TeX** : Flashcards et exercices visibles si sélectionnés

## Non-régression

- Logique métier de sélection préservée
- Templates LaTeX existants inchangés
- Pipeline de compilation PDF inchangé
- Interface utilisateur existante préservée
