# =============================================================================
# qwenpaw-casaos — camada fina sobre a imagem OFICIAL do QwenPaw.
#
# Filosofia: NAO recompilar o QwenPaw. Estendemos a imagem oficial com o minimo:
#   1) ffmpeg + openai-whisper  -> transcricao de audio LOCAL (Telegram etc.)
#   2) 1 linha de patch          -> modelo do Whisper configuravel por env
#
# Atualizar para uma versao nova do QwenPaw = trocar BASE_IMAGE e rebuildar.
# O build leva ~1-2 min (as camadas pesadas vem da base, ja cacheada).
#
# Build normal (CI/CasaOS):
#   docker build -t qwenpaw-casaos .
# Build atras de proxy/firewall com inspecao TLS (coloque o CA em certs/):
#   docker build --network=host \
#     --build-arg HTTPS_PROXY=http://PROXY:PORT --build-arg HTTP_PROXY=... -t ... .
# =============================================================================

# Fixe uma versao (ex.: agentscope/qwenpaw:v2.0.0.post3) para builds
# reproduziveis; :latest segue sempre o mais recente.
ARG BASE_IMAGE=agentscope/qwenpaw:latest
FROM ${BASE_IMAGE}

# Modelo do Whisper embutido na imagem (baixado no build). Trocavel em runtime
# por -e QWENPAW_WHISPER_MODEL=small (o novo modelo baixa no primeiro uso).
ARG WHISPER_MODEL=base

# venv onde o QwenPaw ja esta instalado (imagem oficial).
ENV PATH="/app/venv/bin:${PATH}"
ENV QWENPAW_WHISPER_MODEL=${WHISPER_MODEL}

# -----------------------------------------------------------------------------
# Suporte OPCIONAL a build atras de proxy/firewall com inspecao TLS.
#   * certs/ : em producao contem so .gitkeep -> este passo e no-op.
#              Atras de um proxy MITM, coloque o CA raiz (.crt) em certs/.
#   * HTTPS nos repos Debian: necessario quando o proxy so aceita CONNECT;
#     e inofensivo em builds normais (deb.debian.org tambem serve por HTTPS).
# -----------------------------------------------------------------------------
COPY certs/ /usr/local/share/ca-certificates/
RUN update-ca-certificates 2>/dev/null || true
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' \
      /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# -----------------------------------------------------------------------------
# 1) ffmpeg — o Whisper precisa dele para decodificar os audios recebidos.
# -----------------------------------------------------------------------------
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

# -----------------------------------------------------------------------------
# 2) torch (CPU-only) + openai-whisper no MESMO venv do app.
#    torch CPU-only evita ~2GB de dependencias CUDA que um mini-PC sem GPU
#    nunca usaria. PIP_CERT usa o bundle do sistema (que inclui eventuais CAs
#    corporativos instalados acima) — inocuo em builds normais.
# -----------------------------------------------------------------------------
RUN PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
      pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
      pip install --no-cache-dir openai-whisper

# -----------------------------------------------------------------------------
# 3) Pre-baixa o modelo do Whisper para dentro da imagem (funciona offline e o
#    primeiro audio nao espera download). Fica ANTES dos scripts para que
#    mudancas em scripts nao invalidem esta camada pesada.
# -----------------------------------------------------------------------------
RUN python3 -c "import os, whisper; whisper.load_model(os.environ.get('QWENPAW_WHISPER_MODEL', 'base'))"

# -----------------------------------------------------------------------------
# 4) Patches cirurgicos sobre a imagem oficial:
#    (a) modelo do Whisper vem de QWENPAW_WHISPER_MODEL (falha o build se o
#        alvo sumir — feature critica);
#    (b) conserta a selecao de idioma pt-BR no console (bug do i18next com
#        codigos de regiao; apenas avisa se o upstream ja tiver corrigido);
#    (c) transcreve voz/audio do Telegram para texto no canal (senao o
#        agente repetia a ultima resposta; falha o build se o alvo sumir);
#    (d) esconde a opcao 'Whisper API' do console (usamos so o local;
#        nao-fatal — so um ajuste de UI).
# -----------------------------------------------------------------------------
COPY scripts/patch_whisper_model.py /opt/qwenpaw-casaos/patch_whisper_model.py
COPY scripts/patch_console_i18n.py /opt/qwenpaw-casaos/patch_console_i18n.py
COPY scripts/patch_audio_pipeline.py /opt/qwenpaw-casaos/patch_audio_pipeline.py
COPY scripts/patch_console_hide_whisperapi.py /opt/qwenpaw-casaos/patch_console_hide_whisperapi.py
RUN python3 /opt/qwenpaw-casaos/patch_whisper_model.py \
 && python3 /opt/qwenpaw-casaos/patch_console_i18n.py \
 && python3 /opt/qwenpaw-casaos/patch_audio_pipeline.py \
 && python3 /opt/qwenpaw-casaos/patch_console_hide_whisperapi.py

# -----------------------------------------------------------------------------
# 5) Semeador de config + entrypoint customizado (camadas leves, no fim).
# -----------------------------------------------------------------------------
COPY scripts/seed_config.py /opt/qwenpaw-casaos/seed_config.py
COPY scripts/custom-entrypoint.sh /opt/qwenpaw-casaos/custom-entrypoint.sh
RUN chmod +x /opt/qwenpaw-casaos/custom-entrypoint.sh

# -----------------------------------------------------------------------------
# Defaults da nossa distribuicao (todos overridaveis pelo compose/.env).
# -----------------------------------------------------------------------------
ENV QWENPAW_DEFAULT_LANGUAGE=pt-BR \
    QWENPAW_TRANSCRIPTION_TYPE=local_whisper

EXPOSE 8088

ENTRYPOINT ["/opt/qwenpaw-casaos/custom-entrypoint.sh"]
