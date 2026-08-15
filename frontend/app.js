// ── State ──
const state = {
  view: "albums",        // albums | photos
  albumsBy: "auto",
  album: null,           // {type, key, title, country_code, country_name}
  sort: "taken_desc",
  offset: 0, limit: 40, total: 0,
  photos: [], loading: false, hasMore: false,
  reelsOffset: 0, reelsLimit: 12, reels: [], reelsLoading: false, reelsHasMore: true,
  pollTimer: null,
};

const $ = (id) => document.getElementById(id);
async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(res.status);
  return res.json();
}
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const flag = (cc) => cc ? cc.toUpperCase().replace(/./g, (c) => String.fromCodePoint(127397 + c.charCodeAt(0))) : "";

function dateRange(from, to) {
  if (!from) return "";
  const f = new Date(from), t = to ? new Date(to) : f;
  const opt = { day: "numeric", month: "short", year: "numeric" };
  const a = f.toLocaleDateString("es", opt);
  const b = t.toLocaleDateString("es", opt);
  return a === b ? a : `${a} — ${b}`;
}

// ── Init ──
async function init() {
  bindEvents();
  try {
    const h = await api("/api/health");
    $("nasHost").textContent = h.nas.replace(/^https?:\/\//, "");
  } catch {}
  checkConnection();
  await loadAlbums();
  pollIndexStatus();
}

async function checkConnection() {
  try {
    const { connected } = await api("/api/index/connection");
    $("connBadge").className = "conn " + (connected ? "ok" : "bad");
    $("connText").textContent = connected ? "NAS conectado" : "Sin conexión";
  } catch {
    $("connBadge").className = "conn bad";
    $("connText").textContent = "Sin conexión";
  }
}

// ── Albums ──
async function loadAlbums() {
  let data;
  try { data = await api("/api/albums?by=" + state.albumsBy); }
  catch { data = { albums: [] }; }

  const grid = $("albumGrid");
  grid.innerHTML = "";
  $("albumsEmpty").hidden = data.albums.length > 0;

  data.albums.forEach((al) => {
    const card = document.createElement("div");
    card.className = "album-card";
    const fl = al.country_code
      ? `<div class="album-flag">${flag(al.country_code)}</div>`
      : `<div class="album-flag pin">📍</div>`;
    const sub = al.subtitle ? `<div class="a-sub">${esc(al.subtitle)}</div>` : `<div class="a-sub">${esc(dateRange(al.from_date, al.to_date))}</div>`;
    card.innerHTML = `
      <div class="album-cover" data-cover="${al.cover_photo_id}"></div>
      <div class="album-scrim"></div>
      <div class="album-content">
        ${fl}
        <div class="album-text">
          <div class="a-title">${esc(al.title)}</div>
          ${sub}
          <span class="a-count">${al.count} ${al.count === 1 ? "foto" : "fotos"}</span>
        </div>
      </div>`;
    // Lazy-load blurred cover
    const cover = card.querySelector(".album-cover");
    const img = new Image();
    img.onload = () => { cover.style.backgroundImage = `url(/api/media/thumb/${al.cover_photo_id})`; cover.classList.add("loaded"); };
    img.src = `/api/media/thumb/${al.cover_photo_id}`;
    card.onclick = () => openAlbum(al);
    grid.appendChild(card);
  });
}

// ── View switching ──
function showView(v) {
  state.view = v;
  $("albumsView").hidden = v !== "albums";
  $("photosView").hidden = v !== "photos";
  $("reelsView").hidden = v !== "reels";
  $("tabAlbums").classList.toggle("active", v === "albums");
  $("tabAll").classList.toggle("active", v === "photos" && !state.album);
  $("tabReels").classList.toggle("active", v === "reels");
  if (v !== "reels") pauseReels();
}

function openAlbum(al) {
  state.album = al;
  showView("photos");
  $("backBtn").hidden = false;
  $("heroFlag").textContent = al.country_code ? flag(al.country_code) : "";
  $("heroEyebrow").textContent = al.type === "country" ? "País" : "Carpeta";
  $("heroTitle").textContent = al.title;
  $("tagCountryBtn").hidden = al.type !== "folder";
  loadPhotos(true);
}

function openAll() {
  state.album = null;
  showView("photos");
  $("backBtn").hidden = true;
  $("heroFlag").textContent = "";
  $("heroEyebrow").textContent = "Biblioteca";
  $("heroTitle").textContent = "Todas las fotos";
  $("tagCountryBtn").hidden = true;
  loadPhotos(true);
}

// ── Photos (progressive) ──
function photoQuery() {
  const p = new URLSearchParams();
  p.set("limit", state.limit);
  p.set("offset", state.offset);
  p.set("sort", state.sort);
  if (state.album?.type === "country") p.set("country", state.album.key);
  if (state.album?.type === "folder") p.set("folder", state.album.key);
  return p.toString();
}

async function loadPhotos(reset) {
  if (state.loading) return;
  if (reset) { state.offset = 0; state.photos = []; $("grid").innerHTML = ""; }
  if (!reset && !state.hasMore) return;
  state.loading = true;
  $("gridStatus").textContent = "Cargando…";

  let data;
  try { data = await api("/api/photos?" + photoQuery()); }
  catch { state.loading = false; $("gridStatus").textContent = "Error al cargar"; return; }

  state.total = data.total;
  state.photos.push(...data.photos);
  state.offset += data.photos.length;
  state.hasMore = state.photos.length < state.total;
  renderPhotos(data.photos);

  const meta = `${state.total} ${state.total === 1 ? "foto" : "fotos"}`;
  const range = dateRange(
    data.photos.length ? data.photos[data.photos.length - 1].taken_at : null,
    data.photos.length ? data.photos[0].taken_at : null);
  $("heroMeta").textContent = state.album ? meta : meta;
  $("gridStatus").textContent = state.hasMore ? "" : (state.total ? `— fin · ${state.total} fotos —` : "");
  state.loading = false;
}

function renderPhotos(photos) {
  const grid = $("grid");
  photos.forEach((p) => {
    const idx = state.photos.indexOf(p);
    const tile = document.createElement("div");
    tile.className = "tile" + (p.media_type === "video" ? " video-tile" : "");
    const badge = p.location_city ? `<div class="tile-badge">${flag(p.country_code)} ${esc(p.location_city)}</div>` : "";
    if (p.media_type === "video") {
      tile.innerHTML = `<video preload="metadata" muted playsinline src="/api/media/full/${p.id}"></video><span class="video-mark">▶</span>${badge}`;
      const video = tile.querySelector("video");
      video.onloadeddata = () => video.classList.add("loaded");
    } else {
      tile.innerHTML = `<img loading="lazy" src="/api/media/thumb/${p.id}" alt="">${badge}`;
      const img = tile.querySelector("img");
      img.onload = () => img.classList.add("loaded");
      img.onerror = () => { tile.remove(); };
    }
    tile.onclick = () => openLightbox(idx);
    grid.appendChild(tile);
  });
}

// ── Reels ──
async function openReels() {
  showView("reels");
  if (!state.reels.length) await loadReels(true);
}

async function loadReels(reset) {
  if (state.reelsLoading || (!reset && !state.reelsHasMore)) return;
  if (reset) {
    state.reelsOffset = 0;
    state.reels = [];
    state.reelsHasMore = true;
    $("reelsFeed").innerHTML = "";
  }
  state.reelsLoading = true;
  $("reelsStatus").textContent = "Cargando momentos…";
  try {
    const p = new URLSearchParams({
      limit: state.reelsLimit,
      offset: state.reelsOffset,
      sort: "taken_desc",
      media: "all",
    });
    const data = await api("/api/photos?" + p);
    state.reels.push(...data.photos);
    state.reelsOffset += data.photos.length;
    state.reelsHasMore = state.reels.length < data.total;
    renderReels(data.photos);
    $("reelsStatus").textContent = state.reelsHasMore ? "" : (data.total ? "— Has llegado al principio de tus recuerdos —" : "Aún no hay momentos");
  } catch {
    $("reelsStatus").textContent = "No se pudieron cargar los reels";
  } finally {
    state.reelsLoading = false;
  }
}

function renderReels(items) {
  const feed = $("reelsFeed");
  items.forEach((p) => {
    const article = document.createElement("article");
    article.className = "reel-card";
    article.dataset.id = p.id;
    const place = p.location_city || p.location_country || "Tu fototeca";
    const when = p.taken_at
      ? new Date(p.taken_at).toLocaleDateString("es", { day: "numeric", month: "long", year: "numeric" })
      : "Fecha desconocida";
    const media = p.media_type === "video"
      ? `<video class="reel-media" preload="metadata" muted loop playsinline src="/api/media/full/${p.id}"></video><button class="reel-sound" aria-label="Activar sonido">♪</button>`
      : `<img class="reel-media" loading="lazy" src="/api/media/thumb/${p.id}" alt="${esc(p.filename)}">`;
    article.innerHTML = `
      ${media}
      <div class="reel-shade"></div>
      <div class="reel-copy">
        <span class="reel-flag">${flag(p.country_code)}</span>
        <p class="reel-place">${esc(place)}</p>
        <p class="reel-date">${esc(when)}</p>
      </div>
      <button class="reel-open" aria-label="Abrir ${esc(p.filename)}">↗</button>`;
    article.querySelector(".reel-open").onclick = () => {
      state.photos = state.reels;
      openLightbox(state.reels.indexOf(p));
    };
    const sound = article.querySelector(".reel-sound");
    if (sound) sound.onclick = () => {
      const video = article.querySelector("video");
      video.muted = !video.muted;
      sound.textContent = video.muted ? "♪" : "♫";
    };
    feed.appendChild(article);
    reelObserver.observe(article);
  });
}

function pauseReels() {
  document.querySelectorAll(".reel-card video").forEach((v) => v.pause());
}

const reelObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    const video = entry.target.querySelector("video");
    if (!video) return;
    if (entry.isIntersecting && state.view === "reels") video.play().catch(() => {});
    else video.pause();
  });
}, { threshold: .68 });

// ── Lightbox ──
let lbIndex = 0;
function openLightbox(i) { lbIndex = i; renderLightbox(); $("lightbox").hidden = false; document.body.style.overflow = "hidden"; }
function closeLightbox() {
  $("lightbox").hidden = true;
  $("lbVideo").pause();
  document.body.style.overflow = "";
}
function renderLightbox() {
  const p = state.photos[lbIndex];
  if (!p) return;
  const isVideo = p.media_type === "video";
  $("lbImage").hidden = isVideo;
  $("lbVideo").hidden = !isVideo;
  $("lbVideo").pause();
  if (isVideo) {
    $("lbVideo").src = `/api/media/full/${p.id}`;
  } else {
    $("lbImage").src = `/api/media/full/${p.id}`;
    $("lbVideo").removeAttribute("src");
  }
  const date = p.taken_at ? new Date(p.taken_at).toLocaleString("es", { day:"numeric", month:"long", year:"numeric", hour:"2-digit", minute:"2-digit" }) : "Sin fecha";
  const rows = [
    ["🗓", "Fecha", date],
    ["📍", "Lugar", p.location_name || "—"],
    ["📷", "Cámara", p.camera || "—"],
    ["🖼", "Dimensiones", p.width ? `${p.width} × ${p.height}` : "—"],
    ["📁", "Carpeta", p.folder],
  ];
  if (p.gps_lat) rows.push(["🌐", "GPS", `${p.gps_lat.toFixed(5)}, ${p.gps_lon.toFixed(5)}`]);
  $("lbInfo").innerHTML = `<h3>${esc(p.filename)}</h3>` + rows.map(([i,k,v]) =>
    `<div class="lb-row"><span class="lb-ico">${i}</span><div><div class="lb-k">${k}</div><div class="lb-v">${esc(String(v))}</div></div></div>`).join("");
}
function lbMove(d) { lbIndex = (lbIndex + d + state.photos.length) % state.photos.length; renderLightbox(); }

// ── Country modal ──
function openCountryModal() {
  $("countryModal").hidden = false;
  $("countrySearch").value = "";
  renderCountryList("");
  $("countrySearch").focus();
}
function renderCountryList(q) {
  const list = $("countryList");
  const ql = q.toLowerCase();
  list.innerHTML = "";
  COUNTRIES.filter((c) => c[0].toLowerCase().includes(ql)).slice(0, 60).forEach((c) => {
    const b = document.createElement("button");
    b.className = "country-item";
    b.innerHTML = `<span class="ci-flag">${flag(c[1])}</span><span>${esc(c[0])}</span>`;
    b.onclick = () => assignCountry(c[1], c[0]);
    list.appendChild(b);
  });
}
async function assignCountry(code, name) {
  if (!state.album) return;
  try {
    await api("/api/albums/folder-country", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder: state.album.key, country_code: code, country_name: name }),
    });
    state.album.country_code = code; state.album.country_name = name;
    $("heroFlag").textContent = flag(code);
    $("countryModal").hidden = true;
    loadAlbums();  // refresh so it shows under "Por país" with its flag
  } catch {}
}

// ── Indexing ──
async function startIndex() {
  $("indexBtn").disabled = true;
  try { await api("/api/index/start", { method: "POST" }); $("indexPanel").hidden = false; pollIndexStatus(); }
  catch { $("indexBtn").disabled = false; }
}
async function pollIndexStatus() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  const tick = async () => {
    let s; try { s = await api("/api/index/status"); } catch { return; }
    if (s.running) {
      $("indexPanel").hidden = false; $("indexBtn").disabled = true;
      const pct = s.total ? Math.round((s.processed / s.total) * 100) : 0;
      $("progressFill").style.width = pct + "%";
      $("indexPhase").textContent = s.phase === "listing" ? "Listando archivos…" : `Procesando… ${pct}%`;
      $("indexCounts").textContent = `${s.processed} / ${s.total} · ${s.new} nuevas`;
      $("indexFile").textContent = s.current_file || "";
    } else {
      $("indexBtn").disabled = false;
      if (s.phase === "done" || s.phase === "error") {
        $("progressFill").style.width = "100%";
        $("indexPhase").textContent = s.phase === "done" ? "✓ Indexación completa" : "✕ Error";
        $("indexCounts").textContent = s.message || "";
        clearInterval(state.pollTimer); state.pollTimer = null;
        setTimeout(() => { $("indexPanel").hidden = true; }, 4000);
        await loadAlbums();
        if (state.view === "photos") loadPhotos(true);
      } else { clearInterval(state.pollTimer); state.pollTimer = null; }
    }
  };
  await tick();
  if (!state.pollTimer) state.pollTimer = setInterval(tick, 1500);
}

// ── Events ──
function bindEvents() {
  $("tabAlbums").onclick = () => { showView("albums"); loadAlbums(); };
  $("tabAll").onclick = openAll;
  $("tabReels").onclick = openReels;
  $("backBtn").onclick = () => { showView("albums"); loadAlbums(); };
  $("indexBtn").onclick = startIndex;
  $("sortSelect").onchange = (e) => { state.sort = e.target.value; loadPhotos(true); };

  document.querySelectorAll("#albumsMode .seg").forEach((seg) => {
    seg.onclick = () => {
      document.querySelectorAll("#albumsMode .seg").forEach((s) => s.classList.remove("active"));
      seg.classList.add("active");
      state.albumsBy = seg.dataset.by;
      loadAlbums();
    };
  });

  // Infinite scroll
  const io = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && state.view === "photos" && state.hasMore && !state.loading) loadPhotos(false);
  }, { rootMargin: "600px" });
  io.observe($("sentinel"));

  const reelsIo = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && state.view === "reels" && state.reelsHasMore && !state.reelsLoading) loadReels(false);
  }, { rootMargin: "800px" });
  reelsIo.observe($("reelsSentinel"));

  // Lightbox
  $("lbClose").onclick = closeLightbox;
  $("lbPrev").onclick = () => lbMove(-1);
  $("lbNext").onclick = () => lbMove(1);
  document.addEventListener("keydown", (e) => {
    if (!$("lightbox").hidden) {
      if (e.key === "Escape") closeLightbox();
      if (e.key === "ArrowLeft") lbMove(-1);
      if (e.key === "ArrowRight") lbMove(1);
      return;
    }
    if (state.view === "reels" && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      const cards = [...document.querySelectorAll(".reel-card")];
      const current = cards.findIndex((card) => {
        const rect = card.getBoundingClientRect();
        return rect.top >= 0 && rect.top < innerHeight * .55;
      });
      const next = Math.max(0, Math.min(cards.length - 1, current + (e.key === "ArrowDown" ? 1 : -1)));
      cards[next]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  // Country modal
  $("tagCountryBtn").onclick = openCountryModal;
  $("countryClose").onclick = () => { $("countryModal").hidden = true; };
  $("countryModal").onclick = (e) => { if (e.target.id === "countryModal") $("countryModal").hidden = true; };
  $("countrySearch").oninput = (e) => renderCountryList(e.target.value);
}

// ── Country list (name, ISO-2) ──
const COUNTRIES = [
  ["España","es"],["Portugal","pt"],["Francia","fr"],["Italia","it"],["Alemania","de"],
  ["Reino Unido","gb"],["Irlanda","ie"],["Países Bajos","nl"],["Bélgica","be"],["Suiza","ch"],
  ["Austria","at"],["Noruega","no"],["Suecia","se"],["Dinamarca","dk"],["Finlandia","fi"],
  ["Islandia","is"],["Polonia","pl"],["Chequia","cz"],["Hungría","hu"],["Grecia","gr"],
  ["Croacia","hr"],["Eslovenia","si"],["Eslovaquia","sk"],["Rumanía","ro"],["Bulgaria","bg"],
  ["Serbia","rs"],["Montenegro","me"],["Bosnia y Herzegovina","ba"],["Albania","al"],["Macedonia del Norte","mk"],
  ["Estonia","ee"],["Letonia","lv"],["Lituania","lt"],["Ucrania","ua"],["Rusia","ru"],
  ["Turquía","tr"],["Chipre","cy"],["Malta","mt"],["Luxemburgo","lu"],["Andorra","ad"],
  ["Mónaco","mc"],["Estados Unidos","us"],["Canadá","ca"],["México","mx"],["Cuba","cu"],
  ["República Dominicana","do"],["Costa Rica","cr"],["Panamá","pa"],["Guatemala","gt"],["Colombia","co"],
  ["Venezuela","ve"],["Ecuador","ec"],["Perú","pe"],["Brasil","br"],["Bolivia","bo"],
  ["Chile","cl"],["Argentina","ar"],["Uruguay","uy"],["Paraguay","py"],["Marruecos","ma"],
  ["Túnez","tn"],["Egipto","eg"],["Sudáfrica","za"],["Kenia","ke"],["Tanzania","tz"],
  ["Namibia","na"],["Senegal","sn"],["Cabo Verde","cv"],["Emiratos Árabes Unidos","ae"],["Catar","qa"],
  ["Arabia Saudí","sa"],["Israel","il"],["Jordania","jo"],["Líbano","lb"],["India","in"],
  ["Nepal","np"],["Sri Lanka","lk"],["Tailandia","th"],["Vietnam","vn"],["Camboya","kh"],
  ["Indonesia","id"],["Malasia","my"],["Singapur","sg"],["Filipinas","ph"],["Japón","jp"],
  ["Corea del Sur","kr"],["China","cn"],["Hong Kong","hk"],["Taiwán","tw"],["Australia","au"],
  ["Nueva Zelanda","nz"],["Fiyi","fj"],
];

init();
