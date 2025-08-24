#!/bin/bash
# Script de déploiement Wagtail/Django

cd /srv/pconline || exit

echo "🔹 Activation de l'environnement virtuel..."
source .venv/bin/activate

echo "🔹 Application des migrations..."
python manage.py migrate --noinput

echo "🔹 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "🔹 Redémarrage de Gunicorn..."
sudo systemctl restart pconline

echo "🔹 Rechargement de Nginx..."
sudo systemctl reload nginx

echo "✅ Déploiement terminé !"
