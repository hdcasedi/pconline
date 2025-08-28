# Generated manually for cours app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('referentiel', '0001_initial'),
        ('cours', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursindexpage',
            name='niveau',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cours_index_pages',
                to='referentiel.niveau',
                verbose_name='Niveau',
                null=True
            ),
        ),
    ]




