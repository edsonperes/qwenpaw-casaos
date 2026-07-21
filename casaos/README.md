# Importar o qwenpaw-casaos no CasaOS

O arquivo de instalação é o [`docker-compose.yml`](../docker-compose.yml) na raiz (já traz os metadados `x-casaos`).

## Instalação (Custom App)

1. Abra o **CasaOS → App Store**.
2. Clique no ícone **`+`** (canto superior direito) → **Install a customized app**.
3. Alterne para o modo de **importar Docker Compose** (o botão de "compose" / `</>` na janela) e cole todo o conteúdo do `docker-compose.yml`.
4. **Antes de salvar**, ajuste:
   - `image:` — troque `__GHCR_OWNER__` pelo seu usuário/organização do GitHub. Ex.: `ghcr.io/edson/qwenpaw-casaos:latest`.
   - `QWENPAW_AUTH_PASSWORD` — defina uma senha forte.
5. Clique em **Install**.

O CasaOS cria os dados em `/DATA/AppData/qwenpaw-casaos/` (subpastas `working`, `working.secret`, `working.backups`).

## Após instalar

- O ícone do QwenPaw aparece no painel; abre em `http://IP-DO-SERVIDOR:8088`.
- Faça login com `QWENPAW_AUTH_USERNAME` / `QWENPAW_AUTH_PASSWORD`.
- Primeira inicialização demora um pouco (o container roda `qwenpaw init` e aplica os padrões pt-BR + transcrição local).

## Se a imagem for privada no GHCR

Se você deixou o pacote no GHCR como **privado**, o CasaOS precisa autenticar para baixar. No terminal do servidor:

```bash
echo SEU_TOKEN_GHCR | docker login ghcr.io -u edsonperes --password-stdin
```

Ou torne o pacote **público** em GitHub → Packages → qwenpaw-casaos → Package settings → Change visibility.

## Atualizar pelo CasaOS

- **Settings do app → Update** (puxa a tag `latest` do GHCR e recria, preservando os volumes), ou
- pelo terminal: `cd` até o repositório e rode `./scripts/update.sh`.

## Recomendação de rede

Não exponha a porta `8088` direto na internet. Use o **reverse proxy** do CasaOS (ou Nginx Proxy Manager / Caddy) para servir por **HTTPS** com um domínio. A autenticação já está ligada, mas o TLS é essencial em acesso público.
