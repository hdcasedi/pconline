// Filtrage dynamique des chapitres selon le niveau parent
document.addEventListener('DOMContentLoaded', function() {
    const chapitreSelect = document.querySelector('select[name="chapitre"]');
    
    if (chapitreSelect) {
        // Récupérer le niveau de la page parente depuis l'URL ou les données de la page
        const urlParams = new URLSearchParams(window.location.search);
        const parentId = urlParams.get('parent');
        
        if (parentId) {
            // Faire une requête AJAX pour récupérer les chapitres du niveau parent
            fetch(`/cours/api/chapitres/${parentId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.chapitres) {
                        // Vider le select
                        chapitreSelect.innerHTML = '<option value="">---------</option>';
                        
                        // Ajouter les chapitres filtrés
                        data.chapitres.forEach(chapitre => {
                            const option = document.createElement('option');
                            option.value = chapitre.id;
                            option.textContent = chapitre.titre;
                            chapitreSelect.appendChild(option);
                        });
                    }
                })
                .catch(error => {
                    console.error('Erreur lors du filtrage des chapitres:', error);
                });
        }
    }
});



