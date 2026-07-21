#!/usr/bin/env python3
"""Fixa o idioma na transcricao local do Whisper (evita erro de autodeteccao).

Por padrao o QwenPaw chama ``model.transcribe(file_path)`` sem ``language``, e o
Whisper tenta adivinhar o idioma — em audios curtos ele erra e transcreve como
se fosse outra lingua. Como esta distribuicao e pt-BR, fixamos o idioma.

Prioridade: ``QWENPAW_WHISPER_LANGUAGE`` (ex.: ``pt``); senao deriva de
``QWENPAW_DEFAULT_LANGUAGE`` (``pt-BR`` -> ``pt``). Vazio ou ``auto`` = mantem a
autodeteccao. Patch cirurgico em ``_transcribe_local_whisper._run``. Idempotente.
Nao-fatal no build so se o alvo sumir (retorna erro -> build avisa).
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "[casaos-lang-patch]"

TARGET = (
    "    def _run():\n"
    "        model = _get_local_whisper_model()\n"
    "        result = model.transcribe(file_path)\n"
    "        return (result.get(\"text\") or \"\").strip()\n"
)

REPLACEMENT = (
    "    def _run():\n"
    "        model = _get_local_whisper_model()\n"
    "        # [casaos-lang-patch] Fixa o idioma (autodetect erra em audio curto).\n"
    "        # QWENPAW_WHISPER_LANGUAGE tem prioridade; senao deriva de\n"
    "        # QWENPAW_DEFAULT_LANGUAGE (ex.: 'pt-BR' -> 'pt'). Vazio/'auto' = detecta.\n"
    "        import os as _os\n"
    "        _lang = _os.environ.get(\"QWENPAW_WHISPER_LANGUAGE\", \"\").strip()\n"
    "        if not _lang:\n"
    "            _base = _os.environ.get(\"QWENPAW_DEFAULT_LANGUAGE\", \"\").strip()\n"
    "            _lang = _base.replace(\"_\", \"-\").split(\"-\")[0].lower() if _base else \"\"\n"
    "        _kwargs = {\"language\": _lang} if _lang and _lang.lower() != \"auto\" else {}\n"
    "        result = model.transcribe(file_path, **_kwargs)\n"
    "        return (result.get(\"text\") or \"\").strip()\n"
)


def _target_file() -> Path:
    import qwenpaw.agents.utils.audio_transcription as mod  # noqa: WPS433

    return Path(mod.__file__)


def main() -> int:
    path = _target_file()
    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"[patch-lang] ja aplicado em {path}")
        return 0
    if TARGET not in src:
        print(
            "[patch-lang] ERRO: trecho-alvo nao encontrado em\n"
            f"  {path}\n"
            "O QwenPaw upstream mudou audio_transcription.py. "
            "Revise scripts/patch_whisper_language.py antes de atualizar a base.",
            file=sys.stderr,
        )
        return 1
    path.write_text(src.replace(TARGET, REPLACEMENT), encoding="utf-8")
    print(f"[patch-lang] OK: idioma fixado na transcricao local em {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
