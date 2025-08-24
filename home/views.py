import json
from django.shortcuts import render
from referentiel.models import Niveau

def homepage(request):
    niveaux = Niveau.objects.prefetch_related("themes__chapitres").all().order_by("cycle", "nom")

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
                    "chapitres": [c.titre for c in theme.chapitres.all()]
                }
                for theme in niveau.themes.all()
            ]
        })

    # 🔹 Sérialiser en JSON
    data_json = json.dumps(data, ensure_ascii=False)

    # 🔹 Envoyer "data_json" au template
    return render(request, "home/home.html", {"data_json": data_json})
