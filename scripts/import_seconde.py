from referentiel.models import Niveau, Theme, Chapitre

# Vérifie bien le nom exact de ton Niveau dans l’admin
niveau = Niveau.objects.get(nom="Seconde")

# --- Supprimer les anciens thèmes/chapitres ---
Theme.objects.filter(niveau=niveau).delete()

# --- Définir les vrais thèmes et chapitres d’après le manuel ---
themes = {
    "Constitution et transformations de la matière": [
        "Corps purs et mélanges",
        "Solutions aqueuses",
        "De l’atome à l’élément chimique",
        "Vers des entités plus stables",
        "Quantité de matière",
        "Transformation physique",
        "Transformation chimique",
        "Transformation nucléaire",
    ],
    "Mouvement et interactions": [
        "Description des mouvements",
        "Modéliser une action mécanique sur un système",
        "Principe d’inertie",
    ],
    "Ondes et signaux": [
        "Émission et perception d’un son",
        "Spectres d’émission",
        "Réfraction et réflexion de la lumière",
        "Lentilles minces convergentes",
        "Lois de l’électricité",
    ],
}

# --- Créer en base ---
for theme_nom, chapitres in themes.items():
    theme, _ = Theme.objects.get_or_create(niveau=niveau, nom=theme_nom)
    for i, titre in enumerate(chapitres, start=1):
        Chapitre.objects.get_or_create(theme=theme, numero=i, titre=titre)

print("✅ Thèmes et chapitres corrigés pour Seconde")
