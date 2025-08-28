# Generated manually for cours app

from django.db import migrations, models
import django.db.models.deletion
import wagtail.fields
import wagtail.blocks


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wagtailcore', '0089_log_entry_data_json_null_to_object'),
        ('referentiel', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoursPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('contenu', wagtail.fields.StreamField([('paragraphe', wagtail.blocks.StructBlock([('style', wagtail.blocks.ChoiceBlock(choices=[('normal', 'Normal'), ('exemple', 'Exemple'), ('remarque', 'Remarque'), ('definition', 'Définition')], default='normal', label='Style')), ('alignement', wagtail.blocks.ChoiceBlock(choices=[('gauche', 'Gauche'), ('centre', 'Centré'), ('justifie', 'Justifié'), ('droite', 'Droite')], default='gauche', label='Alignement')), ('contenu', wagtail.blocks.RichTextBlock(features=['bold', 'italic', 'underline', 'link', 'superscript', 'subscript', 'strikethrough', 'ol', 'ul', 'hr', 'blockquote', 'code', 'image', 'embed'], label='Contenu')), ('titre', wagtail.blocks.CharBlock(label='Titre (pour remarque/définition)', required=False))], icon='doc-full', label='Paragraphe', template='cours/blocks/paragraphe.html')), ('titre', wagtail.blocks.StructBlock([('niveau', wagtail.blocks.ChoiceBlock(choices=[('h1', 'H1'), ('h2', 'H2'), ('h3', 'H3')], default='h1', label='Niveau')), ('texte', wagtail.blocks.CharBlock(label='Texte')), ('fiche_methode', wagtail.blocks.BooleanBlock(default=False, label='Afficher bouton fiche méthode')), ('texte_bouton', wagtail.blocks.CharBlock(default='Fiche méthode', label='Texte du bouton'))], icon='title', label='Titre', template='cours/blocks/titre.html')), ('tableau', wagtail.contrib.table_block.blocks.TableBlock()), ('code', wagtail.blocks.StructBlock([('langage', wagtail.blocks.ChoiceBlock(choices=[('python', 'Python'), ('javascript', 'JavaScript'), ('html', 'HTML'), ('css', 'CSS'), ('c', 'C'), ('cpp', 'C++'), ('java', 'Java'), ('php', 'PHP'), ('sql', 'SQL'), ('bash', 'Bash'), ('json', 'JSON'), ('xml', 'XML'), ('yaml', 'YAML'), ('markdown', 'Markdown')], default='python', label='Langage')), ('code', wagtail.blocks.TextBlock(label='Code'))], icon='code', label='Code', template='cours/blocks/code.html'))], use_json_field=True, verbose_name='Contenu')),
                ('chapitre', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cours', to='referentiel.chapitre', verbose_name='Chapitre')),
            ],
            options={
                'verbose_name': 'Cours',
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='CoursIndexPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
            ],
            options={
                'verbose_name': 'Index des cours',
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='CoursRootPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
            ],
            options={
                'verbose_name': 'Racine des cours',
            },
            bases=('wagtailcore.page',),
        ),
    ]
