#!/usr/bin/env bash
set -euo pipefail

# ========= Réglages =========
APP_DIR="/srv/pconline"
BACKUP_DIR="$APP_DIR/manual_backups"
VENV="$APP_DIR/.venv/bin"
SERVICE_GUNICORN="pconline-gunicorn"
SERVICE_NGINX="nginx"

# === Config PostgreSQL (à adapter si besoin) ===
: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGUSER:=postgres}"        # ex: "pconline"
: "${PGDATABASE:=pconline}"    # nom de ta base
# PGPASSWORD peut être exporté dans l’environnement pour éviter le prompt

timestamp() { date +%Y%m%d-%H%M%S; }
ask() {
  local prompt="$1"
  local default="${2:-y}"
  local reply
  read -r -p "$prompt [y/N] " reply || true
  reply="${reply:-$default}"
  [[ "$reply" =~ ^[Yy]$ ]]
}

echo "==> Snapshot PostgreSQL manuel"
mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"
TAG="snapshot-$(timestamp)"

# (optionnel) arrêter services le temps du backup
STOPPED=0
if ask "Arrêter $SERVICE_GUNICORN pendant la sauvegarde ? (recommandé)"; then
  sudo systemctl stop "$SERVICE_GUNICORN" || true
  STOPPED=1
fi
if ask "Arrêter $SERVICE_NGINX ?"; then
  sudo systemctl stop "$SERVICE_NGINX" || true
fi

# 1) CODE (git)
if [ -d ".git" ]; then
  echo "--> Git"
  if ask "Faire un commit des changements détectés ?"; then
    git add -A || true
    if ! git diff --cached --quiet; then
      git commit -m "snapshot: $TAG"
      echo "   Commit créé."
    else
      echo "   Rien à committer."
    fi
  fi
  git tag -f "$TAG" || true
  echo "   Tag: $TAG"
else
  echo "--> Git non initialisé (skip)."
fi

# 2) BASE DE DONNÉES (PostgreSQL)
echo "--> Sauvegarde DB PostgreSQL (pg_dump -Fc)"
OUT_DB="$BACKUP_DIR/pg-$TAG.dump"
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -Fc -f "$OUT_DB"
echo "   -> $OUT_DB"

# 3) MEDIAS
echo "--> Sauvegarde médias"
if [ -d "$APP_DIR/media" ]; then
  OUT_MEDIA="$BACKUP_DIR/media-$TAG.tar.gz"
  tar -czf "$OUT_MEDIA" -C "$APP_DIR" media
  echo "   -> $OUT_MEDIA"
else
  echo "   Dossier media/ introuvable (skip)."
fi

# 4) REQUIREMENTS
echo "--> Export requirements"
if [ -x "$VENV/pip" ]; then
  OUT_REQ="$BACKUP_DIR/requirements-$TAG.txt"
  "$VENV/pip" freeze > "$OUT_REQ"
  echo "   -> $OUT_REQ"
fi

# 5) ROTATION (garde 10 fichiers par type)
ls -1t "$BACKUP_DIR"/pg-*.dump         2>/dev/null | tail -n +11 | xargs -r rm -f
ls -1t "$BACKUP_DIR"/media-*.tar.gz    2>/dev/null | tail -n +11 | xargs -r rm -f
ls -1t "$BACKUP_DIR"/requirements-*.txt 2>/dev/null | tail -n +11 | xargs -r rm -f

# Redémarrage
if [ "$STOPPED" -eq 1 ]; then
  echo "--> Redémarrage services"
  sudo systemctl start "$SERVICE_GUNICORN" || true
fi
if systemctl is-enabled "$SERVICE_NGINX" >/dev/null 2>&1; then
  sudo systemctl start "$SERVICE_NGINX" || true
fi

echo "✅ Snapshot terminé: $TAG"
echo "   Dossier: $BACKUP_DIR"
