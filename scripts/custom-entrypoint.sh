#!/bin/sh
# Entrypoint do qwenpaw-casaos.
#
# Fluxo (apenas no primeiro boot, quando ainda nao ha config.json):
#   1. Grava um config.json minimo com o idioma-base em INGLES. Por que en:
#      os arquivos de personalidade (SOUL/PROFILE/AGENTS...) so existem em
#      en/zh; sem isso o init cai no default chines. E o HEARTBEAT quebra
#      (KeyError) se o idioma-base for pt-BR, entao a base precisa ser en/zh.
#   2. Roda o init: instala tudo em ingles (base neutra, sem texto chines).
#   3. seed_config.py troca o idioma de RESPOSTA para pt-BR (e liga a
#      transcricao local). A base fica en; o assistente responde em pt-BR.
#   4. Delega ao entrypoint OFICIAL, que sobe Xvfb/XFCE/dbus/supervisord/app.
#      Como o config.json ja existe, o oficial nao re-roda o init.
set -e

WORKING_DIR="${QWENPAW_WORKING_DIR:-/app/working}"
# Idioma-base dos arquivos de personalidade (en ou zh; en e o mais neutro).
BOOTSTRAP_LANG="${QWENPAW_BOOTSTRAP_MD_LANGUAGE:-en}"

if [ ! -f "${WORKING_DIR}/config.json" ]; then
  echo "[casaos-entrypoint] Primeiro boot: idioma-base '${BOOTSTRAP_LANG}' antes do init."
  mkdir -p "${WORKING_DIR}"
  printf '{"agents":{"language":"%s"}}' "${BOOTSTRAP_LANG}" > "${WORKING_DIR}/config.json"
  echo "[casaos-entrypoint] Inicializando..."
  qwenpaw init --defaults --accept-security
fi

# Aplica pt-BR (resposta) + transcricao local. Nunca derruba o boot.
python3 /opt/qwenpaw-casaos/seed_config.py \
  || echo "[casaos-entrypoint] AVISO: seed_config.py falhou; seguindo assim mesmo."

# Aviso de seguranca: senha ainda no valor padrao em servico exposto.
if [ "${QWENPAW_AUTH_ENABLED:-}" = "true" ] && \
   [ "${QWENPAW_AUTH_PASSWORD:-}" = "troque-esta-senha" ]; then
  echo "============================================================" >&2
  echo "[SEGURANCA] QWENPAW_AUTH_PASSWORD ainda e a senha PADRAO." >&2
  echo "Defina uma senha forte antes de expor o servico publicamente" >&2
  echo "(ex.: openssl rand -base64 24)." >&2
  echo "============================================================" >&2
fi

echo "[casaos-entrypoint] Delegando ao entrypoint oficial do QwenPaw..."
exec /entrypoint.sh
