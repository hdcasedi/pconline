from django.core.management.base import BaseCommand
from methode.models import MethodePage, MethodeHubPage
from referentiel.models import CategorieMethode


class Command(BaseCommand):
    help = 'Configurer des fiches méthode de test avec les bonnes catégories'

    def handle(self, *args, **options):
        # Récupérer les catégories
        categories = {cat.nom: cat for cat in CategorieMethode.objects.all()}
        
        if not categories:
            self.stdout.write(
                self.style.ERROR("Aucune catégorie trouvée. Exécutez d'abord 'python manage.py create_categories_methode'")
            )
            return
        
        # Mettre à jour la fiche existante
        fiches_existantes = MethodePage.objects.all()
        
        if fiches_existantes.exists():
            fiche = fiches_existantes.first()
            fiche.categorie = categories['Mesurer et manipuler']
            fiche.fiche_college = True
            fiche.fiche_lycee = True
            fiche.save()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Fiche mise à jour : {fiche.title}")
            )
        
        # Créer quelques fiches de test supplémentaires
        fiches_test = [
            {
                'title': 'Utiliser un multimètre',
                'categorie': 'Mesurer et manipuler',
                'college': True,
                'lycee': True
            },
            {
                'title': 'Tracer un graphique',
                'categorie': 'Utiliser et représenter des modèles',
                'college': True,
                'lycee': True
            },
            {
                'title': 'Lire un tableau de données',
                'categorie': "S'informer et communiquer",
                'college': True,
                'lycee': False
            },
            {
                'title': 'Calculer une moyenne',
                'categorie': 'Outils mathématiques',
                'college': True,
                'lycee': True
            },
            {
                'title': 'Utiliser un oscilloscope',
                'categorie': 'Mesurer et manipuler',
                'college': False,
                'lycee': True
            },
            {
                'title': 'Modéliser une situation',
                'categorie': 'Utiliser et représenter des modèles',
                'college': False,
                'lycee': True
            }
        ]
        
        # Récupérer la page parent (MethodeHubPage)
        hub_page = MethodeHubPage.objects.first()
        if not hub_page:
            self.stdout.write(
                self.style.ERROR("Aucune page hub trouvée. Créez d'abord une page MethodeHubPage dans l'admin.")
            )
            return
        
        created_count = 0
        for fiche_data in fiches_test:
            # Vérifier si la fiche existe déjà
            if not MethodePage.objects.filter(title=fiche_data['title']).exists():
                fiche = MethodePage(
                    title=fiche_data['title'],
                    slug=fiche_data['title'].lower().replace(' ', '-'),
                    categorie=categories[fiche_data['categorie']],
                    fiche_college=fiche_data['college'],
                    fiche_lycee=fiche_data['lycee']
                )
                hub_page.add_child(instance=fiche)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Fiche créée : {fiche.title}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Fiche déjà existante : {fiche_data['title']}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"\nRésumé : {created_count} nouvelles fiches créées")
        )
