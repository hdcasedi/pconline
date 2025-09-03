from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail.images.models import Image
from wagtail.snippets.models import register_snippet
from modelcluster.fields import ParentalManyToManyField
from referentiel.models import Niveau, Chapitre


@register_snippet
class DSBrandingSettings(models.Model):
    """Paramètres de marque pour les générateurs de devoirs"""
    logo = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Logo de l'établissement"
    )
    ecole_l1 = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ligne 1 - Nom de l'établissement"
    )
    ecole_l2 = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ligne 2 - Adresse"
    )
    ecole_l3 = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ligne 3 - Ville/Code postal"
    )

    panels = [
        FieldPanel("logo"),
        FieldPanel("ecole_l1"),
        FieldPanel("ecole_l2"),
        FieldPanel("ecole_l3"),
    ]

    class Meta:
        verbose_name = "Paramètres de marque"
        verbose_name_plural = "Paramètres de marque"


class GenerateursHubPage(Page):
    """Page hub pour les générateurs avec onglets"""
    template = "generateurs/generateurs_hub_page.html"
    
    # Contenu de la page
    introduction = models.TextField(
        blank=True,
        verbose_name="Introduction",
        help_text="Texte d'introduction pour les générateurs"
    )
    
    content_panels = Page.content_panels + [
        FieldPanel("introduction"),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []

    class Meta:
        verbose_name = "Hub des générateurs"
        verbose_name_plural = "Hubs des générateurs"


class DSGeneratorPage(Page):
    """Page de génération de devoirs surveillés"""
    template = "generateurs/ds_generator_page.html"
    
    # Étape 1 : Sélection du niveau et des chapitres
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Niveau"
    )
    chapitres = ParentalManyToManyField(
        Chapitre,
        verbose_name="Chapitres"
    )
    
    # Étape 2 : Entête et options
    titre = models.CharField(
        max_length=200,
        default="Contrôle",
        verbose_name="Titre du devoir"
    )
    sous_titre_1 = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sous-titre 1 (chapitres/thèmes)"
    )
    sous_titre_2 = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sous-titre 2 (durée)"
    )
    bareme_global = models.IntegerField(
        default=20,
        verbose_name="Barème global"
    )
    afficher_bareme = models.BooleanField(
        default=True,
        verbose_name="Afficher le barème"
    )
    afficher_bareme_par_question = models.BooleanField(
        default=False,
        verbose_name="Afficher le barème par question"
    )
    afficher_duree_par_exercice = models.BooleanField(
        default=True,
        verbose_name="Afficher la durée par exercice"
    )
    
    # Étape 3 : Composition et pondération
    # QCM
    qcm_min = models.IntegerField(
        default=0,
        verbose_name="Nombre minimum de QCM"
    )
    qcm_max = models.IntegerField(
        default=10,
        verbose_name="Nombre maximum de QCM"
    )
    points_par_qcm = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        choices=[(Decimal('1.0'), '1.0'), (Decimal('0.5'), '0.5')],
        default=Decimal('1.0'),
        verbose_name="Points par QCM"
    )
    
    # Flashcard (QR)
    fc_min = models.IntegerField(
        default=0,
        verbose_name="Nombre minimum de questions-réponses"
    )
    fc_max = models.IntegerField(
        default=10,
        verbose_name="Nombre maximum de questions-réponses"
    )
    points_par_fc = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal('1.0'),
        verbose_name="Points par question-réponse"
    )
    
    # Exercices par niveau
    use_lvl1 = models.BooleanField(
        default=True,
        verbose_name="Utiliser les exercices niveau 1"
    )
    ex_lvl1_min = models.IntegerField(
        default=0,
        verbose_name="Nombre minimum d'exercices niveau 1"
    )
    ex_lvl1_max = models.IntegerField(
        default=5,
        verbose_name="Nombre maximum d'exercices niveau 1"
    )
    
    use_lvl2 = models.BooleanField(
        default=True,
        verbose_name="Utiliser les exercices niveau 2"
    )
    ex_lvl2_min = models.IntegerField(
        default=0,
        verbose_name="Nombre minimum d'exercices niveau 2"
    )
    ex_lvl2_max = models.IntegerField(
        default=5,
        verbose_name="Nombre maximum d'exercices niveau 2"
    )
    
    use_lvl3 = models.BooleanField(
        default=True,
        verbose_name="Utiliser les exercices niveau 3"
    )
    ex_lvl3_min = models.IntegerField(
        default=0,
        verbose_name="Nombre minimum d'exercices niveau 3"
    )
    ex_lvl3_max = models.IntegerField(
        default=5,
        verbose_name="Nombre maximum d'exercices niveau 3"
    )
    
    equilibrer_par_chapitre = models.BooleanField(
        default=True,
        verbose_name="Équilibrer par chapitre"
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("niveau"),
            FieldPanel("chapitres"),
        ], heading="Étape 1 - Niveau et chapitres"),
        MultiFieldPanel([
            FieldPanel("titre"),
            FieldPanel("sous_titre_1"),
            FieldPanel("sous_titre_2"),
            FieldPanel("bareme_global"),
            FieldPanel("afficher_bareme"),
            FieldPanel("afficher_bareme_par_question"),
            FieldPanel("afficher_duree_par_exercice"),
        ], heading="Étape 2 - Entête et options"),
        MultiFieldPanel([
            FieldPanel("qcm_min"),
            FieldPanel("qcm_max"),
            FieldPanel("points_par_qcm"),
            FieldPanel("fc_min"),
            FieldPanel("fc_max"),
            FieldPanel("points_par_fc"),
            FieldPanel("use_lvl1"),
            FieldPanel("ex_lvl1_min"),
            FieldPanel("ex_lvl1_max"),
            FieldPanel("use_lvl2"),
            FieldPanel("ex_lvl2_min"),
            FieldPanel("ex_lvl2_max"),
            FieldPanel("use_lvl3"),
            FieldPanel("ex_lvl3_min"),
            FieldPanel("ex_lvl3_max"),
            FieldPanel("equilibrer_par_chapitre"),
        ], heading="Étape 3 - Composition et pondération"),
    ]

    parent_page_types = ['generateurs.GenerateursHubPage']
    subpage_types = []

    class Meta:
        verbose_name = "Générateur de devoir surveillé"
        verbose_name_plural = "Générateurs de devoirs surveillés"


class SerieGeneratorPage(Page):
    """Page de génération de séries d'exercices"""
    template = "generateurs/serie_generator_page.html"
    
    # Étape 1 : Sélection du niveau et des chapitres
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Niveau"
    )
    chapitres = ParentalManyToManyField(
        Chapitre,
        verbose_name="Chapitres"
    )
    
    # Étape 2 : Entête
    titre = models.CharField(
        max_length=200,
        default="Série d'exercices",
        verbose_name="Titre de la série"
    )
    sous_titre_1 = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sous-titre 1 (chapitres/thèmes)"
    )
    sous_titre_2 = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sous-titre 2"
    )
    
    # Étape 3 : Quantités
    nb_qcm = models.IntegerField(
        default=0,
        verbose_name="Nombre de QCM"
    )
    nb_fc = models.IntegerField(
        default=0,
        verbose_name="Nombre de questions-réponses"
    )
    nb_ex_lvl1 = models.IntegerField(
        default=0,
        verbose_name="Nombre d'exercices niveau 1"
    )
    nb_ex_lvl2 = models.IntegerField(
        default=0,
        verbose_name="Nombre d'exercices niveau 2"
    )
    nb_ex_lvl3 = models.IntegerField(
        default=0,
        verbose_name="Nombre d'exercices niveau 3"
    )
    equilibrer_par_chapitre = models.BooleanField(
        default=True,
        verbose_name="Équilibrer par chapitre"
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("niveau"),
            FieldPanel("chapitres"),
        ], heading="Étape 1 - Niveau et chapitres"),
        MultiFieldPanel([
            FieldPanel("titre"),
            FieldPanel("sous_titre_1"),
            FieldPanel("sous_titre_2"),
        ], heading="Étape 2 - Entête"),
        MultiFieldPanel([
            FieldPanel("nb_qcm"),
            FieldPanel("nb_fc"),
            FieldPanel("nb_ex_lvl1"),
            FieldPanel("nb_ex_lvl2"),
            FieldPanel("nb_ex_lvl3"),
            FieldPanel("equilibrer_par_chapitre"),
        ], heading="Étape 3 - Quantités"),
    ]

    parent_page_types = ['generateurs.GenerateursHubPage']
    subpage_types = []

    class Meta:
        verbose_name = "Générateur de série d'exercices"
        verbose_name_plural = "Générateurs de séries d'exercices"
