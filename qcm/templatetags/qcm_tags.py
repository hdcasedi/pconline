from django import template
from django.utils.html import mark_safe
from wagtail.images import get_image_model

import json

from qcm.models import QcmQuestionAPage, QcmBankBPage

register = template.Library()
Image = get_image_model()


def _img_url(img):
    if not img:
        return None
    try:
        return img.get_rendition("width-800").url
    except Exception:
        return getattr(img, "file", None) and img.file.url or None


@register.simple_tag
def qcm_json_for_cours(cours_page):
    """
    Retourne un JSON compact avec toutes les questions rattachées
    (enfants directs) à cette CoursPage (Types A + B).
    Le tirage (shuffle, 10 max) sera fait côté JS.
    """
    items = []

    # Type A
    for q in QcmQuestionAPage.objects.child_of(cours_page).live():
        options = []
        for opt in q.options.all():
            options.append({
                "html": opt.text,           # RichText rendu tel quel (sera affiché en HTML)
                "correct": bool(opt.is_correct),
                "explanation_html": opt.explanation or "",
            })
        items.append({
            "kind": "A",
            "id": q.id,
            "layout": q.layout,
            "statement_html": q.statement,
            "image": _img_url(q.image),
            "video_url": q.video_url or "",
            "requires_justification": bool(q.requires_justification),
            "explanation_html": q.explanation or "",
            "options": options,            # ≥4 attendu via backoffice
        })

    # Type B (banques + variantes)
    for bank in QcmBankBPage.objects.child_of(cours_page).live():
        variants = []
        for v in bank.variants.all():
            variants.append({
                "layout": v.layout,
                "statement_html": v.statement,
                "answer_html": v.answer,
                "explanation_html": v.explanation or "",
                "image": _img_url(v.image),
                "video_url": v.video_url or "",
            })
        items.append({
            "kind": "B_BANK",
            "id": bank.id,
            "variants": variants,          # distracteurs à piocher dans ce tableau
        })

    return mark_safe(json.dumps(items, ensure_ascii=False))
