"""
Vues pour la gestion des paramètres d'exercices
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.shortcuts import render
from wagtail.models import Page
from .models import ParametreExoPage, ParamItem


@require_http_methods(["POST"])
@csrf_exempt
def rescan_parent(request, page_id):
    """
    Vue pour rescanner l'exercice parent et détecter les paramètres
    """
    try:
        print(f"DEBUG: Vue rescan_parent appelée avec page_id={page_id}")
        
        page = Page.objects.get(id=page_id).specific
        print(f"DEBUG: Page trouvée: {type(page).__name__}")
        
        if not isinstance(page, ParametreExoPage):
            print(f"DEBUG: Page n'est pas une ParametreExoPage")
            return JsonResponse({'error': 'Page invalide'}, status=400)
        
        print(f"DEBUG: Page est une ParametreExoPage valide")
        
        # Lancer l'auto-scan
        print(f"DEBUG: Lancement auto-scan pour page {page.id}")
        result = page.autoscan_create_missing()
        print(f"DEBUG: Résultat auto-scan: {result}")
        
        # Préparer le message
        if result['added'] > 0:
            messages.success(request, f"✅ {result['added']} nouveau(x) paramètre(s) détecté(s) et créé(s)")
        if result['updated'] > 0:
            messages.info(request, f"🔄 {result['updated']} paramètre(s) remis à jour")
        if result['orphaned'] > 0:
            messages.warning(request, f"⚠️ {result['orphaned']} paramètre(s) marqué(s) comme orphelin(s)")
        if result['added'] == 0 and result['updated'] == 0 and result['orphaned'] == 0:
            messages.info(request, "ℹ️ Aucun changement détecté")
        
        return JsonResponse({
            'success': True,
            'result': result
        })
        
    except Page.DoesNotExist:
        print(f"DEBUG: Page {page_id} non trouvée")
        return JsonResponse({'error': 'Page non trouvée'}, status=404)
    except Exception as e:
        print(f"DEBUG: Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@csrf_exempt
def preview_variant(request, page_id):
    """
    Vue pour prévisualiser une variante d'exercice
    TODO: Implémenter la logique complète
    """
    try:
        page = Page.objects.get(id=page_id).specific
        if not isinstance(page, ParametreExoPage):
            return JsonResponse({'error': 'Page invalide'}, status=400)
        
        # Récupérer les paramètres
        variant_index = request.GET.get('variant', 1)
        seed = request.GET.get('seed', '')
        
        try:
            variant_index = int(variant_index)
        except ValueError:
            variant_index = 1
        
        # TODO: Appeler page.build_context_for_variant()
        # context = page.build_context_for_variant(variant_index, seed)
        
        # Pour l'instant, retourner un contexte vide
        context = {
            'variant_index': variant_index,
            'seed': seed,
            'params': {},
            'warnings': []
        }
        
        return JsonResponse(context)
        
    except Page.DoesNotExist:
        return JsonResponse({'error': 'Page non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def validate_params(request, page_id):
    """
    Vue pour valider les paramètres
    TODO: Implémenter la logique complète
    """
    try:
        page = Page.objects.get(id=page_id).specific
        if not isinstance(page, ParametreExoPage):
            return JsonResponse({'error': 'Page invalide'}, status=400)
        
        # TODO: Appeler page.validate_sync_lengths()
        # errors = page.validate_sync_lengths()
        
        # Pour l'instant, retourner une liste vide d'erreurs
        errors = []
        
        return JsonResponse({'errors': errors})
        
    except Page.DoesNotExist:
        return JsonResponse({'error': 'Page non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def ping(request):
    """Vue de test simple pour vérifier que les URLs fonctionnent"""
    return JsonResponse({'message': 'pong', 'status': 'ok'})


def test_content_extraction(request, page_id):
    """
    Vue de test pour vérifier l'extraction du contenu
    """
    try:
        print(f"DEBUG: Test extraction pour page_id={page_id}")
        
        if not page_id or page_id == 0:
            return JsonResponse({'error': 'Page ID invalide'}, status=400)
        
        page = Page.objects.get(id=page_id).specific
        print(f"DEBUG: Page trouvée: {type(page).__name__}")
        
        if not isinstance(page, ParametreExoPage):
            return JsonResponse({'error': 'Page invalide - doit être une ParametreExoPage'}, status=400)
        
        # Tester l'extraction du contenu
        content = page.gather_parent_text()
        
        return JsonResponse({
            'success': True,
            'content_length': len(content),
            'content_preview': content[:1000],
            'parent_title': page.get_parent().title if page.get_parent() else 'Aucun parent',
            'page_id': page_id,
            'page_type': type(page).__name__
        })
        
    except Page.DoesNotExist:
        return JsonResponse({'error': f'Page {page_id} non trouvée'}, status=404)
    except Exception as e:
        print(f"DEBUG: Exception dans test_content_extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def param_config(request, param_id):
    """
    Charge le ParamItem, lit kind si passé en querystring,
    rend le fragment _param_type_fields.html avec les champs selon le type.
    """
    try:
        param = ParamItem.objects.get(id=param_id)
        kind = request.GET.get('kind', param.kind)

        # Pour rendre le bon fragment selon le type demandé
        param.kind = kind

        return render(request, 'exo/_param_type_fields.html', {
            'param': param
        })

    except ParamItem.DoesNotExist:
        return JsonResponse({'error': 'Paramètre non trouvé'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def param_sync(request, param_id):
    """
    Met à jour la synchronisation d'un paramètre.
    """
    try:
        param = ParamItem.objects.get(id=param_id)
        import json
        data = json.loads(request.body)
        sync_enabled = data.get('sync_enabled', False)

        param.sync_enabled = sync_enabled
        param.save()

        return JsonResponse({'success': True})

    except ParamItem.DoesNotExist:
        return JsonResponse({'error': 'Paramètre non trouvé', 'success': False}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def param_name(request, param_id):
    """
    Met à jour le nom d'un paramètre.
    """
    try:
        param = ParamItem.objects.get(id=param_id)
        import json
        data = json.loads(request.body)
        name = data.get('name', '').strip()

        if not name:
            return JsonResponse({'error': 'Le nom ne peut pas être vide', 'success': False})

        if len(name) > 10:
            return JsonResponse({'error': 'Le nom ne peut pas dépasser 10 caractères', 'success': False})

        param.name = name
        param.save()

        return JsonResponse({'success': True})

    except ParamItem.DoesNotExist:
        return JsonResponse({'error': 'Paramètre non trouvé', 'success': False}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def param_field(request, param_id):
    """
    Met à jour un champ spécifique d'un paramètre.
    """
    try:
        param = ParamItem.objects.get(id=param_id)
        import json
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')

        if not field:
            return JsonResponse({'error': 'Champ non spécifié', 'success': False})

        # Champs autorisés pour la mise à jour
        allowed_fields = [
            'const_value', 'range_min', 'range_max', 'range_step',
            'set_text', 'slot_default', 'expr_code',
            'tableau_orientation', 'tableau_header', 'tableau_rows'
        ]

        if field not in allowed_fields:
            return JsonResponse({'error': 'Champ non autorisé', 'success': False})

        # Validation basique selon le type de champ
        if field in ['range_min', 'range_max', 'range_step']:
            if value is not None and value != '':
                try:
                    value = float(value)
                except ValueError:
                    return JsonResponse({'error': 'Valeur numérique invalide', 'success': False})

        setattr(param, field, value)
        param.save()

        return JsonResponse({'success': True})

    except ParamItem.DoesNotExist:
        return JsonResponse({'error': 'Paramètre non trouvé', 'success': False}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=500)


@require_http_methods(["GET"])
def validate_params(request, page_id):
    """
    Appelle validate_sync_coherence() et renvoie la liste d'erreurs.
    """
    try:
        page = Page.objects.get(id=page_id).specific
        if not isinstance(page, ParametreExoPage):
            return JsonResponse({'error': 'Page invalide'}, status=400)

        errors = page.validate_sync_coherence()

        return JsonResponse({'errors': errors})

    except Page.DoesNotExist:
        return JsonResponse({'error': 'Page non trouvée'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

