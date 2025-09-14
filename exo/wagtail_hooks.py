from wagtail import hooks
from django.utils.html import format_html
from django.utils.safestring import mark_safe


@hooks.register("insert_editor_css")
def exo_paramitem_admin_css():
    # Cache tout par défaut ; on affichera ce qu'il faut en JS
    css = """
<style>
  .param-field{display:none;}
  .param-head input, .param-head select{max-width: 220px;}
  .param-field-range .field-content input{max-width: 140px;}
  .param-field-set textarea{min-height: 60px;}
</style>
"""
    return format_html("{}", mark_safe(css))


@hooks.register("insert_editor_js")
def exo_paramitem_admin_js():
    script = """
<script>
document.addEventListener('DOMContentLoaded', function() {
  function findParamContainer(select){
    return select.closest('[data-contentpath^="param_items."]')
      || select.closest('.object')
      || select.closest('fieldset')
      || select.closest('form')
      || document;
  }
  function showTypeFor(select, kind){
    // Normaliser la valeur du type (certains environnements peuvent fournir le libellé traduit)
    const mapKind = {
      'const': 'const', 'constante': 'const',
      'range': 'range', 'plage': 'range',
      'set': 'set', 'ensemble': 'set',
      'slot': 'slot',
      'image': 'image',
      'tableau': 'tableau',
      'expr': 'expr', 'expression': 'expr'
    };
    const k = (kind || '').toString().trim().toLowerCase();
    const norm = mapKind[k] || 'const';
    const container = findParamContainer(select);
    if(!container) return;
    
    console.log('showTypeFor: kind=' + kind + ', norm=' + norm + ', container found=' + !!container);
    
    // Masquer tous les champs de cette ligne paramètre
    container.querySelectorAll('.param-field').forEach(function(el){ 
      el.style.display='none'; 
      console.log('Masqué: ' + el.className);
    });
    
    // Afficher le groupe du type demandé
    const fieldsToShow = container.querySelectorAll('.param-field-' + norm);
    console.log('Champs à afficher pour ' + norm + ': ' + fieldsToShow.length);
    fieldsToShow.forEach(function(el){ 
      el.style.display='block'; 
      console.log('Affiché: ' + el.className);
    });
    
    // Cas const: forcer l'affichage du champ const
    if(norm === 'const'){
      container.querySelectorAll('.param-field-const').forEach(function(el){ el.style.display='block'; });
    }
  }
  function bindAll(){
    console.log('bindAll: Recherche des sélecteurs de type...');
    const selects = document.querySelectorAll('select[name$="-kind"]');
    console.log('bindAll: Trouvé ' + selects.length + ' sélecteurs');
    
    selects.forEach(function(select){
      console.log('bindAll: Traitement sélecteur, valeur=' + select.value);
      showTypeFor(select, select.value);
      select.addEventListener('change', function(){ 
        console.log('bindAll: Changement détecté, nouvelle valeur=' + this.value);
        showTypeFor(select, this.value); 
      });
    });
    
    // Debug: vérifier la présence des champs de tableau
    const tableauFields = document.querySelectorAll('.param-field-tableau');
    console.log('bindAll: Champs tableau trouvés: ' + tableauFields.length);
    tableauFields.forEach(function(field, index){
      console.log('bindAll: Champ tableau ' + index + ': ' + field.className + ', display=' + field.style.display);
    });
  }
  bindAll();
  // Re-appliquer juste après le paint pour couvrir les chargements différés
  setTimeout(bindAll, 0);
  document.body.addEventListener('w-formset:added', function(e){
    const select = e.target.querySelector && e.target.querySelector('select[name$="-kind"]');
    if(select){
      showTypeFor(select, select.value);
      select.addEventListener('change', function(){ showTypeFor(select, select.value); });
    }
  });
});
</script>
"""
    return format_html("{}", mark_safe(script))
