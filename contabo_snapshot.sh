#!/usr/bin/env bash
set -euo pipefail

# ========= CONFIG =========
CLIENT_ID="INT-12224703"
CLIENT_SECRET="aOHoRyxLEjwpLSHJlOgXxrEUM1pBNzXH"   # ton vrai client_secret
API_USER="sciencesslsc@hotmail.fr"                                # ton identifiant client (pas email)
API_PASS="Manoubia1234."                        # ton mot de passe API
INSTANCE_ID="201404635"                            # trouvé via API

timestamp() { date +%Y%m%d-%H%M; }

# Vérifie que jq est installé
if ! command -v jq >/dev/null 2>&1; then
  echo "❌ jq n'est pas installé. Fais: sudo apt install jq"
  exit 1
fi

# 1) Obtenir un token d'accès
echo "🔑 Récupération du token API..."
TOKEN=$(curl -s -X POST "https://auth.contabo.com/auth/realms/contabo/protocol/openid-connect/token" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=$API_USER" \
  -d "password=$API_PASS" \
  -d "grant_type=password" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Impossible d'obtenir un token API"
  exit 1
fi
echo "✅ Token obtenu"

# 2) Vérifier si un snapshot existe déjà
REQ_ID=$(uuidgen)
SNAP_ID=$(curl -s -X GET "https://api.contabo.com/v1/compute/instances/$INSTANCE_ID/snapshots" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-request-id: $REQ_ID" | jq -r '.data[0].snapshotId // "null"')

# 3) Supprimer l'ancien snapshot si présent
if [ "$SNAP_ID" != "null" ]; then
  echo "🗑️ Suppression snapshot $SNAP_ID..."
  REQ_ID=$(uuidgen)
  curl -s -X DELETE "https://api.contabo.com/v1/compute/instances/$INSTANCE_ID/snapshots/$SNAP_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-request-id: $REQ_ID"
  echo "✅ Ancien snapshot supprimé"
fi

# 4) Créer un nouveau snapshot
SNAP_NAME="auto-snapshot-$(timestamp)"
REQ_ID=$(uuidgen)
echo "📸 Création nouveau snapshot: $SNAP_NAME"
RESULT=$(curl -s -X POST "https://api.contabo.com/v1/compute/instances/$INSTANCE_ID/snapshots" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-request-id: $REQ_ID" \
  -d '{"name":"'"$SNAP_NAME"'"}')

if echo "$RESULT" | grep -q '"snapshotId"'; then
  echo "✅ Snapshot $SNAP_NAME créé avec succès"
else
  echo "❌ Erreur lors de la création du snapshot:"
  echo "$RESULT"
  exit 1
fi
