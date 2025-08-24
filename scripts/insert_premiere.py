from referentiel.models import Niveau, Theme, Chapitre

def run():
    # Récupérer le niveau Première spécialité
    niveau = Niveau.objects.get(nom="Première spécialité")

    # Thème 1
    theme1 = Theme.objects.create(niveau=niveau, nom="Constitution et transformations de la matière")
    chapitres1 = [
        "La mole",
        "Réactions d'oxydoréduction",
        "Tableau d'avancement",
        "Titrages colorimétriques",
        "De la structure à la polarité d'une entité chimique",
        "Cohésion de la matière",
        "Structure des entités organiques",
        "Synthèse",
        "Réactions de combustion",
    ]
    for i, titre in enumerate(chapitres1, start=1):
        Chapitre.objects.create(theme=theme1, numero=i, titre=titre)

    # Thème 2
    theme2 = Theme.objects.create(niveau=niveau, nom="Mouvement et interactions")
    chapitres2 = [
        "Interactions, forces et champs",
        "Description d'un fluide au repos",
        "Mouvement d'un système",
    ]
    for i, titre in enumerate(chapitres2, start=10):
        Chapitre.objects.create(theme=theme2, numero=i, titre=titre)

    # Thème 3
    theme3 = Theme.objects.create(niveau=niveau, nom="Énergie : conversions et transferts")
    chapitres3 = [
        "L'énergie des systèmes électriques",
        "Aspects énergétiques des phénomènes mécaniques",
    ]
    for i, titre in enumerate(chapitres3, start=13):
        Chapitre.objects.create(theme=theme3, numero=i, titre=titre)

    # Thème 4
    theme4 = Theme.objects.create(niveau=niveau, nom="Ondes et signaux")
    chapitres4 = [
        "Ondes mécaniques",
        "Lentilles minces convergentes",
        "Couleurs",
        "Lumière : ondes et particules",
    ]
    for i, titre in enumerate(chapitres4, start=15):
        Chapitre.objects.create(theme=theme4, numero=i, titre=titre)

    print("✅ Première spécialité remplie avec ses 4 thèmes et chapitres.")
