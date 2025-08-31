// Script de débogage pour la connexion des élèves
// À ajouter dans la console du navigateur sur la page student_join.html

function debugStudentJoin() {
    console.log('🔍 Débogage de la connexion élève');
    console.log('=' * 50);
    
    // Vérifier les éléments du formulaire
    const codeInput = document.getElementById('code');
    const pseudoInput = document.getElementById('pseudo');
    const joinForm = document.getElementById('joinForm');
    
    console.log('📝 Éléments du formulaire:');
    console.log('- Code input:', codeInput ? '✅ Trouvé' : '❌ Manquant');
    console.log('- Pseudo input:', pseudoInput ? '✅ Trouvé' : '❌ Manquant');
    console.log('- Form:', joinForm ? '✅ Trouvé' : '❌ Manquant');
    
    if (codeInput && pseudoInput) {
        console.log('📊 Valeurs actuelles:');
        console.log('- Code:', codeInput.value);
        console.log('- Pseudo:', pseudoInput.value);
    }
    
    // Vérifier le token CSRF
    const csrfToken = getCookie('csrftoken');
    console.log('🔐 Token CSRF:', csrfToken ? '✅ Présent' : '❌ Manquant');
    
    // Vérifier les variables globales
    console.log('🌐 Variables globales:');
    console.log('- sessionCode:', sessionCode);
    console.log('- participantId:', participantId);
    console.log('- gamePolling:', gamePolling);
}

function testJoinAPI(code, pseudo) {
    console.log('🧪 Test de l\'API join');
    console.log('=' * 50);
    console.log('Code:', code);
    console.log('Pseudo:', pseudo);
    
    const csrfToken = getCookie('csrftoken');
    
    fetch('/kahoot/api/join/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            code_session: code,
            pseudo: pseudo
        })
    })
    .then(response => {
        console.log('📡 Réponse HTTP:', response.status, response.statusText);
        return response.json();
    })
    .then(data => {
        console.log('📊 Données reçues:', data);
        
        if (data.success) {
            console.log('✅ Connexion réussie!');
            console.log('- Session ID:', data.session_id);
            console.log('- Participant ID:', data.participant_id);
            console.log('- État:', data.state);
        } else {
            console.log('❌ Erreur:', data.error);
        }
    })
    .catch(error => {
        console.error('❌ Erreur de connexion:', error);
    });
}

function testStateAPI(code) {
    console.log('🧪 Test de l\'API state');
    console.log('=' * 50);
    console.log('Code:', code);
    
    fetch(`/kahoot/api/state/${code}/`)
    .then(response => {
        console.log('📡 Réponse HTTP:', response.status, response.statusText);
        return response.json();
    })
    .then(data => {
        console.log('📊 État de la session:', data);
        
        if (data.error) {
            console.log('❌ Erreur:', data.error);
        } else {
            console.log('✅ Session trouvée!');
            console.log('- Phase:', data.phase);
            console.log('- Participants:', data.participants);
            console.log('- Questions:', data.total_questions);
        }
    })
    .catch(error => {
        console.error('❌ Erreur de connexion:', error);
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

// Simuler une soumission de formulaire
function simulateJoin(code, pseudo) {
    console.log('🎭 Simulation de connexion');
    console.log('=' * 50);
    
    // Remplir le formulaire
    const codeInput = document.getElementById('code');
    const pseudoInput = document.getElementById('pseudo');
    
    if (codeInput && pseudoInput) {
        codeInput.value = code;
        pseudoInput.value = pseudo;
        
        // Déclencher l'événement submit
        const joinForm = document.getElementById('joinForm');
        if (joinForm) {
            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            joinForm.dispatchEvent(submitEvent);
        }
    }
}

// Exposer les fonctions globalement
window.debugStudentJoin = debugStudentJoin;
window.testJoinAPI = testJoinAPI;
window.testStateAPI = testStateAPI;
window.simulateJoin = simulateJoin;

console.log('🔧 Script de débogage élève chargé');
console.log('Utilisez debugStudentJoin() pour diagnostiquer');
console.log('Utilisez testJoinAPI(code, pseudo) pour tester l\'API');
console.log('Utilisez testStateAPI(code) pour tester l\'état de la session');
console.log('Utilisez simulateJoin(code, pseudo) pour simuler une connexion');

