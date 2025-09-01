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
      'expr': 'expr', 'expression': 'expr'
    };
    const k = (kind || '').toString().trim().toLowerCase();
    const norm = mapKind[k] || 'const';
    const container = findParamContainer(select);
    if(!container) return;
    // Masquer tous les champs de cette ligne paramètre
    container.querySelectorAll('.param-field').forEach(function(el){ el.style.display='none'; });
    // Afficher le groupe du type demandé
    container.querySelectorAll('.param-field-' + norm).forEach(function(el){ el.style.display='block'; });
    // Cas const: forcer l'affichage du champ const
    if(norm === 'const'){
      container.querySelectorAll('.param-field-const').forEach(function(el){ el.style.display='block'; });
    }
  }
  function bindAll(){
    document.querySelectorAll('select[name$="-kind"]').forEach(function(select){
      showTypeFor(select, select.value);
      select.addEventListener('change', function(){ showTypeFor(select, select.value); });
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
