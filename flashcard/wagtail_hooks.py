from wagtail import hooks
from django.db import transaction


@hooks.register("after_publish_page")
def flashcard_auto_import_after_publish(request, page):
    """
    À la publication :
    - si c'est une FlashcardSetPage,
    - si auto_import_on_publish est actif,
    - si un fichier source est présent,
    => import, puis suppression du fichier UNIQUEMENT si created > 0.
    """
    from .models import FlashcardSetPage

    # S'assurer d'être sur la page spécifique
    try:
        specific = page.specific
    except Exception:
        specific = page

    if not isinstance(specific, FlashcardSetPage):
        return
    if not getattr(specific, "auto_import_on_publish", True):
        return
    if not specific.source_file:
        print("[FLASHCARD IMPORT] Aucun fichier source attaché → pas d'import")
        return

    with transaction.atomic():
        try:
            created = specific.import_from_file()
            print(f"[FLASHCARD IMPORT] Publication page {specific.id} → {created} cartes créées")
        except Exception as e:
            print(f"[FLASHCARD IMPORT][ERREUR] Import échoué (page {specific.id}) : {e}")
            raise

        if created > 0:
            def _delete_doc():
                try:
                    specific.delete_source_file()
                    print(f"[FLASHCARD IMPORT] Fichier supprimé après import réussi (page {specific.id})")
                except Exception as e:
                    print(f"[FLASHCARD IMPORT][WARN] Échec suppression fichier (page {specific.id}) : {e}")
            transaction.on_commit(_delete_doc)
        else:
            print(f"[FLASHCARD IMPORT] 0 carte créée → fichier conservé (page {specific.id})")


