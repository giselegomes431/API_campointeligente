# Generated by Django 5.2.4 on 2025-07-25 19:05

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0004_state'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='administrador',
            name='senha_hash',
        ),
        migrations.AddField(
            model_name='administrador',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='administrador_profile', to=settings.AUTH_USER_MODEL),
        ),
    ]
