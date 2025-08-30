# flashcard/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from wagtail.models import Page, Orderable
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.documents.models import Document
from wagtail.images import get_image_model
from wagtail.fields import RichTextField

from modelcluster.fields import ParentalKey

import csv
import io

Image = get_image_model()


class FlashcardItem(Orderable):  # <- héritage Orderable pour InlinePanel (tri + bouton +)
    """Une carte appartenant à un set."""
    page = ParentalKey(
        "flashcard.FlashcardSetPage",
        on_delete=models.CASCADE,
        related_name="cards"
    )

    question = RichTextField(
        features=['h2', 'h3', 'bold', 'italic', 'underline', 'link',
                  'superscript', 'subscript', 'strikethrough', 'ol',
                  'ul', 'hr', 'blockquote', 'code', 'image', 'embed'],
        blank=True
    )
    answer = RichTextField(
        features=['h2', 'h3', 'bold', 'italic', 'underline', 'link',
                  'superscript', 'subscript', 'strikethrough', 'ol',
                  'ul', 'hr', 'blockquote', 'code', 'image', 'embed'],
        blank=True
    )
    image = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    video_url = models.URLField(blank=True)
    tags = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    panels = [
        FieldPanel('is_active'),
        FieldPanel('question'),
        FieldPanel('answer'),
        FieldPanel('image'),
        FieldPanel('video_url'),
        FieldPanel('tags'),
    ]

    class Meta:
        ordering = ["sort_order", "id"]  # Orderable fournit sort_order


class FlashcardSetPage(Page):
    """
    Un paquet de flashcards, enfant direct d'une CoursPage (app 'cours').
    Hérite implicitement du Chapitre / Niveau via le parent.
    """
    template = "flashcard/flashcards_set_page.html"

    MODE_CHOICES = [
        ('manual', 'Saisie manuelle'),
        ('import', 'Import fichier (CSV / TXT)'),
    ]

    mode_creation = models.CharField(
        max_length=10, choices=MODE_CHOICES, default='manual'
    )
    source_file = models.ForeignKey(
        Document, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+',
        help_text="CSV (UTF-8 ; ou ,) avec entêtes question,answer[,tags,video_url] "
                  "ou TXT avec lignes 'question|||answer'."
    )
    import_strategy = models.CharField(
        max_length=10,
        choices=[('append', 'Ajouter'), ('replace', 'Remplacer tout')],
        default='append',
        help_text="Lors du prochain enregistrement, importer le fichier selon la stratégie."
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('mode_creation'),
            FieldPanel('source_file'),
            FieldPanel('import_strategy'),
        ], heading="Import (si mode import)"),
        InlinePanel('cards', label="Cartes (mode manuel)"),
    ]

    # Arborescence
    parent_page_types = ['cours.CoursPage']  # référence string -> pas d'import direct
    subpage_types = []

    @cached_property
    def parent_cours(self):
        try:
            return self.get_parent().specific
        except Exception:
            return None

    def _import_from_txt(self, raw_text: str):
        created = 0
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or '|||' not in line:
                continue
            q, a = line.split('|||', 1)
            self.cards.create(question=q.strip(), answer=a.strip())
            created += 1
        return created

    def _import_from_csv(self, raw_bytes: bytes):
        created = 0
        
        # Essayer différents encodages pour gérer les caractères spéciaux
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        text = None
        
        for encoding in encodings_to_try:
            try:
                text = raw_bytes.decode(encoding)
                print(f"Encodage réussi: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if text is None:
            # Fallback: utiliser utf-8 avec errors='replace' au lieu de 'ignore'
            text = raw_bytes.decode('utf-8', errors='replace')
            print("Encodage: utf-8 avec remplacement des caractères invalides")

        # Nettoyer les caractères problématiques
        text = text.replace('\ufeff', '')  # Supprimer BOM UTF-8
        
        # Sniffer sur un échantillon plus large (pas juste la 1re ligne)
        sample = "\n".join(text.splitlines()[:5]) or text
        try:
            dialect = csv.Sniffer().sniff(sample)
        except Exception:
            class Simple(csv.excel):
                delimiter = ','
            dialect = Simple

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        
        # Debug: afficher les en-têtes détectés
        print(f"En-têtes détectés: {reader.fieldnames}")

        for row_num, row in enumerate(reader, start=2):  # start=2 car ligne 1 = en-têtes
            q = (row.get('question') or '').strip()
            a = (row.get('answer') or '').strip()
            
            # Nettoyer les caractères spéciaux problématiques
            q = self._clean_text(q)
            a = self._clean_text(a)
            
            # Debug: afficher les valeurs pour les premières lignes
            if row_num <= 5:
                print(f"Ligne {row_num}: question='{q}', answer='{a}'")
                print(f"Ligne {row_num}: question (repr)='{repr(q)}', answer (repr)='{repr(a)}'")
            
            # Vérifier si les colonnes existent
            if 'question' not in row or 'answer' not in row:
                print(f"Erreur ligne {row_num}: colonnes 'question' ou 'answer' manquantes")
                print(f"Colonnes disponibles: {list(row.keys())}")
                continue
                
            # Ne pas ignorer si seule la question est vide (peut être une erreur de saisie)
            if not q and not a:
                print(f"Ligne {row_num} ignorée: question et answer vides")
                continue
                
            tags = (row.get('tags') or '').strip()
            video = (row.get('video_url') or '').strip()
            
            # Créer la carte même si la question est vide (pour debug)
            card = self.cards.create(question=q, answer=a, tags=tags, video_url=video)
            created += 1
            
            # Debug: vérifier que la carte a été créée
            if row_num <= 5:
                print(f"Carte créée: id={card.id}, question='{card.question}', answer='{card.answer}'")
                
        print(f"Total cartes créées: {created}")
        return created

    def _clean_text(self, text):
        """Nettoie le texte des caractères problématiques"""
        if not text:
            return text
            
        # Remplacer les caractères problématiques courants
        replacements = {
            '\u2019': "'",  # Apostrophe typographique droite
            '\u2018': "'",  # Apostrophe typographique gauche
            '\u201c': '"',  # Guillemet typographique gauche
            '\u201d': '"',  # Guillemet typographique droite
            '\u2013': '-',  # Tiret en
            '\u2014': '--', # Tiret em
            '\u2026': '...', # Points de suspension
            '\xa0': ' ',    # Espace insécable
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        return text

    def clean(self):
        super().clean()
        if self.mode_creation == 'import' and not self.source_file:
            raise ValidationError({'source_file': "Fichier requis en mode import."})

    def save(self, *args, **kwargs):
        do_import = (self.mode_creation == 'import' and self.source_file is not None)
        strategy = self.import_strategy
        super().save(*args, **kwargs)

        if do_import:
            f = self.source_file.file
            try:
                f.seek(0)
            except Exception:
                pass
            raw = f.read()
            created = 0
            if strategy == 'replace':
                # Supprimer les cartes existantes une par une pour éviter le problème avec FakeQuerySet
                for card in self.cards.all():
                    card.delete()

            name = (self.source_file.title or "").lower()
            if name.endswith('.txt'):
                created = self._import_from_txt(raw.decode('utf-8', errors='ignore'))
            else:
                created = self._import_from_csv(raw)

            # Après l'import, passer automatiquement en mode manuel et supprimer le fichier source
            self.mode_creation = 'manual'
            self.source_file = None
            self.import_strategy = 'append'  # Reset la stratégie
            # Sauvegarder sans déclencher un nouvel import
            super().save(update_fields=['mode_creation', 'source_file', 'import_strategy'])
