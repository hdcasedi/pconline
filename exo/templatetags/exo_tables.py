# exo/templatetags/exo_tables.py
from django import template
from django.utils.safestring import mark_safe
from exo.blocks import StyledTableBlock
from exo.utils.table_param import (
    parse_table_bank, pick_rows, apply_masks_h, apply_masks_v,
    to_tableblock_value_h, to_tableblock_value_v
)

register = template.Library()

@register.simple_tag(takes_context=True)
def render_param_table(context, name: str, view: str = "eleve", orientation: str = "h", n: int = 3, seed: int | None = None):
    """
    Rendu HTML du paramètre tableau `name`.
    - `view` : 'eleve' (masques actifs) ou 'corrige' (masques levés)
    - `orientation`: 'h' (entête ligne 1) ou 'v' (entête colonne 1)
    - `n`: nombre de lignes/colonnes tirées (par défaut 3)
    - `seed`: graine ; si None, tenter context['K'] (graine d'exo)
    """
    # Récup param depuis le contexte (ExoParamPage)
    params = context.get("exo_params", {})
    if name not in params:
        return ""

    base_seed = seed if seed is not None else context.get("K", 1)
    # Varier la graine selon le nom du paramètre pour avoir des tirages différents
    import hashlib
    seed_string = f"{base_seed}_{name}"
    seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)

    bank = parse_table_bank({
        "orientation": params[name].get("orientation", orientation),
        "header": params[name]["header"],
        "rows": params[name]["rows"],
    })

    # Tirage de n lignes (orientation h) ou n colonnes (orientation v)
    picked = pick_rows(bank, n=n, seed=seed)

    block = StyledTableBlock()

    if bank.orientation == "v":
        # picked = colonnes tirées ; appliquer masques par ligne (header vertical)
        header, cols = apply_masks_v(bank.header, list(zip(*picked)) if picked else [], view=view)
        # ^ on veut une liste de colonnes: transpose si nécessaire
        value = to_tableblock_value_v(header, cols)
    else:
        # orientation horizontale
        header, rows = apply_masks_h(bank.header, picked, view=view)
        value = to_tableblock_value_h(header, rows)

    html = block.render(value)
    return mark_safe(html)

