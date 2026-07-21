#!/usr/bin/env python3
"""Transcreve voz/audio do Telegram para texto (corrige 'repete a ultima resposta').

Bug: o canal do Telegram baixa a voz e cria um bloco ``AudioContent`` com o
caminho do arquivo. O modelo padrao do QwenPaw e de TEXTO (nao le audio) e o
pipeline nao transcreve esse bloco -> o modelo nao recebe as palavras e o agente
repete a ultima resposta de texto.

Correcao cirurgica em ``_build_content_parts_from_message`` (canal Telegram):
logo apos baixar o arquivo de voz/audio, transcrevemos com o backend configurado
(``transcription_provider_type``, ex.: local_whisper) e anexamos um
``TextContent`` "[Voice message]: <texto>" em vez do bloco de audio. Se a
transcricao falhar, mantem o bloco de midia original (comportamento antigo).

Idempotente. Falha de proposito se o upstream mudar o trecho-alvo.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "[casaos-audio-patch]"

TARGET = (
    '        if local_path:\n'
    '            file_url = Path(local_path).resolve().as_uri()\n'
    '            content_parts.append(\n'
    '                content_cls(type=content_type, **{url_field: file_url}),\n'
    '            )\n'
)

REPLACEMENT = (
    '        if local_path:\n'
    '            file_url = Path(local_path).resolve().as_uri()\n'
    '            # [casaos-audio-patch] Voz/audio -> transcreve para texto, para o\n'
    '            # modelo (texto) receber as palavras em vez de repetir a ultima\n'
    '            # resposta. Respeita transcription_provider_type (ex: local_whisper).\n'
    '            # Se falhar, mantem o bloco de midia original.\n'
    '            if content_type == ContentType.AUDIO:\n'
    '                _casaos_text = None\n'
    '                try:\n'
    '                    from qwenpaw.agents.utils.audio_transcription import (\n'
    '                        transcribe_audio as _casaos_tx,\n'
    '                    )\n'
    '                    _casaos_text = await _casaos_tx(local_path)\n'
    '                except Exception:\n'
    '                    logger.warning(\n'
    '                        "[casaos-audio-patch] transcription failed for %s",\n'
    '                        local_path, exc_info=True,\n'
    '                    )\n'
    '                if _casaos_text:\n'
    '                    content_parts.append(\n'
    '                        TextContent(\n'
    '                            type=ContentType.TEXT,\n'
    '                            text="[Voice message]: " + _casaos_text,\n'
    '                        ),\n'
    '                    )\n'
    '                    continue\n'
    '            content_parts.append(\n'
    '                content_cls(type=content_type, **{url_field: file_url}),\n'
    '            )\n'
)


def _target_file() -> Path:
    import qwenpaw.app.channels.telegram.channel as mod  # noqa: WPS433

    return Path(mod.__file__)


def main() -> int:
    path = _target_file()
    src = path.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"[patch-audio] ja aplicado em {path}")
        return 0

    if TARGET not in src:
        print(
            "[patch-audio] ERRO: trecho-alvo nao encontrado em\n"
            f"  {path}\n"
            "O QwenPaw upstream provavelmente mudou o canal Telegram.\n"
            "Revise scripts/patch_audio_pipeline.py antes de atualizar a imagem base.",
            file=sys.stderr,
        )
        return 1

    path.write_text(src.replace(TARGET, REPLACEMENT), encoding="utf-8")
    print(f"[patch-audio] OK: transcricao de voz do Telegram habilitada em {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
