from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.models import Page
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.images import get_image_model

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.models import Orderable

Image = get_image_model()


# ============ Type A ============

class QcmQuestionAOption(Orderable):
    page = ParentalKey("qcm.QcmQuestionAPage", on_delete=models.CASCADE, related_name="options")
    text = RichTextField(
        features=['bold', 'italic', 'underline', 'link', 'superscript', 'subscript',
                  'strikethrough', 'ol', 'ul', 'code'],
        blank=False
    )
    is_correct = models.BooleanField(default=False)

    panels = [
        FieldPanel("text"),
        FieldPanel("is_correct"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Proposition"
        verbose_name_plural = "Propositions"


class QcmQuestionAPage(Page):
    """
    Question MCQ complète.
    Enfant direct de cours.CoursPage.
    """
    template = "qcm/qcm_question_a_page.html"
    LAYOUT_CHOICES = [
        ("text", "100% texte"),
        ("text_media", "67% texte / 33% média"),
    ]
    layout = models.CharField(max_length=16, choices=LAYOUT_CHOICES, default="text")

    statement = RichTextField(
        features=['h2','h3','bold','italic','underline','link','superscript','subscript',
                  'strikethrough','ol','ul','hr','blockquote','code','image','embed'],
        help_text="Énoncé (MathJax OK)."
    )
    image = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    video_url = models.URLField(blank=True)

    sans_redaction = models.BooleanField(
        default=True, help_text="QCM sans rédaction (cochez pour QCM simple, décochez pour QCM avec justification écrite)"
    )
    explanation = RichTextField(
        features=['bold','italic','underline','link','ol','ul','code'],
        blank=True, help_text="Explication globale (optionnel)."
    )

    parent_page_types = ['cours.CoursPage']
    subpage_types = []

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("layout"),
            FieldPanel("statement"),
            FieldPanel("image"),
            FieldPanel("video_url"),
        ], heading="Énoncé"),
        InlinePanel("options", label="Propositions (≥4, max 100)"),
        MultiFieldPanel([
            FieldPanel("sans_redaction"),
            FieldPanel("explanation"),
        ], heading="Réglages & Explication"),
    ]

    def clean(self):
        super().clean()
        # garde-fous minimum
        if self.options.count() < 1 and self.pk:
            # On laisse la contrainte "≥4" à l'éditeur (message UX),
            # pas d'exception dure ici pour ne pas bloquer les brouillons.
            pass


# ============ Type B ============

class QcmVariantB(Orderable):
    """
    Une variante (question + bonne réponse + explication) appartenant à une page banque.
    Les distracteurs seront tirés parmi les autres variantes de la même page.
    """
    LAYOUT_CHOICES = [
        ("text", "100% texte"),
        ("text_media", "67% texte / 33% média"),
    ]
    page = ParentalKey("qcm.QcmBankBPage", on_delete=models.CASCADE, related_name="variants")

    layout = models.CharField(max_length=16, choices=LAYOUT_CHOICES, default="text")
    statement = RichTextField(
        features=['h2','h3','bold','italic','underline','link','superscript','subscript',
                  'strikethrough','ol','ul','hr','blockquote','code','image','embed'],
        help_text="Énoncé (MathJax OK)."
    )
    answer = RichTextField(
        features=['bold','italic','underline','link','superscript','subscript','ol','ul','code'],
        help_text="Réponse correcte."
    )
    image = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    video_url = models.URLField(blank=True)

    panels = [
        FieldPanel("layout"),
        FieldPanel("statement"),
        FieldPanel("answer"),
        FieldPanel("image"),
        FieldPanel("video_url"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Variante"
        verbose_name_plural = "Variantes"


class QcmBankBPage(Page):
    """
    Banque de variantes (Type B).
    Une seule page peut contenir un grand nombre de variantes.
    À l'affichage, on choisit 1 variante comme correcte et on pioche 3 distracteurs
    dans les autres variantes de la même page.
    """
    template = "qcm/qcm_question_b_page.html"
    
    sans_redaction = models.BooleanField(
        default=True, help_text="QCM sans rédaction (cochez pour QCM simple, décochez pour QCM avec justification écrite)"
    )
    
    parent_page_types = ['cours.CoursPage']
    subpage_types = []

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("sans_redaction"),
        ], heading="Réglages"),
        InlinePanel("variants", label="Variantes (questions + réponses)"),
    ]


# ============ Type C ============

class QcmQuestionCPage(Page):
    """
    Question MCQ avec listes de bonnes et mauvaises réponses (Type C).
    Les bonnes réponses sont séparées par ';' et les mauvaises réponses par ';'.
    À la génération, on choisit 1 bonne réponse et 3 mauvaises réponses.
    """
    template = "qcm/qcm_question_c_page.html"
    LAYOUT_CHOICES = [
        ("text", "100% texte"),
        ("text_media", "67% texte / 33% média"),
    ]
    layout = models.CharField(max_length=16, choices=LAYOUT_CHOICES, default="text")

    statement = RichTextField(
        features=['h2','h3','bold','italic','underline','link','superscript','subscript',
                  'strikethrough','ol','ul','hr','blockquote','code','image','embed'],
        help_text="Énoncé (MathJax OK)."
    )
    image = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    video_url = models.URLField(blank=True)

    correct_answers = models.TextField(
        help_text="Liste des bonnes réponses séparées par ';' (texte et/ou LaTeX/MathJax)"
    )
    incorrect_answers = models.TextField(
        help_text="Liste des mauvaises réponses séparées par ';' (texte et/ou LaTeX/MathJax)"
    )

    sans_redaction = models.BooleanField(
        default=True, help_text="QCM sans rédaction (cochez pour QCM simple, décochez pour QCM avec justification écrite)"
    )
    explanation = RichTextField(
        features=['bold','italic','underline','link','ol','ul','code'],
        blank=True, help_text="Explication globale (optionnel)."
    )

    parent_page_types = ['cours.CoursPage']
    subpage_types = []

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("layout"),
            FieldPanel("statement"),
            FieldPanel("image"),
            FieldPanel("video_url"),
        ], heading="Énoncé"),
        MultiFieldPanel([
            FieldPanel("correct_answers"),
            FieldPanel("incorrect_answers"),
        ], heading="Réponses"),
        MultiFieldPanel([
            FieldPanel("sans_redaction"),
            FieldPanel("explanation"),
        ], heading="Réglages & Explication"),
    ]

    def clean(self):
        super().clean()
        # Validation des listes de réponses
        if self.correct_answers:
            correct_list = [r.strip() for r in self.correct_answers.split(';') if r.strip()]
            if len(correct_list) < 1:
                raise models.ValidationError({
                    'correct_answers': "Au moins une bonne réponse est requise."
                })
        
        if self.incorrect_answers:
            incorrect_list = [r.strip() for r in self.incorrect_answers.split(';') if r.strip()]
            if len(incorrect_list) < 3:
                raise models.ValidationError({
                    'incorrect_answers': "Au moins 3 mauvaises réponses sont requises pour générer les distracteurs."
                })

    def get_correct_answers_list(self):
        """Retourne la liste des bonnes réponses nettoyées"""
        if not self.correct_answers:
            return []
        return [r.strip() for r in self.correct_answers.split(';') if r.strip()]

    def get_incorrect_answers_list(self):
        """Retourne la liste des mauvaises réponses nettoyées"""
        if not self.incorrect_answers:
            return []
        return [r.strip() for r in self.incorrect_answers.split(';') if r.strip()]
