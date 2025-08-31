import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.contrib import messages
from wagtail.images.models import Image

from .models import KahootGeneratorPage, KahootSession

# URLs directes des images de badges A/B/C/D (dans static/images/)
BADGE_IMAGE_URLS = {
    'A': '/static/images/A.png',
    'B': '/static/images/B.png', 
    'C': '/static/images/C.png',
    'D': '/static/images/D.png',
}
from .utils import get_available_chapters_by_niveau, select_questions_from_chapters


def generator_page(request):
    """
    Page principale du générateur QuizzUp.
    """
    try:
        generator_page = KahootGeneratorPage.objects.live().first()
        if not generator_page:
            # Créer la page si elle n'existe pas
            from home.models import HomePage
            home_page = HomePage.objects.live().first()
            if home_page:
                generator_page = KahootGeneratorPage(
                    title="Générateur QuizzUp",
                    slug="generateur-quizzup",
                    default_questions_count=10,
                    default_timer_enabled=True,
                    default_timer_duration=30
                )
                home_page.add_child(instance=generator_page)
                generator_page.save_revision().publish()
    except Exception:
        generator_page = None
    
    # Récupérer la structure des niveaux/thèmes/chapitres
    chapters_structure = get_available_chapters_by_niveau()
    
    context = {
        'page': generator_page,
        'chapters_structure': chapters_structure,
        'default_questions_count': generator_page.default_questions_count if generator_page else 10,
        'default_timer_enabled': generator_page.default_timer_enabled if generator_page else True,
        'default_timer_duration': generator_page.default_timer_duration if generator_page else 30,
    }
    
    return render(request, 'kahoot/generator_page.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    """
    Crée une nouvelle session de quiz.
    """
    try:
        data = json.loads(request.body)
        
        # Validation des données
        chapter_ids = data.get('chapter_ids', [])
        questions_count = int(data.get('questions_count', 10))
        timer_enabled = bool(data.get('timer_enabled', True))
        timer_duration = int(data.get('timer_duration', 30))
        
        if not chapter_ids:
            return JsonResponse({'error': 'Aucun chapitre sélectionné'}, status=400)
        
        if questions_count < 1 or questions_count > 50:
            return JsonResponse({'error': 'Nombre de questions invalide'}, status=400)
        
        # Sélectionner les questions
        questions = select_questions_from_chapters(chapter_ids, questions_count)
        
        print(f"Chapitres sélectionnés: {chapter_ids}")
        print(f"Questions trouvées: {len(questions)}")
        
        if not questions:
            return JsonResponse({'error': 'Aucune question trouvée dans les chapitres sélectionnés'}, status=400)
        
        # Créer la session
        session = KahootSession.objects.create(
            questions_count=questions_count,
            timer_enabled=timer_enabled,
            timer_duration=timer_duration,
            selected_chapters=chapter_ids,
            questions_data=questions,
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.session_id,
            'join_url': session.get_join_url(),
            'play_url': session.get_play_url(),
            'short_code': session.short_code,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def join_session(request, session_id):
    """
    Page pour rejoindre une session (QR code + liste des participants).
    """
    from django.urls import reverse
    
    # Essayer de trouver la session par session_id ou short_code
    try:
        session = KahootSession.objects.get(session_id=session_id, is_active=True)
    except KahootSession.DoesNotExist:
        try:
            session = KahootSession.objects.get(short_code=session_id, is_active=True)
        except KahootSession.DoesNotExist:
            raise Http404("Session non trouvée")
    
    join_url = request.build_absolute_uri(
        reverse('kahoot:student_join', args=[session.short_code])
    )
    
    context = {
        'session': session,
        'join_url': join_url,
    }
    
    return render(request, 'kahoot/join_session.html', context)


def student_join(request, session_id):
    """
    Page pour que les élèves rejoignent une session (pseudo + code).
    """
    # Essayer de trouver la session par session_id ou short_code
    try:
        session = KahootSession.objects.get(session_id=session_id, is_active=True)
    except KahootSession.DoesNotExist:
        try:
            session = KahootSession.objects.get(short_code=session_id, is_active=True)
        except KahootSession.DoesNotExist:
            raise Http404("Session non trouvée")
    
    context = {
        'session': session,
        'session_id': session.session_id,  # Toujours utiliser le vrai session_id
    }
    
    return render(request, 'kahoot/student_join.html', context)


def student_join_by_code(request):
    """
    Page générale pour que les élèves rejoignent une session par code.
    """
    return render(request, 'kahoot/student_join.html', {})


def play_session(request, session_id):
    """
    Page pour jouer la session (questions + réponses).
    """
    # Debug: afficher les informations de recherche
    print(f"🔍 PLAY_SESSION DEBUG - Recherche session avec: {session_id}")
    print(f"🔍 PLAY_SESSION DEBUG - Type de session_id: {type(session_id)}")
    print(f"🔍 PLAY_SESSION DEBUG - Longueur: {len(session_id)}")
    
    # Essayer de trouver la session par session_id ou short_code (actives d'abord)
    try:
        session = KahootSession.objects.get(session_id=session_id, is_active=True)
        print(f"🔍 PLAY_SESSION DEBUG - Session trouvée par session_id (active)")
    except KahootSession.DoesNotExist:
        print(f"🔍 PLAY_SESSION DEBUG - Session non trouvée par session_id (active), essai avec short_code")
        try:
            session = KahootSession.objects.get(short_code=session_id, is_active=True)
            print(f"🔍 PLAY_SESSION DEBUG - Session trouvée par short_code (active)")
        except KahootSession.DoesNotExist:
            print(f"🔍 PLAY_SESSION DEBUG - Session non trouvée par short_code (active), essai avec sessions inactives")
            # Essayer avec les sessions inactives pour debug
            try:
                session = KahootSession.objects.get(short_code=session_id)
                print(f"🔍 PLAY_SESSION DEBUG - Session trouvée par short_code (inactive)")
            except KahootSession.DoesNotExist:
                print(f"🔍 PLAY_SESSION DEBUG - Session non trouvée du tout")
                # Debug: afficher toutes les sessions pour diagnostiquer
                all_sessions = KahootSession.objects.all()
                print(f"🔍 PLAY_SESSION DEBUG - Toutes les sessions: {list(all_sessions.values('session_id', 'short_code', 'is_active'))}")
                raise Http404("Session non trouvée")
    
    current_question = session.get_current_question()
    
    # Debug info
    print(f"Session: {session.session_id}")
    print(f"Short code: {session.short_code}")
    print(f"Questions data: {len(session.questions_data)} questions")
    print(f"Current index: {session.current_question_index}")
    print(f"Current question: {current_question}")
    
    context = {
        'session': session,
        'current_question': current_question,
        'question_index': session.current_question_index + 1,
        'total_questions': len(session.questions_data),
    }
    
    return render(request, 'kahoot/play_session.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def add_participant(request, session_id):
    """
    API pour ajouter un participant à la session.
    """
    try:
        # Essayer de trouver la session par session_id ou short_code
        try:
            session = KahootSession.objects.get(session_id=session_id, is_active=True)
        except KahootSession.DoesNotExist:
            try:
                session = KahootSession.objects.get(short_code=session_id, is_active=True)
            except KahootSession.DoesNotExist:
                return JsonResponse({'error': 'Code de session invalide'}, status=404)
        
        data = json.loads(request.body)
        pseudo = data.get('pseudo', '').strip()
        
        if not pseudo:
            return JsonResponse({'error': 'Pseudo requis'}, status=400)
        
        if len(pseudo) > 20:
            return JsonResponse({'error': 'Pseudo trop long'}, status=400)
        
        session.add_participant(pseudo)
        
        return JsonResponse({
            'success': True,
            'participants': session.participants,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def start_session(request, session_id):
    """
    API pour démarrer la session.
    """
    try:
        # Essayer de trouver la session par session_id ou short_code
        try:
            session = KahootSession.objects.get(session_id=session_id, is_active=True)
        except KahootSession.DoesNotExist:
            try:
                session = KahootSession.objects.get(short_code=session_id, is_active=True)
            except KahootSession.DoesNotExist:
                return JsonResponse({'error': 'Session non trouvée'}, status=404)
        
        session.start_session()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def next_question(request, session_id):
    """
    API pour passer à la question suivante.
    """
    try:
        # Essayer de trouver la session par session_id ou short_code
        try:
            session = KahootSession.objects.get(session_id=session_id, is_active=True)
        except KahootSession.DoesNotExist:
            try:
                session = KahootSession.objects.get(short_code=session_id, is_active=True)
            except KahootSession.DoesNotExist:
                return JsonResponse({'error': 'Session non trouvée'}, status=404)
        
        if session.next_question():
            current_question = session.get_current_question()
            return JsonResponse({
                'success': True,
                'question': current_question,
                'question_index': session.current_question_index + 1,
                'has_more': session.current_question_index < len(session.questions_data) - 1,
            })
        else:
            # Session terminée
            session.end_session()
            return JsonResponse({
                'success': True,
                'finished': True,
            })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_session_status(request, session_id):
    """
    API pour récupérer le statut de la session.
    """
    try:
        # Essayer de trouver la session par session_id ou short_code
        try:
            session = KahootSession.objects.get(session_id=session_id, is_active=True)
        except KahootSession.DoesNotExist:
            try:
                session = KahootSession.objects.get(short_code=session_id, is_active=True)
            except KahootSession.DoesNotExist:
                return JsonResponse({'error': 'Code de session invalide'}, status=404)
        
        return JsonResponse({
            'session_id': session.session_id,
            'participants': session.participants,
            'current_question_index': session.current_question_index,
            'total_questions': len(session.questions_data),
            'started': session.started_at is not None,
            'ended': session.ended_at is not None,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============ NOUVELLES APIs REST POUR LE TEMPS RÉEL ============

@csrf_exempt
@require_http_methods(["POST"])
def api_join(request):
    """
    API pour rejoindre une session (code_session, pseudo)
    """
    try:
        data = json.loads(request.body)
        session_code = data.get('code_session', '').strip()
        pseudo = data.get('pseudo', '').strip()
        
        if not session_code or not pseudo:
            return JsonResponse({'error': 'Code session et pseudo requis'}, status=400)
        
        # Trouver la session
        try:
            session = KahootSession.objects.get(short_code=session_code, is_active=True)
        except KahootSession.DoesNotExist:
            return JsonResponse({'error': 'Code de session invalide'}, status=404)
        
        # Ajouter le participant
        session.add_participant(pseudo)
        
        return JsonResponse({
            'success': True,
            'session_id': session.session_id,
            'participant_id': len(session.participants) - 1,  # Index du participant
            'state': get_session_state(session)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_state(request, session_code):
    """
    API pour récupérer l'état de la session
    """
    try:
        session = KahootSession.objects.get(short_code=session_code, is_active=True)
        state = get_session_state(session)
        
        # Debug détaillé
        print(f"🔍 API_STATE DEBUG - Full state keys: {list(state.keys())}")
        print(f"🔍 API_STATE DEBUG - Participant answers in state: {state.get('participant_answers')}")
        print(f"🔍 API_STATE DEBUG - Participant scores in state: {state.get('participant_scores')}")
        
        return JsonResponse(state)
        
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_host_start(request, session_code):
    """
    API pour démarrer le quiz (hôte)
    """
    try:
        session = KahootSession.objects.get(short_code=session_code, is_active=True)
        session.start_session()
        
        # S'assurer que current_question_index est à 0
        session.current_question_index = 0
        session.save()
        
        return JsonResponse({
            'success': True,
            'state': get_session_state(session)
        })
        
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_host_next(request, session_code):
    """
    API pour passer à la question suivante (hôte)
    """
    try:
        session = KahootSession.objects.get(short_code=session_code, is_active=True)
        
        print(f"🔍 API_HOST_NEXT DEBUG - Session: {session.short_code}")
        print(f"🔍 API_HOST_NEXT DEBUG - Current index: {session.current_question_index}")
        print(f"🔍 API_HOST_NEXT DEBUG - Total questions: {len(session.questions_data)}")
        
        # Passer à la question suivante
        session.current_question_index += 1
        
        print(f"🔍 API_HOST_NEXT DEBUG - New index: {session.current_question_index}")
        
        # Vérifier si c'est la fin du quiz
        if session.current_question_index >= len(session.questions_data):
            print(f"🔍 API_HOST_NEXT DEBUG - Quiz terminé, fin de session")
            session.end_session()
            return JsonResponse({
                'finished': True,
                'state': get_session_state(session)
            })
        
        # Démarrer automatiquement la phase question pour la nouvelle question
        session.current_phase = 'question'
        session.question_start_time = timezone.now()
        session.answers_revealed = False
        session.save(update_fields=['current_question_index', 'current_phase', 'question_start_time', 'answers_revealed'])
        
        return JsonResponse({
            'success': True,
            'state': get_session_state(session)
        })
        
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_answer(request):
    """
    API pour enregistrer une réponse (version avec pseudo)
    """
    try:
        data = json.loads(request.body)
        session_code = data.get('code_session')
        pseudo = data.get('pseudo')
        answer = data.get('answer')  # A, B, C, D
        
        if not all([session_code, pseudo, answer]):
            return JsonResponse({'error': 'Code session, pseudo et réponse requis'}, status=400)
        
        session = KahootSession.objects.get(short_code=session_code, is_active=True)
        
        # Vérifier que le participant existe dans la session
        if pseudo not in session.participants:
            return JsonResponse({'error': 'Participant non trouvé'}, status=400)
        
        # Enregistrer la réponse
        current_question = session.get_current_question()
        if not current_question:
            return JsonResponse({'error': 'Aucune question active'}, status=400)
        
        # Convertir A,B,C,D en index (0,1,2,3)
        answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        option_index = answer_map.get(answer.upper())
        if option_index is None:
            return JsonResponse({'error': 'Réponse invalide'}, status=400)
        
        # Vérifier que l'index est valide
        if option_index < 0 or option_index >= len(current_question.get('options', [])):
            return JsonResponse({'error': 'Option invalide'}, status=400)
        
        # Trouver l'option sélectionnée
        selected_option = current_question['options'][option_index]
        is_correct = selected_option.get('is_correct', False)
        
        # Vérification alternative: chercher l'option correcte et comparer
        correct_option_found = None
        for i, opt in enumerate(current_question.get('options', [])):
            if opt.get('is_correct', False):
                correct_option_found = i
                break
        
        # Si on a trouvé une option correcte, vérifier si c'est celle sélectionnée
        if correct_option_found is not None:
            is_correct_alt = (option_index == correct_option_found)
            print(f"DEBUG - Vérification alternative: {is_correct_alt}")
            # Utiliser la vérification alternative si elle diffère
            if is_correct != is_correct_alt:
                print(f"DEBUG - CORRECTION: {is_correct} -> {is_correct_alt}")
                is_correct = is_correct_alt
        
        # Debug: afficher les informations pour diagnostiquer
        print(f"DEBUG - Réponse: {answer}, Option index: {option_index}")
        print(f"DEBUG - Options: {current_question.get('options', [])}")
        print(f"DEBUG - Selected option: {selected_option}")
        print(f"DEBUG - Is correct: {is_correct}")
        
        # Vérification supplémentaire: chercher l'option correcte
        correct_option = None
        for i, opt in enumerate(current_question.get('options', [])):
            if opt.get('is_correct', False):
                correct_option = i
                break
        
        print(f"DEBUG - Correct option index: {correct_option}")
        print(f"DEBUG - User selected index: {option_index}")
        print(f"DEBUG - Match: {option_index == correct_option}")
        
        # Debug complet de la structure
        print(f"DEBUG - Question complète: {current_question}")
        print(f"DEBUG - Nombre d'options: {len(current_question.get('options', []))}")
        for i, opt in enumerate(current_question.get('options', [])):
            print(f"DEBUG - Option {i}: {opt}")
        
        # Debug de la réponse utilisateur
        print(f"DEBUG - Utilisateur a répondu: {answer}")
        print(f"DEBUG - Index calculé: {option_index}")
        print(f"DEBUG - Option sélectionnée: {selected_option}")
        print(f"DEBUG - Cette option est-elle correcte? {is_correct}")
        
        # Vérification manuelle
        print(f"DEBUG - Vérification manuelle:")
        for i, opt in enumerate(current_question.get('options', [])):
            status = "✓" if opt.get('is_correct', False) else "✗"
            print(f"DEBUG -   Option {i} ({chr(65+i)}): {opt.get('html', '')} {status}")
        
        # Calculer le score (points fixes pour l'instant)
        score = 10 if is_correct else 0
        
        # Enregistrer la réponse et le score avec le pseudo comme clé
        if pseudo not in session.participant_answers:
            session.participant_answers[pseudo] = {}
        
        session.participant_answers[pseudo][str(session.current_question_index)] = {
            'option_id': f'o{option_index + 1}',
            'is_correct': is_correct,
            'score': score
        }
        
        # Mettre à jour le score total
        if pseudo not in session.participant_scores:
            session.participant_scores[pseudo] = 0
        
        session.participant_scores[pseudo] += score
        
        session.save()
        
        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'score': score
        })
        
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_host_start_question(request, session_code):
    """
    API pour démarrer la phase question (hôte)
    """
    try:
        session = KahootSession.objects.get(short_code=session_code, is_active=True)
        session.start_question_phase()
        
        return JsonResponse({
            'success': True,
            'state': get_session_state(session)
        })
        
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_host_start_answers(request, session_code):
    """
    API pour démarrer la phase réponses (hôte)
    """
    try:
        session = KahootSession.objects.get(short_code=session_code, is_active=True)
        session.start_answers_phase()
        
        return JsonResponse({
            'success': True,
            'state': get_session_state(session)
        })
        
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_host_reveal(request, session_code):
    """
    API pour révéler les réponses (hôte)
    """
    try:
        session = KahootSession.objects.get(short_code=session_code, is_active=True)
        session.reveal_answers()
        
        return JsonResponse({
            'success': True,
            'state': get_session_state(session)
        })
        
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_session_state(session):
    """
    Fonction utilitaire pour générer l'état de la session
    """
    current_question = session.get_current_question()
    
    # Debug
    print(f"🔍 SERVER DEBUG - Participant answers: {session.participant_answers}")
    print(f"🔍 SERVER DEBUG - Participant scores: {session.participant_scores}")
    print(f"🔍 SERVER DEBUG - Current question index: {session.current_question_index}")
    
    state = {
        'session_code': session.short_code,
        'phase': 'waiting' if not session.started_at else 'playing' if not session.ended_at else 'finished',
        'current_phase': session.current_phase,
        'participants': session.participants,
        'current_question_index': session.current_question_index,
        'total_questions': len(session.questions_data),
        'timer': session.timer_duration if session.timer_enabled else None,
        'participant_scores': session.participant_scores,
        'participant_answers': session.participant_answers,
        'answers_revealed': session.answers_revealed,
    }
    
    if session.started_at:
        current_question = session.get_current_question()
        if current_question:
            # Formater la question selon la structure demandée
            options = []
            badges = ['A', 'B', 'C', 'D']
            for i, option in enumerate(current_question.get('options', [])):
                badge = badges[i] if i < len(badges) else str(i+1)
                badge_url = ""
                
                # Récupérer l'URL de l'image de badge
                if badge in BADGE_IMAGE_URLS:
                    badge_url = BADGE_IMAGE_URLS[badge]
                else:
                    badge_url = ""
                
                options.append({
                    'id': f'o{i+1}',
                    'html': option.get('html', ''),
                    'is_correct': option.get('is_correct', False),
                    'badge': badge,
                    'badge_url': badge_url
                })
            
            state['question'] = {
                'qid': session.current_question_index,
                'type': current_question.get('type', 'A'),
                'statement_html': current_question.get('statement', ''),
                'media': {
                    'image_url': current_question.get('image_url', ''),
                    'video_url': current_question.get('video_url', '')
                },
                'options': options,
                'timer': session.timer_duration if session.timer_enabled else None
            }
            
            # Ajouter les statistiques de réponses si révélées
            if session.answers_revealed:
                state['answer_stats'] = get_answer_statistics(session)
    
    return state

def get_answer_statistics(session):
    """Calcule les statistiques de réponses"""
    stats = {}
    total_participants = len(session.participants)
    
    for i in range(4):  # 4 options A, B, C, D
        option_id = f'o{i+1}'
        count = 0
        for participant_id, answers in session.participant_answers.items():
            current_q = str(session.current_question_index)
            if current_q in answers and answers[current_q]['option_id'] == option_id:
                count += 1
        
        stats[option_id] = {
            'count': count,
            'percentage': round((count / total_participants * 100) if total_participants > 0 else 0, 1)
        }
    
    return stats


