#!/usr/bin/env python3
"""Torna o modelo do Whisper local configuravel por variavel de ambiente.

O QwenPaw oficial fixa o modelo em ``whisper.load_model("base")`` dentro de
``qwenpaw/agents/utils/audio_transcription.py``. Este patch cirurgico troca
essa unica linha para ler de ``QWENPAW_WHISPER_MODEL`` (default ``base``),
sem tocar em mais nada do codigo-fonte.

Por que assim (e nao um fork): manter a divergencia em UMA linha significa que
atualizar o QwenPaw = so trocar a tag da imagem base. Se o upstream mudar
justamente esse trecho, o patch NAO encontra o alvo e o build FALHA de
proposito — assim voce descobre na hora da atualizacao, em vez de silenciosamente
rodar com um patch quebrado.

Idempotente: rodar de novo depois de aplicado nao faz nada.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bloco exato do upstream (indentacao de 8 espacos, linha em branco no meio).
TARGET = (
    '        import whisper\n'
    '\n'
    '        _local_whisper_model = whisper.load_model("base")\n'
)

# Substituicao: importa os e le o modelo da env, com "base" como fallback.
REPLACEMENT = (
    '        import os\n'
    '        import whisper\n'
    '\n'
    '        _local_whisper_model = whisper.load_model(\n'
    '            os.environ.get("QWENPAW_WHISPER_MODEL", "base")\n'
    '        )\n'
)


def _target_file() -> Path:
    """Localiza audio_transcription.py no pacote instalado."""
    import qwenpaw.agents.utils.audio_transcription as mod  # noqa: WPS433

    return Path(mod.__file__)


def main() -> int:
    path = _target_file()
    src = path.read_text(encoding="utf-8")

    if REPLACEMENT in src:
        print(f"[patch-whisper] ja aplicado em {path}")
        return 0

    if TARGET not in src:
        print(
            "[patch-whisper] ERRO: bloco alvo nao encontrado em\n"
            f"  {path}\n"
            "O QwenPaw upstream provavelmente alterou audio_transcription.py.\n"
            "Revise scripts/patch_whisper_model.py antes de atualizar a imagem base.",
            file=sys.stderr,
        )
        return 1

    path.write_text(src.replace(TARGET, REPLACEMENT), encoding="utf-8")
    print(
        f"[patch-whisper] OK: modelo do Whisper agora vem de "
        f"QWENPAW_WHISPER_MODEL em {path}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
