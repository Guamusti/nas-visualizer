const API = "";
const state = {
  filters: { year: null, location: null, folder: null },
  sort: "taken_desc",
  offset: 0,
  limit: 60,
  total: 0,
  photos: [],
  pollTimer: null,
};

const $ = (id) => document.getElementById(id);

// ── API helpers ──
async function api(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

// ── Init ──
async function init() {
  // Bind UI events FIRST so buttons always work, even if data loading fails.
  bindEvents();

  try {
    const health = await api("/api/health");
    $("nasHost").textContent = health.nas.replace(/^https?:\/\//, "");
  } catch (e) { /* ignore */ }

  checkConnection();
  try {
    await Promise.all([loadStats(), loadYears(), loadLocations(), loadFolders()]);
    await loadPhotos(true);
  } catch (e) {
    console.error("Error cargando datos:", e);
  }
  pollIndexStatus();
}

async function checkConnection() {
  const badge = $("connBadge");
  try {
    const { connected } = await api("/api/index/connection");
    badge.className = "conn " + (connected ? "ok" : "bad");
    $("connText").textContent = connected ? "NAS conectado" : "Sin conexión";
  } catch {
    badge.className = "conn bad";
    $("connText").textContent = "Sin conexión";
  }
}

// ── Stats & filters ──
async function loadStats() {
  const s = await api("/api/photos/stats");
  $("statTotal").textContent = s.total.toLocaleString("es");
  $("statLoc").textContent = s.with_location.toLocaleString("es");
}

async function loadYears() {
  const years = await api("/api/photos/years");
  const box = $("yearChips");
  box.innerHTML = "";
  if (!years.length) { box.innerHTML = '<span class="muted">—</span>'; return; }
  years.reverse().forEach((y) => {
    box.appendChild(makeChip(y.year, y.count, () => toggleFilter("year", parseInt(y.year))));
  });
}

async function loadLocations() {
  const locs = await api("/api/photos/locations");
  const box = $("locationChips");
  box.innerHTML = "";
  if (!locs.length) { box.innerHTML = '<span class="muted">Sin datos de GPS aún</span>'; return; }
  locs.slice(0, 20).forEach((l) => {
    box.appendChild(makeChip(l.city, l.count, () => toggleFilter("location", l.city)));
  });
}

async function loadFolders() {
  const folders = await api("/api/photos/folders");
  const box = $("folderChips");
  box.innerHTML = "";
  if (!folders.length) { box.innerHTML = '<span class="muted">—</span>'; return; }
  folders.slice(0, 25).forEach((f) => {
    const name = f.folder.split("/").filter(Boolean).pop() || f.folder;
    box.appendChild(makeChip(name, f.count, () => toggleFilter("folder", f.folder)));
  });
}

function makeChip(label, count, onClick) {
  const chip = document.createElement("button");
  chip.className = "chip";
  chip.dataset.label = label;
  chip.innerHTML = `<span>${escapeHtml(label)}</span><span class="count">${count}</span>`;
  chip.onclick = onClick;
  return chip;
}

function toggleFilter(key, value) {
  state.filters[key] = state.filters[key] === value ? null : value;
  refreshChipState();
  renderActiveFilters();
  loadPhotos(true);
}

function refreshChipState() {
  document.querySelectorAll("#yearChips .chip").forEach((c) =>
    c.classList.toggle("active", parseInt(c.dataset.label) === state.filters.year));
  document.querySelectorAll("#locationChips .chip").forEach((c) =>
    c.classList.toggle("active", c.dataset.label === state.filters.location));
  document.querySelectorAll("#folderChips .chip").forEach((c) => {
    const active = state.filters.folder && state.filters.folder.endsWith("/" + c.dataset.label) || state.filters.folder === c.dataset.label;
    c.classList.toggle("active", !!active);
  });
}

function renderActiveFilters() {
  const box = $("activeFilters");
  box.innerHTML = "";
  const labels = { year: "Año", location: "Lugar", folder: "Carpeta" };
  Object.entries(state.filters).forEach(([k, v]) => {
    if (!v) return;
    let display = v;
    if (k === "folder") display = String(v).split("/").filter(Boolean).pop();
    const el = document.createElement("span");
    el.className = "active-filter";
    el.innerHTML = `${labels[k]}: ${escapeHtml(String(display))} <span class="x">✕</span>`;
    el.onclick = () => { state.filters[k] = null; refreshChipState(); renderActiveFilters(); loadPhotos(true); };
    box.appendChild(el);
  });
}

// ── Photos ──
function buildQuery() {
  const p = new URLSearchParams();
  p.set("limit", state.limit);
  p.set("offset", state.offset);
  p.set("sort", state.sort);
  if (state.filters.year) p.set("year", state.filters.year);
  if (state.filters.location) p.set("location", state.filters.location);
  if (state.filters.folder) p.set("folder", state.filters.folder);
  return p.toString();
}

async function loadPhotos(reset) {
  if (reset) { state.offset = 0; state.photos = []; $("grid").innerHTML = ""; }
  const data = await api("/api/photos?" + buildQuery());
  state.total = data.total;
  state.photos.push(...data.photos);
  renderPhotos(data.photos);

  $("empty").hidden = state.total > 0;
  $("grid").hidden = state.total === 0;
  $("gridCount").textContent = `${state.photos.length} de ${state.total.toLocaleString("es")}`;
  $("loadMore").hidden = state.photos.length >= state.total;
}

function renderPhotos(photos) {
  const grid = $("grid");
  photos.forEach((p) => {
    const idx = state.photos.indexOf(p);
    const tile = document.createElement("div");
    tile.className = "tile";
    const badge = p.location_city
      ? `<div class="tile-badge">📍 ${escapeHtml(p.location_city)}</div>`
      : "";
    tile.innerHTML = `<img loading="lazy" src="/api/media/thumb/${p.id}" alt="${escapeHtml(p.filename)}">${badge}`;
    const img = tile.querySelector("img");
    img.onload = () => img.classList.add("loaded");
    img.onerror = () => { tile.style.display = "none"; };
    tile.onclick = () => openLightbox(idx);
    grid.appendChild(tile);
  });
}

// ── Lightbox ──
let lbIndex = 0;
function openLightbox(idx) {
  lbIndex = idx;
  renderLightbox();
  $("lightbox").hidden = false;
  document.body.style.overflow = "hidden";
}
function closeLightbox() {
  $("lightbox").hidden = true;
  document.body.style.overflow = "";
}
function renderLightbox() {
  const p = state.photos[lbIndex];
  if (!p) return;
  $("lbImage").src = `/api/media/full/${p.id}`;
  const date = p.taken_at ? new Date(p.taken_at).toLocaleString("es", {
    day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
  }) : "Sin fecha";
  const rows = [
    ["🗓️", "Fecha", date],
    ["📍", "Lugar", p.location_name || "—"],
    ["📷", "Cámara", p.camera || "—"],
    ["🖼️", "Dimensiones", p.width ? `${p.width} × ${p.height}` : "—"],
    ["📁", "Carpeta", p.folder],
  ];
  if (p.gps_lat) rows.push(["🌐", "GPS", `${p.gps_lat.toFixed(5)}, ${p.gps_lon.toFixed(5)}`]);
  $("lbInfo").innerHTML =
    `<h3>${escapeHtml(p.filename)}</h3>` +
    rows.map(([icon, label, val]) => `
      <div class="lb-meta-row">
        <span class="lb-meta-icon">${icon}</span>
        <div><div class="lb-meta-label">${label}</div><div class="lb-meta-val">${escapeHtml(String(val))}</div></div>
      </div>`).join("");
}
function lbMove(dir) {
  lbIndex = (lbIndex + dir + state.photos.length) % state.photos.length;
  renderLightbox();
}

// ── Indexing ──
async function startIndex() {
  const btn = $("indexBtn");
  btn.disabled = true;
  try {
    await api("/api/index/start", { method: "POST" });
    $("indexPanel").hidden = false;
    pollIndexStatus();
  } catch { btn.disabled = false; }
}

async function pollIndexStatus() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  const tick = async () => {
    let s;
    try { s = await api("/api/index/status"); } catch { return; }
    const panel = $("indexPanel");
    if (s.running) {
      panel.hidden = false;
      $("indexBtn").disabled = true;
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
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        // Refresh everything
        setTimeout(() => { panel.hidden = true; }, 4000);
        await Promise.all([loadStats(), loadYears(), loadLocations(), loadFolders()]);
        loadPhotos(true);
      } else {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
      }
    }
  };
  await tick();
  if (!state.pollTimer) state.pollTimer = setInterval(tick, 1500);
}

// ── Events ──
function bindEvents() {
  $("indexBtn").onclick = startIndex;
  $("sortSelect").onchange = (e) => { state.sort = e.target.value; loadPhotos(true); };
  $("loadMore").onclick = () => { state.offset += state.limit; loadPhotos(false); };
  $("lbClose").onclick = closeLightbox;
  $("lbPrev").onclick = () => lbMove(-1);
  $("lbNext").onclick = () => lbMove(1);
  $("lightbox").onclick = (e) => { if (e.target.id === "lightbox") closeLightbox(); };
  document.addEventListener("keydown", (e) => {
    if ($("lightbox").hidden) return;
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") lbMove(-1);
    if (e.key === "ArrowRight") lbMove(1);
  });
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

init();
