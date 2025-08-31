// Script de débogage pour Kahoot
// À ajouter dans la console du navigateur

function debugKahootState() {
    console.log('🔍 Débogage de l\'état Kahoot');
    console.log('=' * 50);
    
    // Récupérer l'état actuel
    fetch(`/kahoot/api/state/${sessionCode}/`)
        .then(response => response.json())
        .then(data => {
            console.log('📊 État de la session:', data);
            console.log('Phase actuelle:', data.current_phase);
            console.log('Réponses révélées:', data.answers_revealed);
            console.log('Statistiques disponibles:', data.answer_stats);
            console.log('Question actuelle:', data.question);
            
            if (data.question) {
                console.log('Options de la question:', data.question.options);
            }
        })
        .catch(error => {
            console.error('❌ Erreur lors de la récupération de l\'état:', error);
        });
}

function testRevealAnswers() {
    console.log('🧪 Test de révélation des réponses');
    console.log('=' * 50);
    
    // Appeler l'API de révélation
    fetch(`/kahoot/api/host/reveal/${sessionCode}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('✅ Réponse de l\'API reveal:', data);
        
        // Vérifier l'état après révélation
        setTimeout(() => {
            debugKahootState();
        }, 1000);
    })
    .catch(error => {
        console.error('❌ Erreur lors de la révélation:', error);
    });
}

// Fonction pour obtenir le token CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Exposer les fonctions globalement
window.debugKahootState = debugKahootState;
window.testRevealAnswers = testRevealAnswers;

console.log('🔧 Script de débogage Kahoot chargé');
console.log('Utilisez debugKahootState() pour voir l\'état actuel');
console.log('Utilisez testRevealAnswers() pour tester la révélation');

