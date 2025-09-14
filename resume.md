# Récapitulatif — Rendu des tableaux et style Tailwind (cours + exo)

Page de référence: [Cours — Filtre](https://physiquechimie.online/les-cours/les-cours-de-1-spe/couleurs/exercices-couleur-per%C3%A7ue/filtre/)

## 1) Base/layout chargé sur tout le site
- Fichier: `pconline_site/templates/base.html`
  - Charge Tailwind via CDN:
    - `<script src="https://cdn.tailwindcss.com"></script>`
  - Charge MathJax et Alpine.js
  - Conteneur principal de page: `body.bg-blue-100` + wrapper `{% block content %}`

## 2) Côté EXO (exercices paramétrés)
- Template de bloc table stylé Tailwind
  - Fichier: `exo/templates/exo/blocks/styled_table.html`
  - Utilisé par la classe `StyledTableBlock`.
- Définition du bloc
  - Fichier: `exo/blocks.py`
    - `from wagtail.contrib.table_block.blocks import TableBlock`
    - `class StyledTableBlock(TableBlock): template = "exo/blocks/styled_table.html"`
- Templatetags de rendu des paramètres tableau
  - Fichier: `exo/templatetags/exo_tables.py`
    - Tag: `render_param_table(context, name, view, orientation, n, seed)`
    - Construit un `TableBlock` à partir d’une banque (masques, orientation) et rend avec `StyledTableBlock`.
  - Fichier: `exo/templatetags/param_tags.py`
    - `_tableau_pattern = re.compile(r"\[\[\s*tableau:...\]\]")`
    - Fonction interne `tableau_repl(match)`
      - Parse options `view|orientation|n|seed`
      - Gère une graine stable par rendu (cache `__table_seed_cache`, `__render_seed`)
      - Appelle `render_param_table` avec un `Context` local `{'exo_params': {name: param}, 'K': base_seed}`
- Utilitaires de transformation banque → valeur TableBlock
  - Fichier: `exo/utils/table_param.py`
    - `parse_table_bank`, `pick_rows`, `apply_masks_h`, `apply_masks_v`
    - `to_tableblock_value_h`, `to_tableblock_value_v`

Flux EXO: `[[tableau:name|...]]` dans un contenu → `param_tags.tableau_repl` → `exo_tables.render_param_table` → `StyledTableBlock.render(value)` → `exo/templates/exo/blocks/styled_table.html`.

## 3) Côté COURS (StreamField classique)
- Modèles (déclaration des blocs)
  - Fichier: `cours/models.py`
    - `CoursContentBlock.tableau = TableBlock(template='cours/blocks/tableau.html')`
- Templates de bloc table
  - Fichier: `cours/templates/cours/blocks/tableau.html`
    - Rendu d’un `TableBlock` (ou `value.data`) avec classes Tailwind: entête `bg-blue-600`, alternance lignes, etc.
    - Appelle `MathJax.typesetPromise()` après rendu.
  - Fichier: `cours/templates/cours/blocks/table_block.html`
    - Autre rendu stylé d’un tableau (`value.headings` / `value.rows`).
- Page cours (layout contenu)
  - Fichier: `cours/templates/cours/cours_page.html`
    - Étend `base.html`
    - Affiche `page.contenu` via `{% include_block %}` (les blocs choisissent leur template: `tableau.html`, etc.)

Flux COURS: Éditeur Wagtail → bloc `TableBlock` dans `page.contenu` → inclusion `cours/blocks/tableau.html` (ou `table_block.html`) → classes Tailwind présentes dans le HTML rendu.

## 4) Chargement Tailwind / Purge
- Fichier: `tailwind.config.js`
  - `content: ["./pconline_site/templates/**/*.html", "./**/templates/**/*.html"]`
  - Si build local (sans CDN), ajouter si besoin: `"./exo/templates/**/*.html", "./**/*.py"` et une `safelist` pour classes dynamiques.
- CDN actif dans `base.html`. Si on garde le CDN, typiquement pas besoin de rebuild.

## 5) Diagnostic “pas de style sur un tableau”
- Si le tableau vient d’un RichText/Markdown (pas d’un `TableBlock`), il sort sans classes Tailwind → non stylé. Solutions:
  - Activer la Typography du CDN: `<script src="https://cdn.tailwindcss.com?plugins=typography"></script>` et entourer le contenu d’un wrapper `.prose`.
  - Ou remplacer le tableau Markdown par un vrai `TableBlock` (il utilisera `cours/blocks/tableau.html`).
- Vérifier que la page étend `base.html` (les pages cours le font). Exo paramétrés utilisent les templates et tags ci-dessus.

## 6) Doublons/chemins possibles à surveiller
- `exo/templates/exo/blocks/styled_table.html` (bon chemin) vs `exo/templates/blocks/styled_table.html` (ne pas utiliser)
- `StyledTableBlock` pointe bien vers `exo/blocks/styled_table.html`.
