from django.urls import path
from . import views

app_name = 'kahoot'

urlpatterns = [
    # Page principale du générateur
    path('', views.generator_page, name='generator'),
    
    # API pour créer une session
    path('api/create-session/', views.create_session, name='create_session'),
    
    # Pages de session
    path('join/<str:session_id>/', views.join_session, name='join_session'),
    path('student/<str:session_id>/', views.student_join, name='student_join'),
    path('student/', views.student_join_by_code, name='student_join_general'),
    path('play/<str:session_id>/', views.play_session, name='play_session'),
    
    # APIs de session (anciennes)
    path('api/<str:session_id>/add-participant/', views.add_participant, name='add_participant'),
    path('api/<str:session_id>/start/', views.start_session, name='start_session'),
    path('api/<str:session_id>/next-question/', views.next_question, name='next_question'),
    path('api/<str:session_id>/status/', views.get_session_status, name='get_session_status'),
    
    # APIs REST pour le temps réel
    path('api/join/', views.api_join, name='api_join'),
    path('api/state/<str:session_code>/', views.api_state, name='api_state'),
    path('api/host/start/<str:session_code>/', views.api_host_start, name='api_host_start'),
    path('api/host/next/<str:session_code>/', views.api_host_next, name='api_host_next'),
    path('api/answer/', views.api_answer, name='api_answer'),
    path('api/host/reveal/<str:session_code>/', views.api_host_reveal, name='api_host_reveal'),
    path('api/host/start-question/<str:session_code>/', views.api_host_start_question, name='api_host_start_question'),
    path('api/host/start-answers/<str:session_code>/', views.api_host_start_answers, name='api_host_start_answers'),
]

