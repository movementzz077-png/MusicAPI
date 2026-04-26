# MusicAPI

API e interface web em Python para buscar musicas por nome, link do YouTube ou link do Spotify, retornando metadados e audio quando possivel.

> Use apenas conteudo que voce tem direito de reproduzir. Este projeto nao baixa arquivos por padrao; ele usa URLs temporarias obtidas por `yt-dlp` quando disponiveis.

## Recursos

- Backend com FastAPI.
- Interface web responsiva com busca, thumbnail, links e player HTML5.
- Cache local em SQLite com tabelas `songs` e `aliases`.
- Busca de metadados e audio via `yt-dlp`.
- Integracao opcional com Spotify Web API via `spotipy`.
- Proxy local para audio direto e HLS, evitando CORS no navegador.
- Configuracao por `.env`.
- Deploy preparado para Render com `render.yaml`.
- Execucao local com `python app.py`.
- Testes com `pytest`.

## Estrutura

```text
MusicAPI/
  app.py
  requirements.txt
  runtime.txt
  render.yaml
  README.md
  API_USAGE.md
  .env.example
  musicapi/
  templates/
  static/
  tests/
```

## Instalar localmente

```bash
cd MusicAPI
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Acesse:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Variaveis de ambiente

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
APP_HOST=127.0.0.1
APP_PORT=8000
CORS_ORIGINS=*
YTDLP_COOKIES_FILE=
LOG_LEVEL=INFO
APP_DEBUG=false
```

No Render, use:

```env
APP_HOST=0.0.0.0
CORS_ORIGINS=*
YTDLP_COOKIES_FILE=/etc/secrets/youtube-cookies.txt
LOG_LEVEL=INFO
APP_DEBUG=false
```

O Render define `PORT` automaticamente. A aplicacao usa `PORT` quando existir.

Spotify e opcional. Sem `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`, a aplicacao continua funcionando com YouTube/yt-dlp.

## Deploy no Render

### Opcao recomendada: Blueprint

1. Crie um repositorio no GitHub.
2. Envie o conteudo da pasta `MusicAPI` para o repositorio.
3. Entre em `https://render.com`.
4. Clique em `New` > `Blueprint`.
5. Conecte o repositorio.
6. Confirme que o arquivo `render.yaml` foi detectado.
7. Preencha `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET` se quiser Spotify.
8. Se for usar audio do YouTube em producao, adicione um Secret File chamado `youtube-cookies.txt`.
9. Clique em `Deploy Blueprint`.

O Render vai executar:

```bash
pip install -r requirements.txt
uvicorn musicapi.routes:app --host 0.0.0.0 --port $PORT
```

### Opcao manual: Web Service

1. Clique em `New` > `Web Service`.
2. Conecte seu repositorio.
3. Runtime: `Python`.
4. Build Command:

```bash
pip install -r requirements.txt
```

5. Start Command:

```bash
uvicorn musicapi.routes:app --host 0.0.0.0 --port $PORT
```

6. Environment Variables:

```env
APP_HOST=0.0.0.0
APP_DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=*
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
YTDLP_COOKIES_FILE=/etc/secrets/youtube-cookies.txt
```

## YouTube no Render e cookies

Em hospedagens como Render, Koyeb, Railway e Fly.io, o YouTube pode bloquear o `yt-dlp` com:

```text
Sign in to confirm you're not a bot
```

Isso acontece por causa da reputacao/IP do datacenter. Localmente pode funcionar, mas no servidor publico pode falhar.

Opcao tecnica suportada pelo projeto:

1. Exporte cookies do YouTube em formato Netscape `cookies.txt` usando uma extensao confiavel do navegador.
2. No Render, abra seu Web Service.
3. Va em `Environment` ou `Advanced` > `Secret Files`.
4. Clique em `Add Secret File`.
5. Nome do arquivo:

```text
youtube-cookies.txt
```

6. Cole o conteudo do arquivo de cookies.
7. Garanta que a env var esteja assim:

```env
YTDLP_COOKIES_FILE=/etc/secrets/youtube-cookies.txt
```

8. Redeploy.

Use cookies apenas da sua propria conta e apenas para conteudo que voce tem direito de reproduzir. Cookies podem expirar ou serem invalidados pelo YouTube.

## API

Documentacao detalhada para integrar no seu SoundPlayer:

```text
API_USAGE.md
```

Principais endpoints:

```http
GET /api/health
GET /api/prepare/{query}
GET /api/fetch/{song_id}
GET /api/audio/{song_id}
```

Fluxo:

1. Chame `/api/prepare/{query}`.
2. Pegue o `id`.
3. Chame `/api/fetch/{id}` para metadados.
4. Use `/api/audio/{id}` no player.

## Testes

```bash
pytest
```

## Limites do plano gratis

- Web services gratis do Render podem dormir quando ficam sem trafego.
- O SQLite no disco local do plano gratis pode ser reiniciado em redeploys. Para cache persistente, use um disco persistente pago ou migre para Postgres.
- Streaming de audio consome banda. Monitore uso para nao exceder limites do provedor.
- YouTube pode bloquear datacenters publicos. Se isso acontecer, configure `YTDLP_COOKIES_FILE` ou use uma fonte licenciada de audio propria.

## Alternativas gratis

- Render: simples para FastAPI, com plano gratis para testes e hobby.
- Koyeb: oferece instancia free pequena e tambem roda APIs Python.
- Railway: tem trial/creditos, mas pode ter restricoes de rede em contas nao verificadas.
- Fly.io: bom para apps globais, mas o trial gratuito atual e curto.
