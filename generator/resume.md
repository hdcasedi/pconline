# Résumé du module Generator — Pages et valeurs capturées

- Fichier UI principal: `generator/templates/generator/devoir_wizard.html`
- Gabarit en-tête (PDF/LaTeX): `generator/templates/generator/pdf/entete.tex`

## Étapes du wizard et champs capturés

### Étape 1 (A) – Choix des chapitres
- `chapitre_ids` (number[]): liste d’IDs de chapitres sélectionnés (obligatoire)

### Étape 2 (B) – Type, titres, barème et entête
- `type` ("ds" | "serie"): type de sortie
  - DS: titre par défaut "Devoir"
  - Série: titre par défaut "Série d’exercice"
- `titre` (string): titre saisi (conserve une saisie personnalisée)
- `sous_titre_1` (string)
- `sous_titre_2` (string)
  - Préremplissage auto: si vide à l’entrée de l’étape B, rempli avec les titres des chapitres sélectionnés, séparés par " | "
  - Alimente aussi `header_line2` si vide
- `bareme_global` (number): visible/utile seulement pour DS (par défaut 20)
- `afficher_bareme_total` (boolean): afficher le barème total
- `afficher_bareme_par_exercice` (boolean): afficher le barème par exercice
- `afficher_duree_temps` (boolean): afficher la durée estimée
- Paramètres d’entête (bouton “Paramétrer l’entête”):
  - `header_logo_url` (string): par défaut `https://physiquechimie.online/media/images/logo.original.png`
  - `header_line1` (string): par défaut `PHYSIQUE CHIMIE ONLINE`
  - `header_line2` (string): prérempli par défaut avec `sous_titre_2` si vide
  - `header_line3` (string)

### Étape 3 (C) – Composition (logique DS/Série)
- Si `type === 'ds'`:
  - QCM:
    - `ds_qcm_enable` (boolean)
    - `ds_qcm_min` (number, défaut 0)
    - `ds_qcm_max` (number, défaut 10)
    - `ds_qcm_point` (number, 1 ou 0.5 – défaut 1)
  - Réponse libre:
    - `ds_qr_enable` (boolean)
    - `ds_qr_min` (number, défaut 0)
    - `ds_qr_max` (number, défaut 10)
    - `ds_qr_point` (number, 1 ou 0.5 – défaut 1)
  - Exercices (catégories – booléens):
    - `ds_exo_application_enable`
    - `ds_exo_entrainement_enable`
    - `ds_exo_approfondissement_enable`
- Si `type === 'serie'`:
  - `serie_qcm_count` (number, défaut 0)
  - `serie_qr_count` (number, défaut 0)
  - `serie_exo_application_count` (number, défaut 0)
  - `serie_exo_entrainement_count` (number, défaut 0)
  - `serie_exo_approfondissement_count` (number, défaut 0)

### Étape 4 (D) – Options
- `equilibrer_par_chapitre` (boolean, défaut true)
- `masquer_fc` (boolean, défaut true)

### Étape 5 (E) – Récapitulatif
- Affiche le `payload` courant en JSON (à but de contrôle visuel)

## Comportements dynamiques (UI)
- Titre: bascule automatique entre "Devoir" (DS) et "Série d’exercice" (Série) sans écraser une saisie utilisateur.
- Barème global: champ visible seulement pour DS.
- Préremplissage automatique de `sous_titre_2` et de `header_line2` avec les titres des chapitres sélectionnés (séparateur " | ") si vides à l’entrée de l’étape 2.
- Panneaux Étape 3: affichage conditionnel DS/Série.

## Clés de payload (référence rapide)
- Étape 1: `chapitre_ids`
- Étape 2: `type`, `titre`, `sous_titre_1`, `sous_titre_2`, `bareme_global`, `afficher_bareme_total`, `afficher_bareme_par_exercice`, `afficher_duree_temps`, `header_logo_url`, `header_line1`, `header_line2`, `header_line3`
- Étape 3 DS: `ds_qcm_enable`, `ds_qcm_min`, `ds_qcm_max`, `ds_qcm_point`, `ds_qr_enable`, `ds_qr_min`, `ds_qr_max`, `ds_qr_point`, `ds_exo_application_enable`, `ds_exo_entrainement_enable`, `ds_exo_approfondissement_enable`
- Étape 3 Série: `serie_qcm_count`, `serie_qr_count`, `serie_exo_application_count`, `serie_exo_entrainement_count`, `serie_exo_approfondissement_count`
- Étape 4: `equilibrer_par_chapitre`, `masquer_fc`
- Divers: `header_logo_url`, `header_line1`, `header_line2`, `header_line3`, `seed`
- Hérités (non utilisés dans l’UI actuelle): `qcm_min`, `qcm_max`, `ex_lvl1_min`, `ex_lvl1_max`, `ex_lvl2_min`, `ex_lvl2_max`, `ex_lvl3_min`, `ex_lvl3_max`

## Fichiers impliqués
- Wizard UI: `generator/templates/generator/devoir_wizard.html`
- Entête PDF/LaTeX: `generator/templates/generator/pdf/entete.tex`

