#!/usr/bin/env python3
"""Esconde a opcao 'Whisper API' do seletor de transcricao no console.

Esta distribuicao usa apenas o Whisper LOCAL, entao a opcao de endpoint
Whisper API (OpenAI-compativel) so confunde. Removemos o elemento da opcao
``value:"whisper_api"`` do bundle do console (ProviderTypeCard), mantendo
'Desativado' e 'Whisper local'.

O console vem minificado (nomes de variaveis curtos que mudam a cada build),
entao casamos por REGEX ancorada nas strings estaveis (``value:"whisper_api"``
... ``providerTypeWhisperApiDesc``), tolerando os nomes minificados.
Idempotente. Nao-fatal: se o padrao nao existir (upstream mudou o console),
apenas avisa — nao quebra o build. Rode com ``--dry-run`` para so inspecionar.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERN = re.compile(
    r'\w+\.jsxs\(\w+,\{value:"whisper_api",children:\['
    r'.*?providerTypeWhisperApiDesc"\)\}\)\]\}\),',
    re.DOTALL,
)
MARKER = 'value:"whisper_api"'


def _assets_dir() -> Path:
    import qwenpaw  # noqa: WPS433

    return Path(qwenpaw.__file__).parent / "console" / "assets"


def main() -> int:
    dry = "--dry-run" in sys.argv
    assets = _assets_dir()
    if not assets.is_dir():
        print(f"[patch-whisperapi] AVISO: console nao encontrado ({assets}); pulando.")
        return 0

    patched = 0
    for js in sorted(assets.glob("*.js")):
        try:
            text = js.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        if MARKER not in text:
            continue
        match = PATTERN.search(text)
        if not match:
            continue
        new = PATTERN.sub("", text, count=1)
        if dry:
            print(f"[dry-run] {js.name}: removeria {len(match.group(0))} chars")
            print("  keeps local_whisper:", 'value:"local_whisper"' in new,
                  "| keeps disabled:", 'value:"disabled"' in new,
                  "| whisper_api gone:", 'value:"whisper_api"' not in new)
            patched += 1
            continue
        if new != text:
            js.write_text(new, encoding="utf-8")
            patched += 1
            print(f"[patch-whisperapi] OK: opcao Whisper API removida de {js.name}")

    if patched == 0:
        print(
            "[patch-whisperapi] AVISO: opcao Whisper API nao encontrada para "
            "remover (upstream pode ter mudado o console). Sem alteracoes.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
