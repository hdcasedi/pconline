# Generated manually for cours app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0002_add_niveau_to_coursindexpage'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursrootpage',
            name='intro',
            field=models.TextField(
                blank=True,
                help_text='Texte d\'introduction pour la page des cours',
                verbose_name='Introduction'
            ),
        ),
    ]




