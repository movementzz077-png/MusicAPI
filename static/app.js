const form = document.querySelector("#search-form");
const input = document.querySelector("#query");
const submit = document.querySelector("#submit");
const statusBox = document.querySelector("#status");
const result = document.querySelector("#result");
const thumbnail = document.querySelector("#thumbnail");
const title = document.querySelector("#title");
const songId = document.querySelector("#song-id");
const duration = document.querySelector("#duration");
const expires = document.querySelector("#expires");
const youtubeLink = document.querySelector("#youtube-link");
const spotifyLink = document.querySelector("#spotify-link");
const player = document.querySelector("#player");
let hls = null;

function setStatus(message, isError = false) {
  statusBox.hidden = false;
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}

function clearStatus() {
  statusBox.hidden = true;
  statusBox.textContent = "";
  statusBox.classList.remove("error");
}

function formatDuration(seconds) {
  if (!seconds) return "Desconhecida";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

function setLink(anchor, url) {
  anchor.hidden = !url;
  anchor.href = url || "#";
}

function loadAudio(songId) {
  const source = `/api/audio/${songId}`;
  if (hls) {
    hls.destroy();
    hls = null;
  }

  player.hidden = false;
  player.removeAttribute("src");

  if (window.Hls && Hls.isSupported()) {
    hls = new Hls();
    hls.loadSource(source);
    hls.attachMedia(player);
    hls.on(Hls.Events.ERROR, (_, data) => {
      if (data.fatal) {
        const detail = data.response?.code
          ? ` (${data.type}, HTTP ${data.response.code})`
          : ` (${data.type}: ${data.details})`;
        setStatus(`Não foi possível tocar este stream de áudio${detail}.`, true);
      }
    });
    return;
  }

  player.src = source;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  submit.disabled = true;
  result.hidden = true;
  player.hidden = true;
  setStatus("Preparando música...");

  try {
    const prepared = await fetch(`/api/prepare/${encodeURIComponent(query)}`);
    const preparedJson = await prepared.json();
    if (!prepared.ok) throw new Error(preparedJson.detail || "Falha ao preparar a música.");

    setStatus("Carregando metadados...");
    const fetched = await fetch(`/api/fetch/${preparedJson.id}`);
    const data = await fetched.json();
    if (!fetched.ok) throw new Error(data.detail || "Falha ao buscar metadados.");

    title.textContent = data.title;
    songId.textContent = data.id;
    duration.textContent = formatDuration(data.duration);
    expires.textContent = data.cache_expires_at
      ? new Date(data.cache_expires_at).toLocaleString()
      : "Desconhecida";
    thumbnail.src = data.thumbnail || "";
    setLink(youtubeLink, data.youtube_url);
    setLink(spotifyLink, data.spotify_url);

    if (data.audio_url) {
      loadAudio(data.id);
    }

    result.hidden = false;
    clearStatus();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    submit.disabled = false;
  }
});
