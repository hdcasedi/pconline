from django.db import migrations


def rename_block_in_streamfield(value):
    """
    Parcourt récursivement un StreamField JSON (use_json_field=True) et remplace
    les anciens noms de blocs 'CKEditorBlock' par 'CKEditor5Block'.
    """
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                block_type = item.get("type")
                if block_type == "CKEditorBlock":
                    item = {**item, "type": "CKEditor5Block"}
                # Traite un éventuel contenu imbriqué
                if "value" in item:
                    item_value = item["value"]
                    item["value"] = rename_block_in_streamfield(item_value)
            result.append(item)
        return result
    elif isinstance(value, dict):
        return {k: rename_block_in_streamfield(v) for k, v in value.items()}
    else:
        return value


def forwards(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    for page in HomePage.objects.all().iterator():
        body = page.body
        if not body:
            continue
        new_body = rename_block_in_streamfield(body)
        if new_body != body:
            page.body = new_body
            # Sauvegarde sans créer de nouvelle révision de page
            page.save(update_fields=["body"])


def reverse_code(apps, schema_editor):
    # Optionnel: revenir en arrière (CKEditor5Block -> CKEditorBlock)
    HomePage = apps.get_model("home", "HomePage")
    for page in HomePage.objects.all().iterator():
        body = page.body
        if not body:
            continue
        # inversion simple
        def revert(value):
            if isinstance(value, list):
                result = []
                for item in value:
                    if isinstance(item, dict):
                        if item.get("type") == "CKEditor5Block":
                            item = {**item, "type": "CKEditorBlock"}
                        if "value" in item:
                            item["value"] = revert(item["value"])
                    result.append(item)
                return result
            elif isinstance(value, dict):
                return {k: revert(v) for k, v in value.items()}
            else:
                return value

        new_body = revert(body)
        if new_body != body:
            page.body = new_body
            page.save(update_fields=["body"])


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0003_homepage_body"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=reverse_code),
    ]



