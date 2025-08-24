from referentiel.models import Niveau, Theme, Chapitre

# Liste des niveaux collège
niveaux = [
    "Troisième",
    "Quatrième",
    "Cinquième"
]

# Définition des thèmes et chapitres communs
themes = {
    "Organisation et transformation de la matière": [
        "Les états de la matière",
        "Les changements d’états de la matière",
        "Mélange et corps pur",
        "La masse volumique",
        "Les espèces chimiques",
        "Les transformations chimiques",
        "Les acides et les bases",
        "L’Univers",
        "Du Big Bang à l’atome",
    ],
    "Mouvements et interactions": [
        "Mouvement",
        "Action mécanique et force",
    ],
    "L’énergie, ses transferts et ses conversions": [
        "Sources et formes d’énergie",
        "Réaliser des circuits électriques simples",
        "Tension, intensité et lois en électricité",
        "Puissance et énergie électrique",
    ],
    "Des signaux pour observer et communiquer": [
        "Les signaux lumineux",
        "Les signaux sonores",
    ],
}

# Création pour chaque niveau
for niveau_nom in niveaux:
    try:
        niveau = Niveau.objects.get(nom=niveau_nom)
    except Niveau.DoesNotExist:
        print(f"⚠ Niveau '{niveau_nom}' introuvable, à créer d'abord dans l'admin.")
        continue

    numero_chapitre = 1
    for theme_nom, chapitres in themes.items():
        theme, _ = Theme.objects.get_or_create(niveau=niveau, nom=theme_nom)
        for titre in chapitres:
            Chapitre.objects.get_or_create(theme=theme, numero=numero_chapitre, titre=titre)
            numero_chapitre += 1

print("✅ Thèmes + chapitres créés pour Troisième, Quatrième et Cinquième")