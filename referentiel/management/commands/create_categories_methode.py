from django.core.management.base import BaseCommand
from referentiel.models import CategorieMethode


class Command(BaseCommand):
    help = 'Créer les 4 catégories de fiches méthode prédéfinies'

    def handle(self, *args, **options):
        categories = [
            {
                'nom': 'Mesurer et manipuler',
                'couleur': '#28a745'  # Vert
            },
            {
                'nom': 'Utiliser et représenter des modèles',
                'couleur': '#007bff'  # Bleu
            },
            {
                'nom': "S'informer et communiquer",
                'couleur': '#ffc107'  # Jaune
            },
            {
                'nom': 'Outils mathématiques',
                'couleur': '#dc3545'  # Rouge
            }
        ]
        
        created_count = 0
        for cat_data in categories:
            categorie, created = CategorieMethode.objects.get_or_create(
                nom=cat_data['nom'],
                defaults={'couleur': cat_data['couleur']}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Catégorie créée : {categorie.nom}")
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Catégorie déjà existante : {categorie.nom}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"\nRésumé : {created_count} nouvelles catégories créées sur {len(categories)}")
        )
