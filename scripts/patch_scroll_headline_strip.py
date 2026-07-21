#!/usr/bin/env python3
"""Impede que a 'headline' do scroll vaze no chat quando vem sem colchetes.

A estrategia de contexto 'scroll' pede que o modelo termine cada resposta com
uma headline num comentario HTML ``<!-- ⟦ … ⟧ -->``. O renderer chama
``strip_headline`` pra esconder isso na exibicao — MAS o regex so casa quando ha
os colchetes ⟦ ⟧. Modelos pequenos (ex.: nemotron-nano) as vezes emitem
``<!-- acknowledging user thanks -->`` sem os colchetes, e isso vaza (aparece no
Telegram).

Este patch amplia ``strip_headline`` (SO exibicao) com uma rede de seguranca:
remove tambem um comentario HTML de UMA linha grudado no fim da mensagem, mesmo
sem colchetes. Nao toca em ``extract_headline`` (indexacao/memoria continua
igual). Idempotente; falha o build so se o alvo sumir.
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "[casaos-headline-patch]"

TARGET = (
    "    m = _HEADLINE_RE.search(text)\n"
    "    if not m or not m.group(1).strip():\n"
    "        return text\n"
    "    start, end = m.span()  # one line: ``.`` never crosses a newline\n"
    "    cleaned = text[:start] + text[end:]\n"
    "    cleaned = re.sub(r\"\\n{3,}\", \"\\n\\n\", cleaned)  # collapse blank line left\n"
    "    return cleaned.strip()\n"
)

REPLACEMENT = (
    "    m = _HEADLINE_RE.search(text)\n"
    "    if m and m.group(1).strip():\n"
    "        start, end = m.span()  # one line: ``.`` never crosses a newline\n"
    "        text = text[:start] + text[end:]\n"
    "        text = re.sub(r\"\\n{3,}\", \"\\n\\n\", text)  # collapse blank line left\n"
    "        text = text.strip()\n"
    "    # [casaos-headline-patch] Rede de seguranca: modelos pequenos as vezes\n"
    "    # emitem a headline como comentario HTML SEM os colchetes (⟦ ⟧), que o\n"
    "    # _HEADLINE_RE nao pega e vaza no chat. Remove um comentario HTML de UMA\n"
    "    # linha grudado no FIM da mensagem (o formato da headline).\n"
    "    text = re.sub(r\"[ \\t]*(?:\\r?\\n)?[ \\t]*<!--[^\\n]*?-->[ \\t]*\\Z\", \"\", text)\n"
    "    return text.strip()\n"
)


def _target_file() -> Path:
    import qwenpaw.agents.context.scroll.serialize as mod  # noqa: WPS433

    return Path(mod.__file__)


def main() -> int:
    path = _target_file()
    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"[patch-headline] ja aplicado em {path}")
        return 0
    if TARGET not in src:
        print(
            "[patch-headline] ERRO: trecho-alvo nao encontrado em\n"
            f"  {path}\n"
            "O QwenPaw upstream mudou strip_headline. Revise "
            "scripts/patch_scroll_headline_strip.py antes de atualizar a base.",
            file=sys.stderr,
        )
        return 1
    path.write_text(src.replace(TARGET, REPLACEMENT), encoding="utf-8")
    print(f"[patch-headline] OK: limpeza de headline ampliada em {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
