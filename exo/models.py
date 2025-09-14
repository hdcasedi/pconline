from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel, FieldRowPanel
from wagtail.search import index
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import TagBase, TaggedItemBase
from taggit.managers import TaggableManager
from wagtail.images.models import Image
from .blocks import EnonceBlock, Section100Block, Section50_50Block, Section70_30Block, Section75_25Block, QuestionBlock
import json
import re
from typing import Optional, Dict, Any, Set
import math
import random
def format_range_values(min_val, max_val, step):
    """Génère les valeurs entre min et max avec la précision de step."""
    if step is None or step == 0:
        return []
    step_str = f"{step}"
    if "." in step_str:
        ndec = len(step_str.split(".")[1].rstrip("0"))
    else:
        ndec = 0
    values = []
    current = float(min_val)
    while current <= float(max_val) + 1e-9:  # marge flottant
        values.append(f"{current:.{ndec}f}")
        current += float(step)
    return values


class ExoHubPage(Page):
    """Page hub pour organiser les exercices sous une CoursPage"""
    template = "exo/hub.html"
    
    class Meta:
        verbose_name = "Hub des exercices"
        verbose_name_plural = "Hubs des exercices"

    parent_page_types = ['cours.CoursPage']
    subpage_types = ['exo.ExoPageSimple']


class ExoPageSimpleTag(TaggedItemBase):
    """Tag pour les exercices"""
    content_object = ParentalKey(
        'ExoPageSimple',
        related_name='tagged_items',
        on_delete=models.CASCADE,
    )


class ExoPageSimple(Page):
    """Page d'exercice simple avec sections et questions"""
    template = "exo/page_simple.html"
    
    # Métadonnées éditoriales
    difficulty = models.PositiveSmallIntegerField(
        choices=[(1, "1"), (2, "2"), (3, "3")],
        default=2,
        verbose_name="Difficulté"
    )
    
    estimated_time_min = models.PositiveIntegerField(
        default=10,
        verbose_name="Temps estimé (minutes)"
    )
    
    total_points = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total des points"
    )
    
    family_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="ID de famille"
    )
    
    # Contenu flexible : énoncé et questions mélangés
    contenu = StreamField([
        ("enonce", EnonceBlock()),
        ("s100", Section100Block()),
        ("s50_50", Section50_50Block()),
        ("s70_30", Section70_30Block()),
        ("s75_25", Section75_25Block()),
        ("question", QuestionBlock()),
    ], use_json_field=True, blank=True, verbose_name="Contenu de l'exercice")
    
    # Tags
    tags = TaggableManager(
        through=ExoPageSimpleTag,
        blank=True,
        verbose_name="Tags"
    )
    
    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('difficulty'),
            FieldPanel('estimated_time_min'),
            FieldPanel('total_points'),
            FieldPanel('family_id'),
            FieldPanel('tags'),
        ], heading="Métadonnées"),
        FieldPanel('contenu', heading="Contenu de l'exercice"),
    ]
    
    class Meta:
        verbose_name = "Exercice simple"
        verbose_name_plural = "Exercices simples"

    parent_page_types = ['exo.ExoHubPage']
    subpage_types = ['exo.ParametreExoPage']

    search_fields = Page.search_fields + [
        index.SearchField('contenu'),
        index.FilterField('difficulty'),
    ]

    def get_points_sum(self):
        """Calcule la somme des points des questions"""
        total = Decimal('0.00')
        if self.contenu:
            for block in self.contenu:
                if block.block_type == 'question':
                    total += block.value.get('points', Decimal('0.00'))
        return total
    
    def has_fc(self):
        """Vérifie s'il y a au moins une question Flashcard"""
        if self.contenu:
            for block in self.contenu:
                if block.block_type == 'question' and block.value.get('fc'):
                    return True
        return False
    
    def get_context(self, request, *args, **kwargs):
        """Ajoute des variables au contexte"""
        context = super().get_context(request, *args, **kwargs)
        context['points_sum'] = self.get_points_sum()
        context['has_fc'] = self.has_fc()
        # Injecter un contexte aléatoire depuis la page enfant ParametreExoPage si présente
        try:
            params_page = self.get_children().type(ParametreExoPage).specific().first()
        except Exception:
            params_page = None
        if params_page:
            # Optionnel: seed depuis la querystring ?seed=
            seed = request.GET.get('seed') if request else None
            print(f"DEBUG: Tentative génération paramètres pour page {self.id}, seed={seed}")
            try:
                param_context = params_page.build_random_context(seed=seed)
                print(f"DEBUG: Contexte généré pour page {self.id}: {param_context}")
            except Exception as e:
                # Log l'erreur pour le debugging
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"Erreur génération paramètres pour page {self.id}: {e}")
                print(f"DEBUG: Erreur paramètres page {self.id}: {e}")
                print(f"DEBUG: Traceback: {traceback.format_exc()}")
                param_context = {}
            context['param_values'] = param_context
        else:
            context['param_values'] = {}
        return context
    
    def clean(self):
        """Validation : vérifier la cohérence des points"""
        super().clean()
        points_sum = self.get_points_sum()
        if points_sum != self.total_points:
            # Ajouter un warning mais ne pas bloquer
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"Attention : la somme des points ({points_sum}) ne correspond pas au total saisi ({self.total_points})"
            )


class ParamImageEntry(ClusterableModel):
    """Entrée d'image pour un paramètre de type image"""
    param_item = ParentalKey(
        'ParamItem',
        on_delete=models.CASCADE,
        related_name='image_entries'
    )
    
    image = models.ForeignKey(
        Image,
        on_delete=models.CASCADE,
        verbose_name="Image"
    )
    
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Légende"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordre"
    )
    
    panels = [
        FieldPanel('image'),
        FieldPanel('caption'),
        FieldPanel('order'),
    ]
    
    class Meta:
        verbose_name = "Entrée d'image"
        verbose_name_plural = "Entrées d'images"
        ordering = ['order']


class ParametreExoPage(Page):
    """Page de paramétrage pour un exercice parent"""
    template = "exo/parametre_exo_page.html"

    # Champs visibles
    notes = models.TextField(
        blank=True,
        verbose_name="Notes internes"
    )
    
    content_panels = Page.content_panels + [
            FieldPanel('notes'),
        InlinePanel('param_items', heading="Paramètres"),
    ]
    
    class Meta:
        verbose_name = "Page de paramétrage d'exercice"
        verbose_name_plural = "Pages de paramétrage d'exercices"

    parent_page_types = ['exo.ExoPageSimple']
    subpage_types = []

    def compute_sync_K(self) -> Optional[int]:
        """
        Déduit automatiquement K depuis les paramètres synchronisés
        
        Returns:
            K déduit ou None si aucun paramètre synchronisé avec série
        """
        sync_params = self.param_items.filter(sync_enabled=True)
        if not sync_params.exists():
            return None
        
        first_K = None
        
        for param in sync_params:
            count = self._get_param_series_count(param)
            if count is not None:
                if first_K is None:
                    first_K = count
                elif count != first_K:
                    # Incohérence détectée
                    return None
        
        return first_K
    
    def _get_param_series_count(self, param) -> Optional[int]:
        """
        Calcule le nombre d'entrées dans la série d'un paramètre
        
        Args:
            param: ParamItem
            
        Returns:
            Nombre d'entrées ou None si pas de série
        """
        if param.kind == 'const':
            return None  # Compatible avec n'importe quel K
        elif param.kind == 'expr':
            return None  # Se déduit au runtime
        elif param.kind == 'range':
            if param.range_min is not None and param.range_max is not None and param.range_step is not None:
                if param.range_step > 0:
                    vals = format_range_values(param.range_min, param.range_max, param.range_step)
                    return len(vals)
            return None
        elif param.kind == 'set':
            if param.set_text:
                items = parse_set_items(param.set_text)
                return len(items)
            return None
        elif param.kind == 'slot':
            # Les slots participent au K via le nombre de variantes (0 si aucune)
            return param.sync_entries.count()
        elif param.kind == 'image':
            return param.image_entries.count()
        
        return None
    
    def validate_sync_coherence(self) -> list[str]:
        """
        Valide la cohérence des paramètres synchronisés
        
        Returns:
            Liste des erreurs de validation
        """
        errors = []
        K = self.compute_sync_K()
        
        if K is None:
            return errors
        
        sync_params = self.param_items.filter(sync_enabled=True)
        
        for param in sync_params:
            count = self._get_param_series_count(param)
            if count is not None and count != K:
                errors.append(
                    f"Le paramètre '{param.name}' ({param.get_kind_display()}) "
                    f"a {count} entrées mais K={K} est attendu"
                )
        
        return errors

    def gather_parent_text(self) -> str:
        """
        Concatène le contenu pertinent de la page mère (StreamField : énoncé, sections, questions, solutions, légendes d'images).
        
        Returns:
            Contenu textuel complet à scanner
        """
        parent = self.get_parent()
        if not isinstance(parent, ExoPageSimple):
            return ""
        
        content_parts = []
        
        # Parcourir le StreamField contenu
        if parent.contenu:
            for block in parent.contenu:
                if block.block_type == 'enonce':
                    if hasattr(block.value, 'content'):
                        content_parts.append(str(block.value.content))
                elif block.block_type in ['s100', 's50_50', 's70_30']:
                    if hasattr(block.value, 'content'):
                        content_parts.append(str(block.value.content))
                    elif hasattr(block.value, 'left') and hasattr(block.value, 'right'):
                        content_parts.append(str(block.value.left))
                        content_parts.append(str(block.value.right))
                elif block.block_type == 'question':
                    if hasattr(block.value, 'content'):
                        content_parts.append(str(block.value.content))
                    if hasattr(block.value, 'solution'):
                        content_parts.append(str(block.value.solution))

        return "\n".join(content_parts)

    def autoscan_create_missing(self) -> dict:
        """
        Scanne automatiquement l'exercice parent et crée les paramètres manquants.
        
        Returns:
            Dictionnaire avec le récapitulatif (ajoutés, mis à jour, orphelins)
        """
        from .utils.param_scan import find_value_params, find_slot_params, find_image_params
        
        # Récupérer le contenu textuel
        text = self.gather_parent_text()
        
        # Détecter tous les paramètres
        value_params = find_value_params(text)
        slot_params = find_slot_params(text)
        image_params = find_image_params(text)
        
        # Récupérer tous les noms détectés
        detected_names = set()
        detected_names.update(value_params)
        detected_names.update(slot_params.keys())
        detected_names.update(image_params)
        
        # Récupérer les paramètres existants
        existing_params = {param.name: param for param in self.param_items.all()}
        
        added_count = 0
        updated_count = 0
        orphaned_count = 0
        
        # Créer les nouveaux paramètres
        for name in detected_names:
            if name not in existing_params:
                # Inférer le type
                if name in slot_params:
                    kind = 'slot'
                elif name in image_params:
                    kind = 'image'
                else:
                    kind = 'const'  # Valeurs par défaut
                
                param_item = ParamItem(
                    page=self,
                    name=name,
                    kind=kind,
                    is_orphaned=False
                )
                
                # Préremplir le slot_default si c'est un slot
                if kind == 'slot' and name in slot_params:
                    param_item.slot_default = slot_params[name]
                
                param_item.save()
                added_count += 1
            else:
                # Marquer comme non orphelin
                param = existing_params[name]
                if param.is_orphaned:
                    param.is_orphaned = False
                    param.save()
                    updated_count += 1
        
        # Marquer comme orphelins les paramètres non retrouvés
        for name, param in existing_params.items():
            if name not in detected_names and not param.is_orphaned:
                param.is_orphaned = True
                param.save()
                orphaned_count += 1
        
        return {
            'added': added_count,
            'updated': updated_count,
            'orphaned': orphaned_count,
            'total_detected': len(detected_names),
            'total_existing': len(existing_params)
        }

    def first_save_autoscan(self):
        """
        Hook pour lancer l'auto-scan au premier save de la page
        (si aucun ParamItem encore présent)
        """
        if self.param_items.count() == 0:
            self.autoscan_create_missing()

    def save(self, *args, **kwargs):
        """Scan auto à chaque enregistrement pour créer/mettre à jour les ParamItem."""
        super().save(*args, **kwargs)
        try:
            self.autoscan_create_missing()
        except Exception:
            # on ne bloque pas l'enregistrement si le scan échoue
            pass

    def scan_from_parent(self):
        """
        Scanne l'exercice parent et détecte automatiquement les paramètres
        (Méthode legacy - utilise maintenant autoscan_create_missing)
        """
        return self.autoscan_create_missing()

    def validate_sync_lengths(self):
        """
        Vérifie que tous les paramètres synchronisés ont K entrées
        TODO: Implémenter la validation
        """
        errors = []
        for param in self.param_items.all():
            if param.sync_enabled and param.kind != 'const':
                # TODO: Vérifier que param a exactement sync_variant_count entrées
                pass
        return errors

    def build_context_for_variant(self, index: int, seed: Optional[str] = None) -> Dict[str, Any]:
        """
        Construit le contexte synchronisé pour une variante donnée (index 1..K).
        - Pour chaque paramètre sync_enabled avec une série, on prend l'entrée d'indice 'index'.
        - Pour les paramètres sans série (const/expr), on prend la valeur directe.
        - Pour les non synchronisés, on tire au hasard (avec seed si fournie).
        """
        context: Dict[str, Any] = {}
        rng = random.Random(seed)

        def series_values(p: "ParamItem"):
            # Retourne une liste ordonnée de valeurs pour la série du paramètre
            print(f"DEBUG: series_values pour paramètre {p.name} (type: {p.kind})")
            if p.kind == 'range':
                if p.range_min is None or p.range_max is None or p.range_step is None or p.range_step <= 0:
                    return []
                # Génère des chaînes déjà formatées selon la précision de step
                return format_range_values(p.range_min, p.range_max, p.range_step)
            elif p.kind == 'set':
                return parse_set_items(p.set_text or '')
            elif p.kind == 'image':
                # Logique originale : utiliser image_entries pour tous les paramètres d'images
                return [e.image_id for e in p.image_entries.all() if e.image_id]
            elif p.kind == 'slot':
                # Liste des variantes richtext
                return [str(e.value_richtext or '') for e in p.sync_entries.all()]
            elif p.kind == 'tableau':
                # Pour les tableaux, on retourne toujours la même structure
                # (pas de variantes synchronisées pour l'instant)
                return [{
                    'orientation': p.tableau_orientation,
                    'header': p.tableau_header,
                    'rows': p.tableau_rows.split('\n') if p.tableau_rows else []
                }]
            else:
                return []

        # Première passe: valeurs pour tous sauf expr (qui dépend des autres)
        for param in self.param_items.all():
            name = param.name
            if param.sync_enabled:
                values = series_values(param)
                if values:
                    # index est 1..K, accéder à l'entrée correspondante (modulo par sécurité)
                    sel = values[(index - 1) % len(values)]
                    context[name] = sel
                else:
                    # Const / expr / slot sans variantes
                    if param.kind == 'const':
                        context[name] = param.const_value
                    elif param.kind == 'expr':
                        # calculé en deuxième passe
                        context[name] = None
                    elif param.kind == 'slot':
                        # Pas de défaut: vide si aucune variante
                        context[name] = ''
                    elif param.kind == 'tableau':
                        # Retourner la structure complète du tableau
                        context[name] = {
                            'orientation': param.tableau_orientation,
                            'header': param.tableau_header,
                            'rows': param.tableau_rows.split('\n') if param.tableau_rows else []
                        }
                    else:
                        # range/set/image mal configurés
                        context[name] = None
            else:
                # Non synchronisé: tirer au hasard
                if param.kind == 'const':
                    context[name] = param.const_value
                elif param.kind == 'expr':
                    context[name] = None  # calculé en deuxième passe
                elif param.kind == 'range':
                    vals = series_values(param)
                    context[name] = rng.choice(vals) if vals else None
                elif param.kind == 'set':
                    vals = series_values(param)
                    context[name] = rng.choice(vals) if vals else None
                elif param.kind == 'image':
                    vals = series_values(param)
                    context[name] = rng.choice(vals) if vals else None
                elif param.kind == 'slot':
                    vals = series_values(param)
                    context[name] = rng.choice(vals) if vals else ''
                elif param.kind == 'tableau':
                    # Pour les tableaux non synchronisés, on retourne toujours la même structure
                    context[name] = {
                        'orientation': param.tableau_orientation,
                        'header': param.tableau_header,
                        'rows': param.tableau_rows.split('\n') if param.tableau_rows else []
                    }
                else:
                    context[name] = None

        # Deuxième passe: évaluer les expressions en se basant sur le contexte
        param_exprs = [p for p in self.param_items.all() if p.kind == 'expr']
        if param_exprs:
            # Remplacer [[name]] dans expr_code puis essayer d'évaluer
            import re as _re
            placeholder = _re.compile(r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
            # Préparer environnement numérique
            num_env: Dict[str, float] = {}
            for k, v in context.items():
                try:
                    if v is not None and v != '':
                        num_env[k] = float(v)
                except Exception:
                    pass
            safe_globals = {'__builtins__': {}}
            safe_locals = {'math': math, **num_env}
            for p in param_exprs:
                expr = p.expr_code or ''
                def repl(m):
                    nm = m.group(1)
                    val = context.get(nm)
                    return str(val) if val is not None else '0'
                expr_replaced = placeholder.sub(repl, expr)
                # Essayer évaluation numérique
                val_out: Any
                try:
                    val_out = eval(expr_replaced, safe_globals, safe_locals)
                except Exception:
                    # garder la chaîne substituée si non numérique
                    val_out = expr_replaced
                context[p.name] = val_out
        
        return context

    def build_random_context(self, seed: Optional[str] = None) -> Dict[str, Any]:
        """Construit un contexte aléatoire. Si K (synchro) est défini, choisit un index global (1..K)
        et délègue à build_context_for_variant pour synchroniser tous les paramètres cochés.
        Sinon, effectue un tirage libre par paramètre (comportement non-synchro).
        """
        print(f"DEBUG: build_random_context appelé pour page {self.id}, seed={seed}")
        K = self.compute_sync_K()
        print(f"DEBUG: K calculé = {K}")
        if K and K > 0:
            rng = random.Random(seed)
            index = rng.randint(1, K)
            print(f"DEBUG: Utilisation build_context_for_variant avec index={index}")
            return self.build_context_for_variant(index, seed=seed)
        # Pas de synchro: fallback sur ancienne logique param par param
        rng = random.Random(seed)
        ctx: Dict[str, Any] = {}
        print(f"DEBUG: Traitement param par param, {self.param_items.count()} paramètres")
        for param in self.param_items.all():
            print(f"DEBUG: Traitement paramètre {param.name} (type: {param.kind})")
            if param.sync_enabled:
                # Même sans K, rester cohérent: essaye série sinon valeurs directes
                return self.build_context_for_variant(1, seed=seed)
            # Non synchro
            if param.kind == 'const':
                ctx[param.name] = param.const_value
            elif param.kind == 'expr':
                ctx[param.name] = None  # calculé après
            elif param.kind == 'range':
                vals = []
                if param.range_min is not None and param.range_max is not None and param.range_step is not None and param.range_step > 0:
                    count = int(math.floor((param.range_max - param.range_min) / param.range_step) + 1)
                    vals = [param.range_min + i * param.range_step for i in range(count)]
                ctx[param.name] = rng.choice(vals) if vals else None
            elif param.kind == 'set':
                try:
                    vals = parse_set_items(param.set_text or '')
                    ctx[param.name] = rng.choice(vals) if vals else None
                except Exception as e:
                    print(f"DEBUG: Erreur paramètre set '{param.name}': {e}")
                    ctx[param.name] = None
            elif param.kind == 'image':
                # Pour les paramètres non synchronisés, utiliser image_entries
                vals = [e.image_id for e in param.image_entries.all() if e.image_id]
                ctx[param.name] = rng.choice(vals) if vals else None
            elif param.kind == 'slot':
                try:
                    vals = [str(e.value_richtext or '') for e in param.sync_entries.all()]
                    ctx[param.name] = rng.choice(vals) if vals else ''
                except Exception as e:
                    print(f"DEBUG: Erreur paramètre slot '{param.name}': {e}")
                    ctx[param.name] = ''
            elif param.kind == 'tableau':
                # Retourner la structure complète du tableau
                ctx[param.name] = {
                    'orientation': param.tableau_orientation,
                    'header': param.tableau_header,
                    'rows': param.tableau_rows.split('\n') if param.tableau_rows else []
                }
            else:
                ctx[param.name] = None
        # Évaluer les expr en dernier
        import re as _re
        placeholder = _re.compile(r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]")
        num_env: Dict[str, float] = {}
        for k, v in ctx.items():
            try:
                if v is not None and v != '':
                    num_env[k] = float(v)
            except Exception:
                pass
        safe_globals = {'__builtins__': {}}
        safe_locals = {'math': math, **num_env}
        for p in self.param_items.all():
            if p.kind == 'expr':
                expr = p.expr_code or ''
                def repl(m):
                    nm = m.group(1)
                    val = ctx.get(nm)
                    return str(val) if val is not None else '0'
                expr_replaced = placeholder.sub(repl, expr)
                try:
                    val_out = eval(expr_replaced, safe_globals, safe_locals)
                except Exception:
                    val_out = expr_replaced
                ctx[p.name] = val_out
        print(f"DEBUG: Contexte final généré: {ctx}")
        return ctx


class ParamItem(ClusterableModel):
    """Paramètre détecté dans l'exercice parent"""
    page = ParentalKey(
        ParametreExoPage,
        on_delete=models.CASCADE,
        related_name='param_items'
    )
    
    name = models.CharField(
        max_length=10,
        verbose_name="Nom du paramètre"
    )
    
    KIND_CHOICES = [
        ('const', 'Constante'),
        ('range', 'Plage'),
        ('set', 'Ensemble'),
        ('slot', 'Slot'),
        ('image', 'Image'),
        ('tableau', 'Tableau'),
        ('expr', 'Expression'),
    ]
    
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default='const',
        verbose_name="Type"
    )
    
    sync_enabled = models.BooleanField(
        default=False,
        verbose_name="Synchro"
    )
    
    is_orphaned = models.BooleanField(
        default=False,
        verbose_name="Paramètre orphelin"
    )
    
    # Champs de données selon le type
    const_value = models.TextField(
        blank=True,
        verbose_name="Valeur constante"
    )
    
    range_min = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Minimum"
    )
    
    range_max = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Maximum"
    )
    
    range_step = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Pas"
    )
    
    set_text = models.TextField(
        blank=True,
        verbose_name="Texte de l'ensemble",
        help_text="Séparer par ; ou retour ligne ; nombres ou texte court (1–3 mots)"
    )
    
    slot_default = RichTextField(
        blank=True,
        verbose_name="Texte par défaut du slot"
    )
    
    expr_code = models.TextField(
        blank=True,
        verbose_name="Code d'expression"
    )

    # Champs pour le type tableau
    tableau_orientation = models.CharField(
        max_length=1,
        choices=[('h', 'Horizontal'), ('v', 'Vertical')],
        default='h',
        verbose_name="Orientation"
    )

    tableau_header = models.TextField(
        blank=True,
        verbose_name="Entête",
        help_text="Titres séparés par des points-virgules (;)"
    )

    tableau_rows = models.TextField(
        blank=True,
        verbose_name="Lignes",
        help_text="Chaque ligne sur une nouvelle ligne, valeurs séparées par des points-virgules (;)"
    )

    panels = [
        # Ligne 1 : Synchro | Nom | Type
        FieldRowPanel([
            FieldPanel('sync_enabled', classname='param-head'),
            FieldPanel('name', classname='param-head'),
            FieldPanel('kind', classname='param-head param-kind-select'),
        ], heading="Paramètre"),
        # Ligne 2 : champs par type (toggle via JS admin)
        FieldPanel('const_value', classname='param-field param-field-const'),
        FieldRowPanel([
            FieldPanel('range_min', classname='param-field param-field-range'),
            FieldPanel('range_max', classname='param-field param-field-range'),
            FieldPanel('range_step', classname='param-field param-field-range'),
        ], classname='param-field param-field-range'),
        FieldPanel('set_text', classname='param-field param-field-set'),
        FieldPanel('slot_default', classname='param-field param-field-slot'),
        InlinePanel('sync_entries', heading="Variantes du slot (1 entrée = 1 version)", classname='param-field param-field-slot'),
        FieldPanel('expr_code', classname='param-field param-field-expr'),
        InlinePanel('image_entries', heading="Images", classname='param-field param-field-image'),
        FieldRowPanel([
            FieldPanel('tableau_orientation', classname='param-field param-field-tableau'),
            FieldPanel('tableau_header', classname='param-field param-field-tableau'),
        ], classname='param-field param-field-tableau'),
        FieldPanel('tableau_rows', classname='param-field param-field-tableau'),
    ]
    
    class Meta:
        verbose_name = "Paramètre"
        verbose_name_plural = "Paramètres"
        ordering = ['name']


class ParamSyncEntry(ClusterableModel):
    """Entrée synchronisée pour un paramètre"""
    param_item = ParentalKey(
        ParamItem,
        on_delete=models.CASCADE,
        related_name='sync_entries'
    )
    
    index = models.PositiveIntegerField(
        verbose_name="Index (1..K)"
    )
    
    # Champs polyvalents selon le type de paramètre
    value_text = models.TextField(
        blank=True,
        verbose_name="Valeur texte"
    )
    
    value_number = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valeur numérique"
    )
    
    value_richtext = RichTextField(
        blank=True,
        verbose_name="Valeur texte riche"
    )
    
    value_image = models.ForeignKey(
        Image,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Valeur image"
    )
    
    panels = [
        FieldPanel('index'),
        FieldPanel('value_richtext'),
    ]
    
    class Meta:
        verbose_name = "Entrée synchronisée"
        verbose_name_plural = "Entrées synchronisées"
        ordering = ['index']


def parse_set_items(text: str) -> list[str]:
    """
    Parse le texte d'un ensemble de valeurs
    
    Args:
        text: Texte contenant les valeurs séparées par ; ou \n
        
    Returns:
        Liste des valeurs nettoyées
    """
    if not text:
        return []
    
    # Split par ; ou \n
    items = re.split(r'[;\n]', text)
    
    # Nettoyer chaque item
    cleaned_items = []
    for item in items:
        item = item.strip()
        if item:  # Ignorer les items vides
            cleaned_items.append(item)
    
    return cleaned_items
