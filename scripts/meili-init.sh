#!/bin/sh
set -e

DIM="${EMBED_DIM:-384}"
API="http://meilisearch:7700"
KEY="${MEILI_KEY}"

echo "Creating indexes and applying settings..."

curl -v -X POST "$API/indexes" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"uid":"documents","primaryKey":"id"}' || true

curl -v -X POST "$API/indexes" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"uid":"chunks","primaryKey":"id"}' || true

JSON_PAYLOAD="{\"embedders\":{\"default\":{\"source\":\"userProvided\",\"dimensions\":$DIM}},\"searchableAttributes\":[\"content\",\"title\"],\"displayedAttributes\":[\"id\",\"content\",\"title\",\"metadata\",\"source\",\"tags\"],\"filterableAttributes\":[\"source\",\"tags\",\"metadata.sha\",\"metadata.lang\"],\"sortableAttributes\":[\"created_at\",\"updated_at\"]}"

curl -v -X PATCH "$API/indexes/documents/settings" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" || true

curl -v -X PATCH "$API/indexes/chunks/settings" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" || true

echo "✅ Meilisearch initialization completed."
