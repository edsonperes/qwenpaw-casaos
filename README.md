# qwenpaw-casaos

QwenPaw personalizado para rodar no **CasaOS**, mantendo-se **fácil de atualizar** a partir do projeto oficial.

Este repositório **não é um fork** do [QwenPaw](https://github.com/agentscope-ai/QwenPaw): é uma **camada fina** por cima da imagem oficial `agentscope/qwenpaw:latest`. Toda a personalização é feita por configuração + um patch mínimo, então atualizar = puxar a imagem oficial nova e reconstruir a casca (segundos).

## O que foi personalizado

| Personalização | Como é feito |
|---|---|
| **Português (PT-BR) por padrão** | Semeador aplica `language=pt-BR` no `config.json`; o console já detecta o idioma do navegador. |
| **Login e senha obrigatórios** | Autenticação nativa do QwenPaw via variáveis `QWENPAW_AUTH_*` (o sistema vai ficar exposto publicamente). |
| **Transcrição de áudio local** | `ffmpeg` + `openai-whisper` embutidos; `transcription_provider_type=local_whisper`. Áudios do **Telegram** viram texto automaticamente. |
| **Provedor de IA compatível com OpenAI** | Nativo: no console você informa host + token e ele lista os modelos. |
| **Empacotado para CasaOS** | `docker-compose.yml` com metadados `x-casaos`. |

O visual e o nome originais do QwenPaw foram mantidos.

## Como funciona (arquitetura)

```
agentscope/qwenpaw:latest  (imagem oficial, intocada)
        │
        ▼  Dockerfile (camada fina)
  + ffmpeg + openai-whisper (torch CPU-only)
  + patch de 1 linha: modelo do Whisper vem de env
  + seed_config.py  (pt-BR + transcrição local, idempotente)
  + custom-entrypoint.sh (init → seed → entrypoint oficial)
        │
        ▼
  ghcr.io/edsonperes/qwenpaw-casaos:latest
```

A divergência de código-fonte é de **uma única linha** (tornar o modelo do Whisper configurável), protegida por uma guarda: se o QwenPaw oficial mudar aquele trecho, o build falha de propósito para você revisar — nada roda silenciosamente quebrado.

## Pré-requisitos

- CasaOS em máquina **amd64** (o build padrão é amd64; veja o workflow para habilitar arm64).
- Uma chave/endpoint de um **provedor compatível com OpenAI** (você configura depois, no console).
- (Opcional) Um **bot do Telegram** — crie com o [@BotFather](https://t.me/BotFather) e guarde o token.

## Deploy no CasaOS

1. No CasaOS: **App Store → Custom Install** (ícone `+` / "Install a customized app").
2. Cole o conteúdo do `docker-compose.yml` **ou** importe o arquivo.
3. Ajuste antes de salvar:
   - `image:` já vem como `ghcr.io/edsonperes/qwenpaw-casaos:latest` — troque só se for usar outra conta/organização.
   - `QWENPAW_AUTH_PASSWORD`: defina uma senha forte.
4. Instale. O console abre em `http://IP-DO-SERVIDOR:8088`.

> Guia passo a passo com telas: veja [`casaos/README.md`](casaos/README.md).

## Deploy via docker compose (qualquer host)

```bash
git clone https://github.com/edsonperes/qwenpaw-casaos.git
cd qwenpaw-casaos
cp .env.example .env
# edite .env: GHCR_OWNER, QWENPAW_AUTH_PASSWORD, etc.
docker compose up -d
```

## Configuração pós-deploy (primeiro acesso)

1. Acesse `http://IP:8088` e faça login com o usuário/senha definidos.
2. **Modelo de IA** — em *Models/Providers*, adicione um provedor **OpenAI-compatible**: informe o **host** (base URL) e o **token**; o QwenPaw busca os modelos disponíveis. Selecione o modelo padrão.
3. **Telegram** — em *Channels*, habilite o Telegram e cole o **bot token**. Mande uma mensagem de **áudio** para o bot: ela deve chegar como texto transcrito.
4. **Idioma** — já deve estar em português. Para trocar, use o seletor no canto da interface.

## Como atualizar (mantém-se em dia com o oficial)

**Regenerar a imagem** a partir de uma versão mais nova do QwenPaw oficial:
- No GitHub: **Actions → build → Run workflow**. O workflow puxa `agentscope/qwenpaw:latest`, reaplica a camada fina e publica no GHCR. (Também roda sozinho toda segunda-feira.)

**Atualizar o servidor** para a imagem nova:
```bash
./scripts/update.sh          # docker compose pull && up -d (preserva dados)
```
No CasaOS, o mesmo efeito: **Settings do app → atualizar imagem** (ou recriar puxando a tag `latest`).

Como a personalização é uma casca fina, não há merge de código para resolver — as novidades do QwenPaw oficial entram junto com a imagem base.

## Segurança (leia — vai ficar exposto publicamente)

- **Sempre atrás de HTTPS.** Coloque um reverse proxy (Caddy, Nginx Proxy Manager, Traefik) na frente. Não exponha a porta 8088 sem TLS.
- **Senha forte** em `QWENPAW_AUTH_PASSWORD` (`openssl rand -base64 24`). Nunca versione o `.env`.
- Considere restringir o acesso por IP/allowlist no reverse proxy.
- Os segredos (tokens de canais, chaves de API) ficam no volume `working.secret`, criptografados pelo próprio QwenPaw.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `QWENPAW_AUTH_ENABLED` | `true` | Liga a autenticação do console. |
| `QWENPAW_AUTH_USERNAME` | `admin` | Usuário do login. |
| `QWENPAW_AUTH_PASSWORD` | — | Senha do login (**defina!**). |
| `QWENPAW_DEFAULT_LANGUAGE` | `pt-BR` | Idioma padrão aplicado ao `config.json`. |
| `QWENPAW_TRANSCRIPTION_TYPE` | `local_whisper` | `local_whisper`, `whisper_api` ou `disabled`. |
| `QWENPAW_WHISPER_MODEL` | `base` | Modelo do Whisper local (`base`/`small`/`medium`). |
| `QWENPAW_DISABLED_CHANNELS` | `imessage` | Canais desabilitados (iMessage exige macOS). |
| `QWENPAW_SEED_FORCE` | — | `true` reaplica os padrões mesmo já semeado (debug). |

## Trocar o modelo do Whisper

Para transcrever melhor (custa mais RAM/CPU), mude `QWENPAW_WHISPER_MODEL` para `small` ou `medium` no compose e recrie o container. Na primeira transcrição o novo modelo é baixado automaticamente. Para já embuti-lo na imagem, rode o workflow com `whisper_model=small`.

## Estrutura do repositório

```
Dockerfile               camada fina (ffmpeg + whisper + patch)
docker-compose.yml       deploy CasaOS (x-casaos)
docker-compose.test.yml  teste local
.env.example             modelo de variáveis
scripts/
  patch_whisper_model.py modelo do Whisper via env (com guarda anti-quebra)
  seed_config.py         semeia pt-BR + transcrição local (idempotente)
  custom-entrypoint.sh   init → seed → entrypoint oficial
  update.sh              atualiza o deploy
casaos/                  guia de importação no CasaOS
.github/workflows/       build & push para o GHCR
```

## Créditos

Construído sobre o [QwenPaw](https://github.com/agentscope-ai/QwenPaw) (AgentScope, Apache-2.0). Este repositório apenas empacota e configura; todo o mérito do produto é do projeto original.
