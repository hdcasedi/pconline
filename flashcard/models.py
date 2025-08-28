# flashcard/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from wagtail.models import Page
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.documents.models import Document
from wagtail.images import get_image_model
from wagtail.fields import RichTextField

from modelcluster.fields import ParentalKey

import csv
import io

Image = get_image_model()


class FlashcardItem(models.Model):
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
    sort_order = models.IntegerField(default=0)

    panels = [
        FieldPanel('question'),
        FieldPanel('answer'),
        FieldPanel('image'),
        FieldPanel('video_url'),
        FieldPanel('tags'),
        FieldPanel('is_active'),
    ]

    class Meta:
        ordering = ["sort_order", "id"]


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
        text = raw_bytes.decode('utf-8', errors='ignore')
        # détection simple ; sinon fallback à ,
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(text.splitlines()[0])
        except Exception:
            class Simple(dialect:=csv.excel):  # noqa
                delimiter = ','
            dialect = Simple
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)

        for row in reader:
            q = (row.get('question') or '').strip()
            a = (row.get('answer') or '').strip()
            if not q and not a:
                continue
            tags = (row.get('tags') or '').strip()
            video = (row.get('video_url') or '').strip()
            self.cards.create(question=q, answer=a, tags=tags, video_url=video)
            created += 1
        return created

    def clean(self):
        super().clean()
        if self.mode_creation == 'import' and not self.source_file:
            raise ValidationError({'source_file': "Fichier requis en mode import."})

    def save(self, *args, **kwargs):
        do_import = (self.mode_creation == 'import' and self.source_file is not None)
        strategy = self.import_strategy
        super().save(*args, **kwargs)

        if do_import:
            # Relire depuis le début
            f = self.source_file.file
            try:
                f.seek(0)
            except Exception:
                pass
            raw = f.read()
            created = 0
            if strategy == 'replace':
                self.cards.all().delete()

            name = (self.source_file.title or "").lower()
            if name.endswith('.txt'):
                created = self._import_from_txt(raw.decode('utf-8', errors='ignore'))
            else:
                created = self._import_from_csv(raw)

            # Reset strategy pour éviter les ré-imports involontaires au prochain save
            FlashcardSetPage.objects.filter(pk=self.pk).update(import_strategy='append')
