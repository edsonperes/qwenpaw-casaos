#!/usr/bin/env python3
"""Corrige a selecao de idioma pt-BR no console do QwenPaw.

Bug do console oficial: a config do i18next usa ``nonExplicitSupportedLngs: true``
junto com ``supportedLngs`` contendo ``"pt-BR"``. Com isso, ao escolher
"Portugues (Brasil)" o i18next tenta resolver a base ``"pt"`` (que nao existe
nos resources, so ``"pt-BR"``) e cai no fallback ingles. Idiomas sem regiao
(en/zh/ja/ru) nao sao afetados. Reproduzido e confirmado com i18next isolado:
remover ``nonExplicitSupportedLngs`` conserta o pt-BR e mantem os demais.

Como o console e distribuido ja minificado, trocamos no bundle a forma
minificada ``nonExplicitSupportedLngs:!0`` (true) por ``:!1`` (false). Mesmo
numero de caracteres -> nao desalinha o arquivo. A lib i18next (i18n-vendor)
tem ``:!1`` por default e nao e tocada.

Nao e fatal: se o padrao nao existir (upstream corrigiu, ou a minificacao
mudou), apenas avisa — assim uma atualizacao do QwenPaw nunca quebra o build.
"""

from __future__ import annotations

import sys
from pathlib import Path

TARGET = "nonExplicitSupportedLngs:!0"
REPLACEMENT = "nonExplicitSupportedLngs:!1"


def _assets_dir() -> Path:
    import qwenpaw  # noqa: WPS433

    return Path(qwenpaw.__file__).parent / "console" / "assets"


def main() -> int:
    assets = _assets_dir()
    if not assets.is_dir():
        print(f"[patch-i18n] AVISO: pasta do console nao encontrada ({assets}); pulando.")
        return 0

    patched = 0
    for js in assets.glob("*.js"):
        try:
            text = js.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        if TARGET not in text:
            continue
        js.write_text(text.replace(TARGET, REPLACEMENT), encoding="utf-8")
        patched += 1
        print(f"[patch-i18n] OK: pt-BR corrigido em {js.name}")

    if patched == 0:
        print(
            "[patch-i18n] AVISO: padrao nao encontrado. O console upstream pode "
            "ter corrigido a selecao de idioma, ou a forma minificada mudou. "
            "Confirme o seletor pt-BR apos atualizar a imagem base.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
