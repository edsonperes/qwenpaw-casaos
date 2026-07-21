#!/usr/bin/env bash
# Atualiza o deploy do qwenpaw-casaos para a imagem mais recente.
#
# Fluxo padrao (imagem vinda do GHCR, buildada pelo GitHub Actions):
#   1. Baixa a imagem nova publicada no GHCR.
#   2. Recria o container preservando os volumes (dados/config/sessoes).
#
# Para gerar uma imagem NOVA a partir de uma versao mais recente do QwenPaw
# oficial, rode o workflow "build" no GitHub (Actions -> Run workflow) — ele
# puxa agentscope/qwenpaw:latest, reaplica a camada fina e publica no GHCR.
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

echo "==> Baixando imagem mais recente..."
docker compose -f "$COMPOSE_FILE" pull

echo "==> Recriando o container (volumes preservados)..."
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Limpando imagens antigas orfas..."
docker image prune -f >/dev/null 2>&1 || true

echo "==> Pronto. Logs: docker compose -f $COMPOSE_FILE logs -f"
