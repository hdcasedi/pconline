from django import forms
from wagtail import blocks

try:
    from django_ckeditor_5.widgets import CKEditor5Widget as _CKEditor5Widget
except Exception:  # pragma: no cover
    _CKEditor5Widget = None  # type: ignore


class CKEditor5Block(blocks.FieldBlock):
    """
    Bloc Wagtail utilisant CKEditor 5 via django-ckeditor-5.
    Icône d’admin: doc-full
    """

    def __init__(self, *args, **kwargs):
        config_name = kwargs.pop("config_name", "default")
        if _CKEditor5Widget is None:
            raise ImportError(
                "django_ckeditor_5 n'est pas installé. Ajoutez 'django-ckeditor-5' aux dépendances."
            )
        self.field = forms.CharField(
            required=False,
            widget=_CKEditor5Widget(config_name=config_name),
        )
        super().__init__(*args, **kwargs)

    def get_searchable_content(self, value):
        from django.utils.html import strip_tags

        return [strip_tags(value)] if value else []

    class Meta:
        icon = "doc-full"
        label = "CKEditor 5"
        help_text = "Contenu HTML édité avec CKEditor 5"
        form_classname = "full"


# Alias rétro-compatible pour les anciennes migrations/pages
# Permet d'éviter AttributeError: 'CKEditorBlock' absent
CKEditorBlock = CKEditor5Block


