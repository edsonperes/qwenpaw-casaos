#!/usr/bin/env python3
"""Semeador de configuracao idempotente do qwenpaw-casaos.

Aplica os nossos padroes ao ``config.json`` que o ``qwenpaw init`` gera:

  * ``agents.language``                  -> QWENPAW_DEFAULT_LANGUAGE (default pt-BR)
  * ``agents.audio_mode``                -> "auto" (transcreve audio recebido)
  * ``agents.transcription_provider_type`` -> QWENPAW_TRANSCRIPTION_TYPE
                                            (default local_whisper)

Principios:
  * NAO recompila o QwenPaw. So mexe em campos publicos do config.json.
  * Roda UMA vez (grava um marcador). Depois disso, respeita mudancas que
    voce fizer manualmente pelo console. Force com QWENPAW_SEED_FORCE=true.
  * Nunca derruba o boot: qualquer erro aqui e apenas avisado, nao fatal.
  * Escrita atomica (arquivo temporario + replace) para nao corromper o
    config se algo falhar no meio.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WORKING_DIR = Path(os.environ.get("QWENPAW_WORKING_DIR", "/app/working"))
CONFIG_PATH = WORKING_DIR / "config.json"
MARKER_PATH = WORKING_DIR / ".qwenpaw_casaos_seeded"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _log(msg: str) -> None:
    print(f"[seed-config] {msg}", flush=True)


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)  # atomico no mesmo filesystem


def main() -> int:
    language = os.environ.get("QWENPAW_DEFAULT_LANGUAGE", "pt-BR").strip()
    transcription = os.environ.get(
        "QWENPAW_TRANSCRIPTION_TYPE", "local_whisper",
    ).strip()
    force = _truthy(os.environ.get("QWENPAW_SEED_FORCE"))

    if not CONFIG_PATH.exists():
        _log(f"config.json ainda nao existe em {CONFIG_PATH}; nada a fazer.")
        return 0

    if MARKER_PATH.exists() and not force:
        _log(
            "ja semeado anteriormente; respeitando a config atual "
            "(use QWENPAW_SEED_FORCE=true para reaplicar).",
        )
        return 0

    try:
        original = CONFIG_PATH.read_text(encoding="utf-8")
        cfg = json.loads(original)
    except Exception as exc:  # noqa: BLE001 - nunca derrubar o boot
        _log(f"AVISO: nao consegui ler o config.json ({exc}); seguindo sem semear.")
        return 0

    agents = cfg.setdefault("agents", {})
    if not isinstance(agents, dict):
        _log("AVISO: bloco 'agents' inesperado no config.json; seguindo sem semear.")
        return 0

    changed: list[str] = []

    if language and agents.get("language") != language:
        agents["language"] = language
        changed.append(f"language={language}")

    if agents.get("audio_mode") != "auto":
        agents["audio_mode"] = "auto"
        changed.append("audio_mode=auto")

    if transcription and agents.get("transcription_provider_type") != transcription:
        agents["transcription_provider_type"] = transcription
        changed.append(f"transcription_provider_type={transcription}")

    if changed:
        try:
            # backup leve do original antes da primeira escrita
            backup = CONFIG_PATH.with_suffix(".json.casaos.bak")
            if not backup.exists():
                _atomic_write(backup, original)
            _atomic_write(
                CONFIG_PATH,
                json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
            )
            _log("aplicado: " + ", ".join(changed))
        except Exception as exc:  # noqa: BLE001
            _log(f"AVISO: falha ao gravar config.json ({exc}); nada alterado.")
            return 0
    else:
        _log("nada a alterar (config ja estava conforme).")

    try:
        MARKER_PATH.write_text("seeded by qwenpaw-casaos\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass  # marcador e best-effort

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
