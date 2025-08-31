import uuid
import json
from django.utils import timezone
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField


class KahootGeneratorPage(Page):
    """
    Page de génération de quiz Kahoot.
    Permet de configurer et lancer une session de quiz.
    """
    template = "kahoot/generator_page.html"
    
    # Configuration par défaut
    default_questions_count = models.IntegerField(
        default=10,
        help_text="Nombre de questions par défaut"
    )
    default_timer_enabled = models.BooleanField(
        default=True,
        help_text="Chrono activé par défaut"
    )
    default_timer_duration = models.IntegerField(
        default=30,
        help_text="Durée par défaut en secondes"
    )
    
    parent_page_types = ['home.HomePage']
    subpage_types = []
    
    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("default_questions_count"),
            FieldPanel("default_timer_enabled"),
            FieldPanel("default_timer_duration"),
        ], heading="Configuration par défaut"),
    ]


class KahootSession(models.Model):
    """
    Session de quiz Kahoot en cours.
    """
    session_id = models.CharField(max_length=36, unique=True, default=uuid.uuid4)
    short_code = models.CharField(max_length=8, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Configuration de la session
    questions_count = models.IntegerField(default=10)
    timer_enabled = models.BooleanField(default=True)
    timer_duration = models.IntegerField(default=30)
    selected_chapters = models.JSONField(default=list)  # Liste des IDs de chapitres
    
    # Questions de la session (sérialisées)
    questions_data = models.JSONField(default=list)
    current_question_index = models.IntegerField(default=0)
    
    # Participants
    participants = models.JSONField(default=list)  # Liste des pseudos
    participant_scores = models.JSONField(default=dict)  # Scores par participant
    participant_answers = models.JSONField(default=dict)  # Réponses par participant
    
    # Statut
    is_active = models.BooleanField(default=True)
    current_phase = models.CharField(max_length=20, default='waiting')  # waiting, question, answers, results
    question_start_time = models.DateTimeField(null=True, blank=True)
    answers_revealed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Session Kahoot"
        verbose_name_plural = "Sessions Kahoot"
    
    def __str__(self):
        return f"Session {self.session_id[:8]} - {self.questions_count} questions"
    
    def get_join_url(self):
        """Retourne l'URL pour rejoindre la session"""
        return f"/kahoot/student/{self.short_code}/"
    
    def get_play_url(self):
        """Retourne l'URL pour jouer la session"""
        return f"/kahoot/play/{self.session_id}/"
    
    def generate_short_code(self):
        """Génère un code court unique de 8 chiffres"""
        import random
        
        while True:
            # Générer un code de 8 chiffres
            code = ''.join(random.choices('0123456789', k=8))
            
            # Vérifier qu'il n'existe pas déjà
            if not KahootSession.objects.filter(short_code=code).exists():
                return code
    
    def save(self, *args, **kwargs):
        # Générer un code court si il n'en a pas
        if not self.short_code:
            self.short_code = self.generate_short_code()
        super().save(*args, **kwargs)
    
    def get_current_question(self):
        """Retourne la question actuelle"""
        if self.current_question_index < len(self.questions_data):
            return self.questions_data[self.current_question_index]
        return None
    
    def add_participant(self, pseudo):
        """Ajoute un participant à la session"""
        if pseudo not in self.participants:
            self.participants.append(pseudo)
            self.save(update_fields=['participants'])
    
    def next_question(self):
        """Passe à la question suivante"""
        if self.current_question_index < len(self.questions_data) - 1:
            self.current_question_index += 1
            self.save(update_fields=['current_question_index'])
            return True
        return False
    
    def start_session(self):
        """Démarre la session"""
        self.started_at = timezone.now()
        self.current_question_index = 0
        self.current_phase = 'question'  # Démarrer directement en phase question
        self.question_start_time = timezone.now()
        self.answers_revealed = False
        self.save(update_fields=['started_at', 'current_question_index', 'current_phase', 'question_start_time', 'answers_revealed'])
    
    def start_question_phase(self):
        """Démarre la phase question (10 secondes)"""
        self.current_phase = 'question'
        self.question_start_time = timezone.now()
        self.answers_revealed = False
        self.save(update_fields=['current_phase', 'question_start_time', 'answers_revealed'])
    
    def start_answers_phase(self):
        """Démarre la phase réponses"""
        self.current_phase = 'answers'
        self.save(update_fields=['current_phase'])
    
    def reveal_answers(self):
        """Révèle les réponses et passe en phase résultats"""
        self.current_phase = 'results'
        self.answers_revealed = True
        self.save(update_fields=['current_phase', 'answers_revealed'])
    
    def end_session(self):
        """Termine la session"""
        self.ended_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['ended_at', 'is_active'])


