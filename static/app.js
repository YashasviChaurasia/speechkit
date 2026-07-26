let asset, artifact;

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[character]);
const time = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const safeMessage = data => data.error?.message || data.detail || "SpeechLens could not complete this request.";

function setStatus(message, kind = "") {
  const status = $("#status");
  status.textContent = message;
  status.className = `status${kind ? ` status--${kind}` : ""}`;
}

function seek(seconds) {
  const media = $("#media");
  media.currentTime = seconds;
  media.play().catch(() => {});
}

function tags(values, cls = "") {
  return values?.length ? `<span class="tags ${cls}">${values.map(value => `<i>${esc(value)}</i>`).join("")}</span>` : "";
}

function render() {
  $("#result").hidden = false;
  $("#media").src = `/api/assets/${asset}/media`;
  $("#filename").textContent = artifact.filename;
  const meta = artifact.metadata || {};
  $("#facts").innerHTML = [
    ["Model", artifact.model],
    ["Language", artifact.language_code || "Unknown"],
    ["Speakers", artifact.speakers.length],
    ["Turns", artifact.segments.length],
    ["Duration", time(artifact.duration_seconds)],
    ["Est. cost", `₹${meta.estimated_cost_inr ?? "—"}`],
  ].map(([key, value]) => `<div><dt>${key}</dt><dd>${esc(value)}</dd></div>`).join("");
  $("#speaker-cards").innerHTML = artifact.speakers.map(speaker => `
    <article class="speaker-card">
      <div class="speaker-name"><input aria-label="Speaker name" value="${esc(speaker.display_name)}" data-speaker="${esc(speaker.speaker_id)}"><button class="rename" data-speaker="${esc(speaker.speaker_id)}" type="button">Save name</button></div>
      <p><strong>${speaker.speaking_percentage}%</strong> · ${time(speaker.speaking_seconds)} speaking</p>
      <small>${speaker.turn_count} turns · ${speaker.word_count} words · ${speaker.questions_asked} questions</small>
      ${tags(speaker.keywords)}${tags(speaker.entities, "entities")}
      <blockquote>${esc(speaker.representative_quotes[0] || "No representative quote")}</blockquote>
    </article>`).join("");
  $("#segments").innerHTML = artifact.segments.map(segment => `
    <button class="segment" type="button" data-start="${segment.start_seconds}">
      <span class="time">${time(segment.start_seconds)}–${time(segment.end_seconds)}</span>
      <span><b>${esc(segment.speaker_name)}</b><em>${esc(segment.text)}</em>${tags(segment.keywords)}${tags(segment.entities, "entities")}</span>
    </button>`).join("");
  $("#raw").textContent = JSON.stringify(artifact, null, 2);
}

async function refresh() {
  const response = await fetch(`/api/assets/${asset}/artifact`);
  const data = await response.json();
  if (!response.ok) throw new Error(safeMessage(data));
  artifact = data;
  render();
}

async function rename(button) {
  const id = button.dataset.speaker;
  const name = button.previousElementSibling.value.trim();
  if (!name) return;
  const response = await fetch(`/api/assets/${asset}/speakers/${id}`, {
    method: "PATCH",
    headers: {"content-type":"application/json"},
    body: JSON.stringify({display_name: name}),
  });
  const data = await response.json();
  if (!response.ok) {
    setStatus(safeMessage(data), "error");
    return;
  }
  await refresh();
  setStatus("Speaker name saved.", "complete");
  if ($("#query").value) search();
}

function resultCard(result) {
  const close = !result.is_exact && result.similarity != null;
  const field = {keywords:"keyword", entities:"entity", topics:"topic", speaker_name:"speaker"}[result.matched_fields?.[0]] || "token";
  const details = close ? `<p class="close-match"><strong>Close ${field} · ${Math.round(result.similarity * 100)}%</strong><br>Query: ${esc($("#query").value.trim())} · Matched term: ${esc(result.matched_term)} · Field: ${esc(result.matched_fields?.join(", "))}</p>` : "";
  return `<article class="result" data-start="${result.start_seconds}"><div><span class="time">${time(result.start_seconds)}–${time(result.end_seconds)}</span><b>${esc(result.speaker_name)}</b></div>${details}<p>${esc(result.text)}</p>${tags(result.keywords)}${tags(result.entities, "entities")}<footer><span>score ${result.score}</span><span>matched: ${esc(result.matched_fields?.join(", ") || "indexed fields")}</span><button class="play" type="button" data-start="${result.start_seconds}">Play at timestamp</button></footer></article>`;
}

async function search() {
  const query = $("#query").value.trim();
  const mode = $("#mode").value;
  if (!query || !asset) return;
  const response = await fetch(`/api/assets/${asset}/search?q=${encodeURIComponent(query)}&mode=${mode}`);
  const data = await response.json();
  if (!response.ok) {
    $("#search-meta").textContent = safeMessage(data);
    return;
  }
  $("#search-meta").textContent = `${data.results.length} result${data.results.length === 1 ? "" : "s"} · ${data.elapsed_ms} ms · ${data.mode}`;
  $("#results").innerHTML = data.results.map(resultCard).join("") || "<p class='empty'>No indexed match. Try substring mode for a middle-of-word query.</p>";
}

function setupRail() {
  const links = [...document.querySelectorAll(".rail-link")];
  const setCurrent = id => links.forEach(link => link.classList.toggle("is-current", link.getAttribute("href") === `#${id}`));
  links.forEach(link => link.addEventListener("click", () => setCurrent(link.getAttribute("href").slice(1))));
  const sections = links.map(link => document.querySelector(link.getAttribute("href"))).filter(Boolean);
  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
    if (visible) setCurrent(visible.target.id);
  }, {rootMargin: "-18% 0px -70% 0px", threshold: [0, .1, .3]});
  sections.forEach(section => observer.observe(section));
}

$("#upload").onsubmit = async event => {
  event.preventDefault();
  setStatus("Extracting audio, submitting Sarvam Batch STT, and indexing turns…");
  const response = await fetch("/api/assets", {method:"POST", body:new FormData(event.target)});
  const data = await response.json();
  if (!response.ok) {
    setStatus(safeMessage(data), "error");
    return;
  }
  asset = data.asset_id;
  try {
    await refresh();
    setStatus("Analysis complete. Inspect the evidence below.", "complete");
    document.querySelector("#overview").scrollIntoView({behavior:"smooth", block:"start"});
  } catch (error) {
    setStatus(error.message, "error");
  }
};

$("#search").onclick = search;
$("#query").onkeydown = event => { if (event.key === "Enter") { event.preventDefault(); search(); } };
document.addEventListener("click", event => {
  const renameButton = event.target.closest(".rename");
  const start = event.target.closest("[data-start]");
  if (renameButton) rename(renameButton);
  if (start && !event.target.closest("input")) seek(Number(start.dataset.start));
});
$("#export").onclick = () => {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(new Blob([JSON.stringify(artifact, null, 2)], {type:"application/json"}));
  anchor.download = "speechkit.v1.json";
  anchor.click();
};

setupRail();
const preloaded = new URLSearchParams(location.search).get("asset");
if (preloaded) {
  asset = preloaded;
  refresh().then(() => setStatus("Loaded completed demo.", "complete")).catch(error => setStatus(error.message, "error"));
}
