# API para SoundPlayer

Use a URL base do deploy:

```text
https://SEU-SERVICO.onrender.com
```

Troque `SEU-SERVICO` pelo nome gerado no Render.

## Fluxo recomendado

1. Preparar a musica com texto, YouTube ou Spotify.
2. Buscar os metadados pelo ID retornado.
3. Usar `/api/audio/{id}` como URL do player.

## Endpoints

### Health check

```http
GET /api/health
```

Resposta:

```json
{
  "status": "ok"
}
```

### Preparar musica

```http
GET /api/prepare/{query}
```

Exemplos:

```text
GET /api/prepare/twenty%20one%20pilots%20stressed%20out
GET /api/prepare/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DpXRviuL6vMY
GET /api/prepare/https%3A%2F%2Fopen.spotify.com%2Ftrack%2F...
```

Resposta:

```json
{
  "id": "20e1a064-4d46-4971-93e5-2be72f629036"
}
```

### Buscar dados

```http
GET /api/fetch/{song_id}
```

Resposta:

```json
{
  "id": "20e1a064-4d46-4971-93e5-2be72f629036",
  "name": "twenty one pilots: Stressed Out [OFFICIAL VIDEO]",
  "title": "twenty one pilots: Stressed Out [OFFICIAL VIDEO]",
  "youtube_id": "pXRviuL6vMY",
  "youtube_url": "https://www.youtube.com/watch?v=pXRviuL6vMY",
  "spotify_id": null,
  "spotify_url": null,
  "duration": 225,
  "thumbnail": "https://...",
  "audio_url": "https://...",
  "audio_expires_at": "2026-04-26T19:00:00+00:00",
  "cache_expires_at": "2026-05-03T19:00:00+00:00"
}
```

### Audio

```http
GET /api/audio/{song_id}
```

Use esta URL diretamente no player do seu app:

```text
https://SEU-SERVICO.onrender.com/api/audio/20e1a064-4d46-4971-93e5-2be72f629036
```

O endpoint pode retornar audio direto ou playlist HLS. Em app web, use `hls.js` quando o navegador nao suportar HLS nativamente.

## Exemplo JavaScript

```js
const API_BASE = "https://SEU-SERVICO.onrender.com";

async function searchSong(query) {
  const prepareRes = await fetch(`${API_BASE}/api/prepare/${encodeURIComponent(query)}`);
  if (!prepareRes.ok) throw new Error("Falha ao preparar musica");
  const { id } = await prepareRes.json();

  const fetchRes = await fetch(`${API_BASE}/api/fetch/${id}`);
  if (!fetchRes.ok) throw new Error("Falha ao buscar musica");
  return await fetchRes.json();
}

async function play(query, audioElement) {
  const song = await searchSong(query);
  const audioUrl = `${API_BASE}/api/audio/${song.id}`;

  if (window.Hls && Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(audioUrl);
    hls.attachMedia(audioElement);
  } else {
    audioElement.src = audioUrl;
  }

  await audioElement.play();
  return song;
}
```

## Observacoes importantes

- URLs de audio expiram. Chame `/api/fetch/{song_id}` antes de tocar para renovar quando necessario.
- O plano gratuito do Render pode dormir quando fica sem trafego. A primeira chamada depois de um tempo pode demorar.
- Em servidores publicos, o YouTube pode bloquear o `yt-dlp` com verificacao anti-bot. Nesse caso, o deploy precisa de `YTDLP_COOKIES_FILE` configurado como Secret File no Render, ou outra fonte de audio licenciada.
- Use apenas conteudo que voce tem direito de reproduzir no seu app.
