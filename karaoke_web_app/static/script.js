console.log("APP JS LOADED");

let player = null;
let queueSongs = [];
let rejectedVideosGlobal = {};
let searchResults = [];
let currentResultIndex = 0;
let currentlyPlayingSong = null;
let fixingVideo = false;

function onYouTubeIframeAPIReady() {
  console.log("YT READY");

  player = new YT.Player("player", {
    playerVars: {
      controls: 0,
      modestbranding: 1,
      rel: 0,
      playsinline: 1,
      origin: window.location.origin,
    },

    events: {
      onReady: () => {
        console.log("PLAYER READY");
      },

      onStateChange: onPlayerStateChange,
    },
  });
}
window.onYouTubeIframeAPIReady = onYouTubeIframeAPIReady;

function onPlayerStateChange(event) {
  if (event.data === YT.PlayerState.ENDED) {
    playNextSong();
  }
}

const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#search-input");

const songCard = document.querySelector("#song-card");
const resultCount = document.querySelector("#result-count");

const previousButton = document.querySelector("#previous-button");
const nextButton = document.querySelector("#next-button");
const reserveButton = document.querySelector("#reserve-button");

const queueList = document.querySelector("#queue-list");
const queueCount = document.querySelector("#queue-count");

const skipButton = document.querySelector("#skip-button");

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function currentSong() {
  return searchResults[currentResultIndex] || null;
}

function displayCurrentSong() {
  const song = currentSong();

  const exists = Boolean(song);

  previousButton.disabled = !exists || searchResults.length <= 1;
  nextButton.disabled = !exists || searchResults.length <= 1;
  reserveButton.disabled = !exists;

  resultCount.textContent = exists
    ? `${currentResultIndex + 1} / ${searchResults.length}`
    : "0 / 0";

  if (!exists) {
    songCard.className = "song-card empty";

    songCard.innerHTML = `
        <p class="results-label">RESULTS</p>
        <h2>SEARCH TO BEGIN</h2>
        `;

    return;
  }

  songCard.className = "song-card";

  songCard.innerHTML = `
    <p class="results-label">RESULTS</p>
    <h2>${escapeHtml(song.title)}</h2>
    <p>${escapeHtml(song.artist)}</p>
  <small>
${song.code ? `Code: ${escapeHtml(song.code)}` : "OPEN SONG"}
</small>

  <button
    id="fix-video-button"
    class="fix-video-button">
    Fix Video
  </button>
`;

  const fixButton = document.getElementById("fix-video-button");

  if (fixButton) {
    fixButton.onclick = fixCurrentVideo;
  }
}

async function searchSongs() {
  const query = searchInput.value.trim();

  if (!query) {
    searchResults = [];
    displayCurrentSong();
    return;
  }

  const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);

  const data = await response.json();

  searchResults = data.results;

  searchResults.forEach((song) => {
    const key = `${song.title}|${song.artist}`;

    song.rejectedVideos = rejectedVideosGlobal[key] || [];
  });
  currentResultIndex = 0;

  displayCurrentSong();

  if (searchResults.length > 0) {
    songCard.focus?.();
  }
}



async function fixCurrentVideo() {
  if (fixingVideo) return;

  const song = currentlyPlayingSong;

  if (!song) {
    console.log("NO CURRENTLY PLAYING SONG");
    return;
  }

  fixingVideo = true;

  if (!song.rejectedVideos) {
    song.rejectedVideos = [];
  }

  // Reject the video currently being played
  if (song.video_id && !song.rejectedVideos.includes(song.video_id)) {
    song.rejectedVideos.push(song.video_id);
  }

  console.log("TITLE:", song.title);
  console.log("ARTIST:", song.artist);
  console.log("REJECTED:", song.rejectedVideos);

  try {
    const response = await fetch("/api/fix-video", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: song.title,
        artist: song.artist,
        rejected_videos: song.rejectedVideos,
      }),
    });

    const data = await response.json();

    console.log("SERVER RESPONSE:", data);

    if (!response.ok) {
      alert(data.error || "No replacement video found");
      return;
    }

    if (!data.video_id) {
      alert("Server returned no video ID");
      return;
    }

    const newVideoId = data.video_id;

    // IMPORTANT:
    // Remember the newly selected video
    song.video_id = newVideoId;

    // Also reject it so the next FIX cannot return it
    if (!song.rejectedVideos.includes(newVideoId)) {
      song.rejectedVideos.push(newVideoId);
    }

    console.log("NEW VIDEO:", newVideoId);
    console.log("UPDATED REJECTED:", song.rejectedVideos);

    if (player) {
      player.loadVideoById(newVideoId);
    }

    alert("Video fixed successfully");
  } catch (error) {
    console.error("FIX VIDEO ERROR:", error);
    alert("Unable to fix video");
  } finally {
    fixingVideo = false;
  }
}

async function reserveCurrentSong() {
  const song = currentSong();

  if (!song) return;

  console.log({
    code: song.code,
    title: song.title,
    artist: song.artist,
    video_id: song.video_id,
    source: song.source,
  });
  const response = await fetch("/api/queue", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      code: song.code,
      title: song.title,
      artist: song.artist,
      video_id: song.video_id,
      source: song.source,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    console.error(data);
    alert(data.error || "Failed to reserve song");
    return;
  }

  await loadQueue();

  // start only first song
  if (queueSongs.length === 1 && player && song.video_id) {
    console.log("PLAYING:", song.title);

    currentlyPlayingSong = queueSongs[0];

    player.loadVideoById(currentlyPlayingSong.video_id);
  }
}

async function loadQueue() {
  const response = await fetch("/api/queue");

  const data = await response.json();

  queueSongs = data.queue;

  renderQueue(queueSongs);
}

async function playNextSong() {
  if (!queueSongs.length) return;

  const current = queueSongs[0];

  await fetch(`/api/queue/${current.queue_id}`, {
    method: "DELETE",
  });

  await loadQueue();

  currentlyPlayingSong = queueSongs[0] || null;

  if (currentlyPlayingSong && player) {
    console.log("NEXT:", currentlyPlayingSong.title);

    player.loadVideoById(currentlyPlayingSong.video_id);
  }
}

async function skipCurrentSong() {
  if (!queueSongs.length) {
    console.log("No song playing");
    return;
  }

  console.log("SKIPPING:", queueSongs[0].title);

  await fetch(`/api/queue/${queueSongs[0].queue_id}`, {
    method: "DELETE",
  });

  await loadQueue();

  currentlyPlayingSong = queueSongs[0] || null;

  if (!currentlyPlayingSong) {
    console.log("Queue empty");

    if (player) {
      player.stopVideo();
    }

    return;
  }

  console.log("PLAYING NEXT:", currentlyPlayingSong.title);

  if (player && currentlyPlayingSong.video_id) {
    player.loadVideoById(currentlyPlayingSong.video_id);
  }
}

function renderQueue(queue) {
  queueCount.textContent = queue.length;

  if (!queue.length) {
    queueList.innerHTML = `
        <li class="empty-queue">
        STANDBY
        </li>
        `;

    return;
  }

  queueList.innerHTML = queue
    .map(
      (song, index) =>
        `
    <li>

        <div>
            <strong>
            ${escapeHtml(song.title)}
            </strong>

            <span>
            ${escapeHtml(song.artist)}
            </span>

        </div>


        ${
          index !== 0
            ? `
      <button
      class="remove-button"
      data-queue-id="${song.queue_id}">
      Remove
      </button>
      `
            : ""
        }
    </li>

    `,
    )
    .join("");
}

function moveResult(direction) {
  if (!searchResults.length) return;

  currentResultIndex =
    (currentResultIndex + direction + searchResults.length) %
    searchResults.length;

  displayCurrentSong();
}

searchForm.addEventListener("submit", (e) => {
  e.preventDefault();
  searchSongs();
});

previousButton.addEventListener("click", () => moveResult(-1));

nextButton.addEventListener("click", () => moveResult(1));

reserveButton.addEventListener("click", reserveCurrentSong);

skipButton.addEventListener("click", skipCurrentSong);

queueList.addEventListener("click", async (e) => {
  const button = e.target.closest(".remove-button");

  if (!button) return;

  await fetch(`/api/queue/${button.dataset.queueId}`, {
    method: "DELETE",
  });

  loadQueue();
});

window.addEventListener("load", async () => {
  await fetch("/api/reset-queue", {
    method: "POST",
  });

  loadQueue();
});

document.addEventListener("keydown", (e) => {
  if (document.activeElement === searchInput) {
    return;
  }

  if (e.key === "ArrowLeft") {
    moveResult(-1);
  }

  if (e.key === "ArrowRight") {
    moveResult(1);
  }
});

function hideLoadingScreen() {
  const loading = document.getElementById("loading-screen");

  if (!loading) return;

  loading.remove();
}

const vinyl = document.getElementById("vinyl");
const introCover = document.getElementById("intro-cover");

let wipeAnimationRunning = true;

function updateVinylWipe() {
  if (!vinyl || !introCover || !wipeAnimationRunning) return;

  const styles = getComputedStyle(vinyl);

  const right = parseFloat(styles.right);
  const vinylCenter = window.innerWidth - right - vinyl.offsetWidth / 2;

  introCover.style.setProperty("--wipe-edge", `${vinylCenter}px`);

  requestAnimationFrame(updateVinylWipe);
}

vinyl.addEventListener("animationend", (event) => {
  if (event.animationName === "vinylIntro") {
    wipeAnimationRunning = false;
    hideLoadingScreen();
  }
});

updateVinylWipe();
