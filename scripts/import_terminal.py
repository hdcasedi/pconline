from referentiel.models import Niveau, Theme, Chapitre

niveau = Niveau.objects.get(nom="Terminale spécialité")

# Thème 1
theme1, _ = Theme.objects.get_or_create(niveau=niveau, nom="Constitution et transformations de la matière")
chapitres1 = [
    "Transformations acide-base",
    "Méthodes physiques d’analyse",
    "Méthodes chimiques d’analyse",
    "Modélisation macroscopique de l’évolution d’un système",
    "Modélisation microscopique de l’évolution d’un système",
    "Évolution d’un système, siège d’une transformation nucléaire",
    "Sens d’évolution spontanée d’un système chimique",
    "Force des acides et des bases",
    "Forcer l’évolution d’un système",
    "Synthèses organiques",
]
for i, titre in enumerate(chapitres1, start=1):
    Chapitre.objects.get_or_create(theme=theme1, numero=i, titre=titre)

# Thème 2
theme2, _ = Theme.objects.get_or_create(niveau=niveau, nom="Mouvement et interactions")
chapitres2 = [
    "Mouvement et deuxième loi de Newton",
    "Mouvement dans un champ uniforme",
    "Mouvement dans un champ de gravitation",
    "Modélisation de l’écoulement d’un fluide",
]
for i, titre in enumerate(chapitres2, start=11):
    Chapitre.objects.get_or_create(theme=theme2, numero=i, titre=titre)

# Thème 3
theme3, _ = Theme.objects.get_or_create(niveau=niveau, nom="Énergie : conversions et transferts")
chapitres3 = [
    "Premier principe de la thermodynamique et bilan énergétique",
    "Transferts thermiques",
]
for i, titre in enumerate(chapitres3, start=15):
    Chapitre.objects.get_or_create(theme=theme3, numero=i, titre=titre)

# Thème 4
theme4, _ = Theme.objects.get_or_create(niveau=niveau, nom="Ondes et signaux")
chapitres4 = [
    "Sons et effet Doppler",
    "Diffraction et interférences",
    "Lunette astronomique",
    "La lumière : un flux de photons",
    "Dynamique du dipôle RC",
]
for i, titre in enumerate(chapitres4, start=17):
    Chapitre.objects.get_or_create(theme=theme4, numero=i, titre=titre)

print("✅ Terminale spécialité importée avec succès")





