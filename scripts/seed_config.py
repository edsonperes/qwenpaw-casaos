#!/usr/bin/env python3
"""Semeador de configuracao idempotente do qwenpaw-casaos.

Aplica os nossos padroes ao ``config.json`` que o ``qwenpaw init`` gera:

  * ``agents.language``                  -> QWENPAW_DEFAULT_LANGUAGE (default pt-BR)
  * ``agents.audio_mode``                -> "auto" (transcreve audio recebido)
  * ``agents.transcription_provider_type`` -> QWENPAW_TRANSCRIPTION_TYPE
                                            (default local_whisper)
  * loop.rubric.enabled (por agente)     -> False (evita RESPOSTA
                                            DUPLICADA no Telegram; roda
                                            todo boot, opt-out via
                                            QWENPAW_ALLOW_TEXT_REPROMPT)

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


def _find_loop_blocks(obj):
    """Gera os dicts que parecem um bloco de loop-gates (tem rubric + iteration)."""
    if isinstance(obj, dict):
        if isinstance(obj.get("rubric"), dict) and "iteration" in obj:
            yield obj
        for value in obj.values():
            yield from _find_loop_blocks(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _find_loop_blocks(value)


def enforce_single_reply(working_dir: Path) -> None:
    """Desliga o gate ``rubric`` (re-prompt em resposta so-texto) em cada agente.

    Esse gate reenvia o agente depois de uma resposta de texto -> no Telegram
    isso vira mensagem DUPLICADA. O default do proprio QwenPaw (config.json
    global) ja vem desligado, mas alguns ``agent.json`` chegam com ele ligado.
    Alinhamos aqui, a CADA boot (nao e travado pelo marcador de seed).

    Opt-out: ``QWENPAW_ALLOW_TEXT_REPROMPT=true``.
    """
    if _truthy(os.environ.get("QWENPAW_ALLOW_TEXT_REPROMPT")):
        _log("QWENPAW_ALLOW_TEXT_REPROMPT=true; mantendo o gate 'rubric' como esta.")
        return

    workspaces = working_dir / "workspaces"
    for agent_file in sorted(workspaces.glob("*/agent.json")):
        try:
            cfg = json.loads(agent_file.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - nunca derrubar o boot
            _log(f"AVISO: nao consegui ler {agent_file} ({exc}); pulando.")
            continue

        changed = False
        for loop in _find_loop_blocks(cfg):
            rubric = loop.get("rubric")
            if isinstance(rubric, dict) and rubric.get("enabled") is not False:
                rubric["enabled"] = False
                changed = True

        if not changed:
            continue
        try:
            _atomic_write(
                agent_file,
                json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
            )
            _log(
                "rubric desligado (anti-duplicacao) em "
                f"{agent_file.parent.name}/agent.json",
            )
        except Exception as exc:  # noqa: BLE001
            _log(f"AVISO: falha ao gravar {agent_file} ({exc}).")


def main() -> int:
    language = os.environ.get("QWENPAW_DEFAULT_LANGUAGE", "pt-BR").strip()
    transcription = os.environ.get(
        "QWENPAW_TRANSCRIPTION_TYPE", "local_whisper",
    ).strip()
    force = _truthy(os.environ.get("QWENPAW_SEED_FORCE"))

    # Anti-duplicacao: roda SEMPRE (mesmo apos ja semeado), pois nao depende
    # do marcador — desliga o gate 'rubric' que duplica respostas no Telegram.
    enforce_single_reply(WORKING_DIR)

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
