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
from flashcard.models import FlashcardSetPage, FlashcardItem
from types import SimpleNamespace
from wagtail.rich_text import RichText
import random


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
    fiche_methode = BooleanBlock(default=False, required=False, label="Afficher bouton fiche méthode")
    texte_bouton = CharBlock(default="Fiche méthode", required=False, label="Texte du bouton")

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


# === NEW: Section 2 colonnes (50/50, 67/33, 33/67) ===
from wagtail.blocks import StructBlock, ChoiceBlock, StreamBlock

class TwoColsBlock(StructBlock):
    ratio = ChoiceBlock(
        choices=[
            ("50-50", "50 / 50"),
            ("67-33", "67 / 33"),
            ("33-67", "33 / 67"),
        ],
        default="50-50",
        label="Disposition"
    )

    left = StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("tableau", TableBlock()),
            ("code", CodeBlock()),
        ],
        required=False,
        label="Colonne gauche"
    )
    right = StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("tableau", TableBlock()),
            ("code", CodeBlock()),
        ],
        required=False,
        label="Colonne droite"
    )

    class Meta:
        template = "cours/blocks/section_two_cols.html"
        icon = "placeholder"
        label = "Section 2 colonnes"


# === NEW: Section 3 colonnes (33/33/33) ===
class ThreeColsBlock(StructBlock):
    col1 = StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("tableau", TableBlock()),
            ("code", CodeBlock()),
        ],
        required=False,
        label="Colonne 1"
    )
    col2 = StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("tableau", TableBlock()),
            ("code", CodeBlock()),
        ],
        required=False,
        label="Colonne 2"
    )
    col3 = StreamBlock(
        [
            ("paragraphe", ParagrapheBlock()),
            ("titre", TitreBlock()),
            ("tableau", TableBlock()),
            ("code", CodeBlock()),
        ],
        required=False,
        label="Colonne 3"
    )

    class Meta:
        template = "cours/blocks/section_three_cols.html"
        icon = "placeholder"
        label = "Section 3 colonnes"


# --- add near other block classes ---
from wagtail.blocks import StructBlock, CharBlock, RichTextBlock

class FormulaireBlock(StructBlock):
    # Ligne 1 : 100% rich text
    ligne1 = RichTextBlock(
        features=['h2','h3','bold','italic','underline','link','superscript','subscript',
                  'strikethrough','ol','ul','hr','blockquote','code','image','embed'],
        label="Ligne 1 (texte riche plein largeur)"
    )
    # Ligne 2 (33%) : formule TeX (MathJax), centrée H/V
    formule = CharBlock(
        required=True,
        label="Formule (TeX / MathJax, sans délimiteurs)",
        help_text=r"Ex: E = mc^2  (les délimiteurs $$...$$ seront ajoutés au rendu)"
    )
    # Ligne 2 (67%) : liste rich text
    liste = RichTextBlock(
        features=['bold','italic','underline','link','ol','ul','hr','blockquote','code','image','embed'],
        label="Liste (texte riche)"
    )

    class Meta:
        template = "cours/blocks/formulaire.html"
        icon = "form"
        label = "Formulaire"


class CoursContentBlock(StreamBlock):
    paragraphe = ParagrapheBlock()
    titre = TitreBlock()
    tableau = TableBlock(template='cours/blocks/tableau.html')
    code = CodeBlock()
    # NEW:
    section_2cols = TwoColsBlock()
    section_3cols = ThreeColsBlock()
    formulaire = FormulaireBlock()


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
    subpage_types = [
        'flashcard.FlashcardSetPage',   # déjà présent
        'qcm.QcmQuestionAPage',         # Type A (multi-propositions)
        'qcm.QcmBankBPage',             # Type B (banque de variantes)
        'qcm.QcmQuestionCPage',         # Type C (listes de réponses)
    ]

    def all_flashcards_qs(self):
        """Toutes les cartes actives de tous les sets enfants de ce cours."""
        set_ids = self.get_children().type(FlashcardSetPage).values_list('id', flat=True)
        return FlashcardItem.objects.filter(page_id__in=set_ids, is_active=True)

    def random_flashcards(self, limit=10):
        """Un échantillon au hasard (sans ORDER BY ?) efficace."""
        ids = list(self.all_flashcards_qs().values_list('id', flat=True))
        random.shuffle(ids)
        return FlashcardItem.objects.filter(id__in=ids[:limit])

    def definition_flashcards(self):
        """
        Extrait du StreamField toutes les définitions (ParagrapheBlock style='definition')
        et les expose comme 'pseudo-cartes' compatibles avec le rendu des flashcards.
        """
        cards = []
        for block in self.contenu:  # StreamField
            if block.block_type == 'paragraphe':
                v = block.value  # StructValue
                try:
                    if v.get('style') == 'definition':
                        titre = v.get('titre') or "Définition"
                        contenu = v.get('contenu')  # RichText (Wagtail)
                        # On construit un objet simple avec les mêmes attr que FlashcardItem
                        cards.append(SimpleNamespace(
                            is_virtual=True,
                            question=RichText(f"<strong>{titre}</strong>"),
                            answer=contenu,
                            image=None,
                            video_url="",
                            tags="definition"
                        ))
                except Exception:
                    continue
        return cards

    def random_cards_with_definitions(self, limit=10):
        """
        Mélange flashcards DB + définitions du cours et renvoie 'limit' cartes.
        """
        pool = list(self.all_flashcards_qs()) + self.definition_flashcards()
        random.shuffle(pool)
        return pool[:limit]

    def random_cards10(self):
        """
        Wrapper sans argument pour les templates :
        - si random_cards_with_definitions existe => 10 cartes mélangées (flashcards + définitions)
        - sinon fallback => 10 flashcards DB
        """
        if hasattr(self, "random_cards_with_definitions"):
            try:
                return self.random_cards_with_definitions(limit=10)
            except TypeError:
                # au cas où la signature ne prend pas 'limit'
                return self.random_cards_with_definitions()
        # Fallback si pas de méthode avancée
        if hasattr(self, "all_flashcards_qs"):
            return self.all_flashcards_qs()[:10]
        return []

    def get_context(self, request):
        ctx = super().get_context(request)

        # On tente d'importer l'app QCM. Si non installée: on passe.
        try:
            from qcm.models import QcmQuestionAPage, QcmBankBPage, QcmQuestionCPage
        except Exception:
            ctx["qcm_set"] = []
            return ctx

        # Par défaut, on ne génère que les QCM sans rédaction
        # Mais on peut accepter un paramètre pour inclure les QCM avec rédaction
        include_justification = request.GET.get('justification', 'false').lower() == 'true'

        # Récupérer les enfants (publiés) de la CoursPage
        children = self.get_children().live().specific()

        # ---- TYPE A : une question = 4 options (1 correcte + 3 distracteurs) ----
        qcm_a = [c for c in children if isinstance(c, QcmQuestionAPage)]
        payload_a = []
        for q in qcm_a:
            # Filtrer selon le paramètre sans_redaction
            if not q.sans_redaction and not include_justification:
                continue
                
            opts = list(q.options.all())
            if len(opts) < 4:
                continue  # on exige 4 propositions min
            corrects = [o for o in opts if o.is_correct]
            incorrects = [o for o in opts if not o.is_correct]
            if not corrects:
                continue

            correct = random.choice(corrects)
            # 3 distracteurs si possible, sinon on saute
            if len(incorrects) < 3:
                continue
            distractors = random.sample(incorrects, 3)

            # pool final et shuffle
            final_opts = [{"html": o.text, "is_correct": (o == correct)} for o in [correct, *distractors]]
            random.shuffle(final_opts)

            payload_a.append({
                "type": "A",
                "statement": q.statement,
                "image": q.image,  # Ajouter l'image
                "options": final_opts,
                "explanation": getattr(q, "explanation", ""),
            })

        # ---- TYPE B : piocher 1 variante correcte + 3 distracteurs dans la même banque ----
        qcm_banks = [c for c in children if isinstance(c, QcmBankBPage)]
        payload_b = []
        for bank in qcm_banks:
            # Filtrer selon le paramètre sans_redaction
            if not bank.sans_redaction and not include_justification:
                continue
                
            variants = list(bank.variants.all())
            if len(variants) < 4:
                continue
            correct_var = random.choice(variants)
            other_vars = [v for v in variants if v != correct_var]
            distractors = random.sample(other_vars, 3)

            # Construire options : 1 correcte (answer de correct_var) + 3 distracteurs (answers d'autres variantes)
            opts = [{"html": correct_var.answer, "is_correct": True}]
            for d in distractors:
                opts.append({"html": d.answer, "is_correct": False})
            random.shuffle(opts)

            payload_b.append({
                "type": "B",
                "statement": correct_var.statement,
                "options": opts,
                "explanation": "",  # Pas d'explication au niveau des variantes
            })

        # ---- TYPE C : 1 bonne réponse + 3 mauvaises réponses depuis les listes ----
        qcm_c = [c for c in children if isinstance(c, QcmQuestionCPage)]
        payload_c = []
        for q in qcm_c:
            # Filtrer selon le paramètre sans_redaction
            if not q.sans_redaction and not include_justification:
                continue
                
            correct_answers = q.get_correct_answers_list()
            incorrect_answers = q.get_incorrect_answers_list()
            
            if len(correct_answers) < 1 or len(incorrect_answers) < 3:
                continue  # on exige au moins 1 bonne réponse et 3 mauvaises
            
            # Choisir 1 bonne réponse au hasard
            correct = random.choice(correct_answers)
            # Choisir 3 mauvaises réponses au hasard
            distractors = random.sample(incorrect_answers, 3)
            
            # Construire les options
            opts = [{"html": correct, "is_correct": True}]
            for d in distractors:
                opts.append({"html": d, "is_correct": False})
            random.shuffle(opts)
            
            payload_c.append({
                "type": "C",
                "statement": q.statement,
                "image": q.image,  # Ajouter l'image
                "options": opts,
                "explanation": getattr(q, "explanation", ""),
            })

        # Mélange global + limite 10
        all_q = payload_a + payload_b + payload_c
        random.shuffle(all_q)
        ctx["qcm_set"] = all_q[:10]

        return ctx
