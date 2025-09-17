import json
from django.shortcuts import render
from referentiel.models import Niveau
from cours.models import CoursPage

def homepage(request):
    niveaux = Niveau.objects.prefetch_related("themes__chapitres__cours").all().order_by("cycle", "nom")

    data = {}
    for niveau in niveaux:
        cycle = niveau.cycle
        if cycle not in data:
            data[cycle] = {"nom": cycle, "niveaux": []}

        data[cycle]["niveaux"].append({
            "id": niveau.id,
            "nom": niveau.nom,
            "themes": [
                {
                    "nom": theme.nom,
                    "chapitres": [
                        {
                            "titre": c.titre,
                            "id": c.id,
                            "cours_url": c.cours.first().url if c.cours.exists() else None,
                            "cours_title": c.cours.first().title if c.cours.exists() else None
                        }
                        for c in theme.chapitres.all() if c.cours.exists()  # Seuls les chapitres avec cours
                    ]
                }
                for theme in niveau.themes.all()
            ]
        })

    # 🔹 Sérialiser en JSON
    data_json = json.dumps(data, ensure_ascii=False)

    # 🔹 Envoyer "data_json" au template
    return render(request, "home/home.html", {"data_json": data_json})


def mon_compagnon_page(request):
    return render(request, "home/mon_compagnon.html")
