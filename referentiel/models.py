from django.db import models
from django import forms
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet


class ColorInput(forms.TextInput):
    """Widget pour sélectionner une couleur"""
    input_type = 'color'
    template_name = 'django/forms/widgets/input.html'


@register_snippet
class CategorieMethode(models.Model):
    nom = models.CharField(max_length=200, verbose_name="Nom de la catégorie")
    couleur = models.CharField(
        max_length=7, 
        verbose_name="Code couleur", 
        help_text="Code couleur hexadécimal (ex: #FF0000)",
        default="#007bff"
    )

    panels = [
        FieldPanel("nom"),
        FieldPanel("couleur", widget=ColorInput),
    ]

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Catégorie fiche méthode"
        verbose_name_plural = "Catégories fiches méthode"


@register_snippet
class Niveau(models.Model):
    CYCLES = [
        ("college", "Cycle 4"),
        ("lycee", "Lycée"),
       ("Enseignement", "Enseignement scientifique"),
    ]

    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    cycle = models.CharField(max_length=20, choices=CYCLES, default="lycee")

    panels = [
        FieldPanel("nom"),
        FieldPanel("code"),
        FieldPanel("cycle"),
    ]

    def __str__(self):
        return f"{self.nom} ({self.get_cycle_display()})"


@register_snippet
class Theme(models.Model):
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name="themes")
    nom = models.CharField(max_length=150)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("niveau"),
        FieldPanel("nom"),
        FieldPanel("image"),
    ]

    def __str__(self):
        return f"{self.niveau} → {self.nom}"


@register_snippet
class Chapitre(models.Model):
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="chapitres")
    numero = models.IntegerField()
    titre = models.CharField(max_length=200)

    panels = [
        FieldPanel("theme"),
        FieldPanel("numero"),
        FieldPanel("titre"),
    ]

    class Meta:
        ordering = ["theme", "numero"]

    def __str__(self):
        return f"{self.theme.niveau} | {self.theme.nom} | {self.numero}. {self.titre}"
