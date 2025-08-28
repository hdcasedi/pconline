from django.db import models
from django import forms
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import (
    StructBlock, CharBlock, ChoiceBlock, RichTextBlock,
    BooleanBlock, TextBlock, StreamBlock
)
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.admin.forms import WagtailAdminPageForm
from referentiel.models import Chapitre


# ============== Blocs ==============

class ParagrapheBlock(StructBlock):
    style = ChoiceBlock(
        choices=[
            ('normal', 'Normal'),
            ('exemple', 'Exemple'),
            ('remarque', 'Remarque'),
            ('definition', 'Définition'),
        ],
        default='normal',
        label="Style",
    )
    alignement = ChoiceBlock(
        choices=[
            ('gauche', 'Gauche'),
            ('centre', 'Centré'),
            ('justifie', 'Justifié'),
            ('droite', 'Droite'),
        ],
        default='gauche',
        label="Alignement",
    )
    contenu = RichTextBlock(
        features=[
            'h2', 'h3', 'bold', 'italic', 'underline', 'link',
            'superscript', 'subscript', 'strikethrough', 'ol',
            'ul', 'hr', 'blockquote', 'code', 'image', 'embed'
        ],
        label="Contenu",
    )
    titre = CharBlock(required=False, label="Titre (pour remarque/définition)")

    class Meta:
        template = "cours/blocks/paragraphe.html"
        icon = "doc-full"
        label = "Paragraphe"


class TitreBlock(StructBlock):
    niveau = ChoiceBlock(
        choices=[('h1', 'H1'), ('h2', 'H2'), ('h3', 'H3')],
        default='h1',
        label="Niveau",
    )
    texte = CharBlock(label="Texte")
    fiche_methode = BooleanBlock(default=False, label="Afficher bouton fiche méthode")
    texte_bouton = CharBlock(default="Fiche méthode", label="Texte du bouton")

    class Meta:
        template = "cours/blocks/titre.html"
        icon = "title"
        label = "Titre"


class CodeBlock(StructBlock):
    langage = ChoiceBlock(
        choices=[
            ('python', 'Python'), ('javascript', 'JavaScript'),
            ('html', 'HTML'), ('css', 'CSS'),
            ('c', 'C'), ('cpp', 'C++'), ('java', 'Java'),
            ('php', 'PHP'), ('sql', 'SQL'), ('bash', 'Bash'),
            ('json', 'JSON'), ('xml', 'XML'), ('yaml', 'YAML'),
            ('markdown', 'Markdown'),
        ],
        default='python',
        label="Langage",
    )
    code = TextBlock(label="Code")

    class Meta:
        template = "cours/blocks/code.html"
        icon = "code"
        label = "Code"


class CoursContentBlock(StreamBlock):
    paragraphe = ParagrapheBlock()
    titre = TitreBlock()
    tableau = TableBlock()
    code = CodeBlock()


# ============== Pages ==============

class CoursRootPage(Page):
    """Page racine des cours"""
    intro = models.TextField(
        blank=True,
        verbose_name="Introduction",
        help_text="Texte d'introduction pour la page des cours",
    )

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    class Meta:
        verbose_name = "Racine des cours"

    parent_page_types = ['wagtailcore.Page']
    subpage_types = ['cours.CoursIndexPage']


class CoursIndexPage(Page):
    """Index par niveau"""
    niveau = models.ForeignKey(
        'referentiel.Niveau',
        on_delete=models.PROTECT,  # Wagtail déconseille CASCADE
        related_name='cours_index',
        verbose_name="Niveau",
    )

    content_panels = Page.content_panels + [
        FieldPanel('niveau'),
    ]

    class Meta:
        verbose_name = "Index des cours"

    parent_page_types = ['cours.CoursRootPage']
    subpage_types = ['cours.CoursPage']


# --- Form admin qui filtre les chapitres par niveau parent ---
class CoursPageForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        parent_page = kwargs.pop('parent_page', None)  # fourni à la création
        super().__init__(*args, **kwargs)

        parent_niveau = None
        # création
        if parent_page and hasattr(parent_page.specific, 'niveau'):
            parent_niveau = parent_page.specific.niveau
        # édition
        elif self.instance and self.instance.pk:
            parent = self.instance.get_parent().specific
            if hasattr(parent, 'niveau'):
                parent_niveau = parent.niveau

        if 'chapitre' in self.fields:
            qs = Chapitre.objects.all()
            if parent_niveau:
                qs = qs.filter(theme__niveau=parent_niveau)
            self.fields['chapitre'].queryset = qs


class CoursPage(Page):
    """Page de cours"""
    template = "cours/cours_page.html"
    chapitre = models.ForeignKey(
        Chapitre,
        on_delete=models.PROTECT,
        related_name='cours',
        verbose_name="Chapitre",
    )

    contenu = StreamField(
        CoursContentBlock,  # la CLASSE (Wagtail l’instancie)
        use_json_field=True,
        verbose_name="Contenu",
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel('chapitre'),
        FieldPanel('contenu'),
    ]

    # ➜ branche le form custom
    base_form_class = CoursPageForm

    # (optionnel mais recommandé) re-filtre côté serveur
    def clean(self):
        super().clean()
        parent = self.get_parent().specific if self.get_parent() else None
        if parent and hasattr(parent, 'niveau') and self.chapitre:
            if self.chapitre.theme.niveau_id != parent.niveau_id:
                raise forms.ValidationError({
                    'chapitre': f'Le chapitre doit appartenir au niveau "{parent.niveau.nom}".'
                })

    # >>> IMPORTANT pour que l'admin passe toujours le parent_page,
    # même en édition (sinon certains contextes ne le fournissent pas)
    def get_admin_form_kwargs(self):
        kwargs = super().get_admin_form_kwargs()
        if 'parent_page' not in kwargs:
            try:
                parent = self.get_parent()
            except Exception:
                parent = None
            if parent:
                kwargs['parent_page'] = parent
        return kwargs

    class Meta:
        verbose_name = "Cours"

    parent_page_types = ['cours.CoursIndexPage']
    subpage_types = []
