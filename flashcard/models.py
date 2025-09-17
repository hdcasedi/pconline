# flashcard/models.py
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from wagtail.models import Page, Orderable
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.documents.models import Document
from wagtail.images import get_image_model
from wagtail.fields import RichTextField

from modelcluster.fields import ParentalKey

import csv
import hashlib
import io

Image = get_image_model()


# Utilitaire: calculer le hash SHA-256 d'un objet fichier sans altérer sa position
def _sha256_filelike(fobj) -> str:
    pos = None
    try:
        pos = fobj.tell()
    except Exception:
        pos = None
    try:
        try:
            fobj.seek(0)
        except Exception:
            pass
        h = hashlib.sha256()
        for chunk in iter(lambda: fobj.read(65536), b""):
            h.update(chunk)
        digest = h.hexdigest()
    finally:
        try:
            if pos is not None:
                fobj.seek(pos)
        except Exception:
            pass
    return digest


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

    source_file = models.ForeignKey(
        Document, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+',
        help_text="CSV (UTF-8 ; ou ,) avec entêtes question,answer[,tags,video_url] "
                  "ou TXT avec lignes 'question|||answer|||tags' (tags optionnel)."
    )
    import_strategy = models.CharField(
        max_length=10,
        choices=[('append', 'Ajouter'), ('replace', 'Remplacer tout')],
        default='append',
        help_text="Lors du prochain enregistrement, importer le fichier selon la stratégie."
    )
    auto_import_on_publish = models.BooleanField(
        default=True,
        help_text="Importer automatiquement à la publication."
    )
    last_import_checksum = models.CharField(max_length=64, blank=True, default="")
    last_import_document_id = models.PositiveIntegerField(null=True, blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('source_file'),
            FieldPanel('import_strategy'),
            FieldPanel('auto_import_on_publish'),
        ], heading="Import de fichier (CSV/TXT)"),
        InlinePanel('cards', label="Cartes"),
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
            
            # Diviser la ligne en parties (question, answer, tags optionnel)
            parts = line.split('|||')
            if len(parts) < 2:
                continue
                
            q = parts[0].strip()
            a = parts[1].strip()
            tags = parts[2].strip() if len(parts) > 2 else ''
            
            # Nettoyer les caractères spéciaux problématiques
            q = self._clean_text(q)
            a = self._clean_text(a)
            tags = self._clean_text(tags)
            
            self.cards.create(question=q, answer=a, tags=tags)
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
        # Plus de validation nécessaire

    def save(self, *args, **kwargs):
        # Plus d'import automatique - juste sauvegarder
        super().save(*args, **kwargs)

    # --- Parsing TXT/CSV normalisé ---
    def _parse_txt(self, text: str):
        """
        TXT attendu (UTF-8) :
          question|||answer
          question|||answer|||tags   (tags optionnel)
        """
        for raw in text.splitlines():
            line = (raw or "").strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|||")]
            if len(parts) < 2:
                # ligne invalide → on ignore
                continue
            yield {
                "question": parts[0],
                "answer": parts[1],
                "tags": parts[2] if len(parts) > 2 else "",
                "video_url": "",
            }

    def _parse_csv(self, bytes_content: bytes, encoding="utf-8"):
        """
        CSV attendu (UTF-8) avec séparateur **;** (point-virgule) et en-têtes :
          question;answer[;tags[;video_url]]
        Aucune auto-détection : on force le point-virgule.
        Robuste aux colonnes surnuméraires (clé None).
        """
        s = bytes_content.decode(encoding, errors="replace")
        # Enlève un éventuel BOM
        if s.startswith("\ufeff"):
            s = s.lstrip("\ufeff")

        buf = io.StringIO(s)

        # Dialecte forcé au point-virgule
        class SemiDialect(csv.excel):
            delimiter = ';'
        dialect = SemiDialect()

        reader = csv.DictReader(buf, dialect=dialect)

        # Normalise les headers (lower/strip) si présents
        if reader.fieldnames:
            reader.fieldnames = [(h or "").strip().lower() for h in reader.fieldnames]

        for raw_row in reader:
            # Normalisation sûre (évite l'erreur .strip() sur list/None)
            row = {}
            for k, v in raw_row.items():
                if k is None:   # colonnes en trop regroupées sous None → on ignore
                    continue
                key = (k or "").strip().lower()
                if isinstance(v, list):
                    v = " ".join(x for x in v if isinstance(x, str))
                elif v is None:
                    v = ""
                else:
                    v = str(v)
                row[key] = v.strip()

            q = row.get("question", "")
            a = row.get("answer", "")
            if not q and not a:
                continue

            yield {
                "question": q,
                "answer": a,
                "tags": row.get("tags", ""),
                "video_url": row.get("video_url", ""),
            }

    def _iter_rows(self, doc):
        """
        Sélection du parseur :
          - Si extension .txt → TXT '|||'
          - Si extension .csv → CSV ';'
          - Sinon : on regarde le contenu (priorité au '|||', sinon CSV ';')
        """
        name = (doc.title or doc.file.name).lower()
        data = doc.file.read()
        try:
            doc.file.seek(0)
        except Exception:
            pass

        if name.endswith(".txt"):
            text = data.decode("utf-8", errors="replace")
            yield from self._parse_txt(text)
            return

        if name.endswith(".csv"):
            yield from self._parse_csv(data)
            return

        # Fallback par contenu si l'extension est atypique
        head = data[:4096].decode("utf-8", errors="replace")
        if "|||" in head:
            text = head + data[4096:].decode("utf-8", errors="replace")
            yield from self._parse_txt(text)
        else:
            yield from self._parse_csv(data)

    def _current_doc_checksum(self):
        if not self.source_file:
            return None
        try:
            f = self.source_file.file
            return _sha256_filelike(f)
        except Exception:
            return None

    def delete_source_file(self):
        """Supprime le fichier du Document et détache la référence de la page."""
        doc = self.source_file
        if not doc:
            return
        try:
            storage = getattr(doc.file, 'storage', None)
            path = getattr(doc.file, 'name', None)
            if storage and path and storage.exists(path):
                storage.delete(path)
            # Supprimer l'objet Document (supprime aussi la DB)
            doc.delete()
        finally:
            self.source_file = None
            # Sauvegarder silencieusement la page mise à jour
            super().save(update_fields=['source_file'])

    @transaction.atomic
    def import_from_file(self):
        """Importe le fichier attaché (CSV/TXT) et crée des FlashcardItem. Retourne le nombre créé."""
        if not self.source_file:
            print("[FLASHCARD IMPORT] Aucun fichier source → 0 carte")
            return 0

        # Idempotence: si même checksum et même document, ne rien faire
        checksum = self._current_doc_checksum()
        if checksum and (self.last_import_checksum or "") == checksum and self.last_import_document_id == self.source_file_id:
            print("[FLASHCARD IMPORT] Déjà importé (checksum & document identiques) → 0 carte")
            return 0

        # Parser toutes les lignes
        rows = list(self._iter_rows(self.source_file))
        try:
            fname = self.source_file.file.name
        except Exception:
            fname = str(self.source_file_id)
        print(f"[FLASHCARD IMPORT] {len(rows)} lignes parsées depuis {fname}")
        if rows[:2]:
            print("[FLASHCARD IMPORT] Aperçu 2 premières:", rows[:2])

        if not rows:
            # Rien de valide → ne rien créer
            return 0

        # Stratégie : 'replace' = purge avant insert
        if getattr(self, 'import_strategy', 'append') == 'replace':
            self.cards.all().delete()

        # Création des cartes (bulk)
        created_objs = [
            FlashcardItem(
                page=self,
                question=r.get('question', ''),
                answer=r.get('answer', ''),
                tags=r.get('tags', ''),
                video_url=r.get('video_url', ''),
                is_active=True,
            )
            for r in rows
        ]
        created = len(created_objs)
        if created > 0:
            FlashcardItem.objects.bulk_create(created_objs)

        # Mettre à jour les marqueurs d'idempotence
        self.last_import_checksum = checksum or ""
        self.last_import_document_id = self.source_file_id
        super().save(update_fields=['last_import_checksum', 'last_import_document_id'])

        print(f"[FLASHCARD IMPORT] {created} cartes créées")
        return created
