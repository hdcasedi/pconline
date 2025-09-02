from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, FieldRowPanel

from .blocks import MethodeContentBlock


class MethodeHubPage(Page):
    """Page de recensement des fiches méthode"""
    intro = RichTextField(blank=True, verbose_name="Introduction")
    
    # Configuration des onglets
    onglet_actif = models.CharField(
        max_length=10,
        choices=[
            ('college', 'Collège'),
            ('lycee', 'Lycée'),
        ],
        default='college',
        verbose_name="Onglet actif par défaut"
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("onglet_actif"),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = ['methode.MethodePage']

    class Meta:
        verbose_name = "Recensement Fiches Méthode"
        verbose_name_plural = "Recensement Fiches Méthode"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        # Récupérer l'onglet actif depuis l'URL ou utiliser la valeur par défaut
        onglet = request.GET.get('onglet', self.onglet_actif)
        context['onglet_actif'] = onglet
        
        # Récupérer toutes les fiches méthode
        fiches_methodes = MethodePage.objects.live().order_by('categorie__nom', 'title')
        
        # Filtrer selon l'onglet
        if onglet == 'college':
            fiches_methodes = fiches_methodes.filter(fiche_college=True)
        else:  # lycee
            fiches_methodes = fiches_methodes.filter(fiche_lycee=True)
        
        # Grouper par catégorie
        categories_fiches = {}
        for fiche in fiches_methodes:
            categorie = fiche.categorie
            if categorie:
                if categorie.nom not in categories_fiches:
                    categories_fiches[categorie.nom] = {
                        'categorie': categorie,
                        'fiches': []
                    }
                categories_fiches[categorie.nom]['fiches'].append(fiche)
        
        # Trier les catégories par nom
        context['categories_fiches'] = dict(sorted(categories_fiches.items()))
        
        return context


class MethodePage(Page):
    intro = RichTextField(blank=True, verbose_name="Introduction")
    body = StreamField(
        MethodeContentBlock(),  # Utilise le bloc principal qui contient tous les blocs
        use_json_field=True,
        blank=True,
        verbose_name="Contenu"
    )
    
    # Nouveaux champs
    categorie = models.ForeignKey(
        'referentiel.CategorieMethode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Catégorie méthode"
    )
    fiche_college = models.BooleanField(
        default=False,
        verbose_name="Fiche méthode collège"
    )
    fiche_lycee = models.BooleanField(
        default=False,
        verbose_name="Fiche méthode lycée"
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("categorie"),
        FieldRowPanel([
            FieldPanel("fiche_college"),
            FieldPanel("fiche_lycee"),
        ], heading="Type de fiche"),
        FieldPanel("body"),
    ]

    parent_page_types = ['methode.MethodeHubPage']
    subpage_types = []

    class Meta:
        verbose_name = "Méthode"
        verbose_name_plural = "Méthodes"



