const API = "http://127.0.0.1:8801";

async function safeFetch(url, options) {
  try {
    const res = await fetch(url, options);
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.detail || JSON.stringify(data) };
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `network error: ${e.message} — is the backend running?` };
  }
}

function err(msg) { return `<span class="error-text">${msg}</span>`; }

// ── Corpus stats ─────────────────────────────────────────────
async function loadCorpusStats() {
  const { ok, data } = await safeFetch(`${API}/corpus/stats`);
  if (!ok) return;
  document.getElementById("corpusStats").innerHTML = [
    `<div class="stat-chip"><span>${data.own_posts}</span> posts</div>`,
    `<div class="stat-chip"><span>${data.reply_examples}</span> replies</div>`,
    `<div class="stat-chip"><span>${data.references}</span> refs</div>`,
  ].join("");
}

// ── Import from my_twitter_data/ folder ──────────────────────
document.getElementById("importArchiveBtn").addEventListener("click", async () => {
  const el = document.getElementById("archiveStatus");
  el.textContent = "importing archive… (this may take a minute)";
  const { ok, data, error } = await safeFetch(`${API}/tweets/import_archive`, { method: "POST" });
  if (!ok) { el.innerHTML = err(error); return; }
  el.textContent =
    `done — ${data.posts_cleaned} posts in ${data.cluster_count} clusters, ` +
    `${data.replies_indexed} reply examples, scorer f1=${data.scorer_metrics?.f1?.toFixed(3) ?? "n/a"}`;
  loadCorpusStats();
});

// ── Import from JSON file ─────────────────────────────────────
document.getElementById("importTweetsBtn").addEventListener("click", async () => {
  const file = document.getElementById("tweetsFileInput").files[0];
  const el = document.getElementById("importStatus");
  if (!file) { el.innerHTML = err("pick a file first"); return; }
  el.textContent = "importing…";
  const fd = new FormData();
  fd.append("file", file);
  const { ok, data, error } = await safeFetch(`${API}/tweets/import`, { method: "POST", body: fd });
  if (!ok) { el.innerHTML = err(error); return; }
  el.textContent =
    `imported ${data.raw_count} → ${data.cleaned_count} cleaned, ` +
    `${data.cluster_count} clusters, scorer f1=${data.scorer_metrics?.f1?.toFixed(3)}`;
  loadCorpusStats();
});

// ── Add by URL ────────────────────────────────────────────────
document.getElementById("addFromUrlBtn").addEventListener("click", async () => {
  const url = document.getElementById("tweetUrlInput").value.trim();
  const el = document.getElementById("urlStatus");
  if (!url) { el.innerHTML = err("paste a URL first"); return; }
  el.textContent = "fetching…";
  const { ok, data, error } = await safeFetch(`${API}/style/add_from_url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, note: document.getElementById("tweetUrlNote").value }),
  });
  if (!ok) { el.innerHTML = err(error); return; }
  el.textContent = `added: "${data.text?.slice(0, 90)}…"`;
  document.getElementById("tweetUrlInput").value = "";
  loadCorpusStats();
});

// ── Add post example ──────────────────────────────────────────
document.getElementById("addPostBtn").addEventListener("click", async () => {
  const text = document.getElementById("addPostText").value.trim();
  const el = document.getElementById("addPostStatus");
  if (!text) { el.innerHTML = err("type something first"); return; }
  const { ok, error } = await safeFetch(`${API}/style/add_post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!ok) { el.innerHTML = err(error); return; }
  el.textContent = "added as post example ✓";
  document.getElementById("addPostText").value = "";
  loadCorpusStats();
});

// ── Add reply example ─────────────────────────────────────────
document.getElementById("addReplyBtn").addEventListener("click", async () => {
  const text = document.getElementById("addReplyText").value.trim();
  const el = document.getElementById("addReplyStatus");
  if (!text) { el.innerHTML = err("type something first"); return; }
  const { ok, error } = await safeFetch(`${API}/style/add_reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!ok) { el.innerHTML = err(error); return; }
  el.textContent = "added as reply example ✓";
  document.getElementById("addReplyText").value = "";
  loadCorpusStats();
});

// ── Generate post ─────────────────────────────────────────────
document.getElementById("generateBtn").addEventListener("click", async () => {
  const statusEl = document.getElementById("generateStatus");
  const listEl   = document.getElementById("candidateList");
  statusEl.textContent = "generating…";
  listEl.innerHTML = "";
  const { ok, data, error } = await safeFetch(`${API}/generate`, { method: "POST" });
  if (!ok) { statusEl.innerHTML = err(error); return; }
  statusEl.innerHTML = data.accepted
    ? `<span class="accepted">accepted after ${data.attempts} attempt(s)</span>`
    : `<span class="rejected">nothing cleared the style bar after ${data.attempts} attempt(s) — pick one manually below</span>`;
  for (const c of data.candidates) {
    const li = document.createElement("li");
    li.innerHTML = `
      <div>${c.text} ${c.hashtags.join(" ")}</div>
      <div class="score">style score: ${c.style_score.toFixed(3)}</div>
      <button data-text="${c.text}" data-tags="${c.hashtags.join(",")}">Post this</button>
    `;
    li.querySelector("button").addEventListener("click", e => postCandidate(e.target));
    listEl.appendChild(li);
  }
});

async function postCandidate(btn) {
  const text = btn.dataset.text;
  const hashtags = btn.dataset.tags ? btn.dataset.tags.split(",").filter(Boolean) : [];
  const { ok, data, error } = await safeFetch(`${API}/post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, hashtags }),
  });
  if (!ok) { btn.textContent = `failed: ${error}`; return; }
  btn.textContent = data.status === "drafted" ? "drafted ✓" : `posted — id ${data.tweet_id}`;
  btn.disabled = true;
}

// ── Generate reply for a specific tweet ───────────────────────
let _pendingReplyId = "";
let _pendingUsername = "";

document.getElementById("generateReplyBtn").addEventListener("click", async () => {
  const url  = document.getElementById("replyTweetUrl").value.trim();
  const text = document.getElementById("replyTweetText").value.trim();
  const statusEl  = document.getElementById("replyGenerateStatus");
  const previewEl = document.getElementById("replyPreview");

  if (!url && !text) { statusEl.innerHTML = err("paste a URL or tweet text first"); return; }

  statusEl.textContent = "generating reply…";
  previewEl.classList.add("hidden");

  const { ok, data, error } = await safeFetch(`${API}/generate/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tweet_url: url, tweet_text: text }),
  });
  if (!ok) { statusEl.innerHTML = err(error); return; }

  statusEl.textContent = "";
  _pendingReplyId = data.original_tweet_id || "";
  _pendingUsername = data.original_username || "";

  document.getElementById("replyPreviewText").textContent =
    data.reply.text + " " + data.reply.hashtags.join(" ");
  document.getElementById("replyPreviewScore").textContent =
    `style score: ${data.reply.style_score.toFixed(3)}`;
  document.getElementById("replySendStatus").textContent = "";
  document.getElementById("sendReplyBtn").disabled = false;
  document.getElementById("sendReplyBtn").textContent = "Send reply";
  previewEl.classList.remove("hidden");
});

document.getElementById("sendReplyBtn").addEventListener("click", async () => {
  const replyText = document.getElementById("replyPreviewText").textContent;
  const statusEl  = document.getElementById("replySendStatus");
  const btn       = document.getElementById("sendReplyBtn");

  if (!_pendingReplyId) {
    statusEl.innerHTML = err("no tweet ID — paste a URL (not just text) to reply to a specific tweet");
    return;
  }

  const { ok, data, error } = await safeFetch(`${API}/post/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: replyText, hashtags: [], in_reply_to_id: _pendingReplyId, mention_username: _pendingUsername }),
  });
  if (!ok) { statusEl.innerHTML = err(error); return; }
  const sent = data.status === "drafted" ? "drafted ✓" : `sent ✓ — tweet id ${data.tweet_id}`;
  const method = data.as_mention ? " (posted as @mention — free tier fallback)" : "";
  statusEl.textContent = sent + method;
  btn.disabled = true;
});

// ── Settings ─────────────────────────────────────────────────
async function loadSettings() {
  const { ok, data } = await safeFetch(`${API}/settings`);
  if (!ok) return;
  document.getElementById("postModeSelect").value  = data.post_mode;
  document.getElementById("thresholdInput").value  = data.style_score_threshold;
  document.getElementById("maxRetriesInput").value = data.max_retries;
}

document.getElementById("saveSettingsBtn").addEventListener("click", async () => {
  const el = document.getElementById("settingsStatus");
  const { ok, data, error } = await safeFetch(`${API}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      post_mode: document.getElementById("postModeSelect").value,
      style_score_threshold: parseFloat(document.getElementById("thresholdInput").value),
      max_retries: parseInt(document.getElementById("maxRetriesInput").value, 10),
    }),
  });
  if (!ok) { el.innerHTML = err(error); return; }
  el.textContent = `saved — mode: ${data.post_mode}, threshold: ${data.style_score_threshold}`;
});

// ── Auto-post scheduler ───────────────────────────────────────
document.getElementById("startSchedulerBtn").addEventListener("click", async () => {
  const body = { times_per_day: parseInt(document.getElementById("timesPerDayInput").value, 10) };
  const secs = document.getElementById("intervalSecondsInput").value;
  if (secs) body.interval_seconds = parseInt(secs, 10);
  const { ok, data, error } = await safeFetch(`${API}/scheduler/start`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  document.getElementById("postSchedulerStatus").textContent = ok
    ? (data.interval_seconds ? `started — every ${data.interval_seconds}s` : `started — ${data.times_per_day} posts/day`)
    : `failed: ${error}`;
});

document.getElementById("stopSchedulerBtn").addEventListener("click", async () => {
  const { ok, data, error } = await safeFetch(`${API}/scheduler/stop`, { method: "POST" });
  document.getElementById("postSchedulerStatus").textContent = ok ? `stopped` : `failed: ${error}`;
  document.getElementById("postCountdown").textContent = "";
});

document.getElementById("runNowBtn").addEventListener("click", async () => {
  const { ok, error } = await safeFetch(`${API}/scheduler/run_now`, { method: "POST" });
  document.getElementById("postSchedulerStatus").textContent = ok
    ? "triggered — check History in a moment"
    : `failed: ${error}`;
});

// ── Auto-reply scheduler ──────────────────────────────────────
document.getElementById("startReplyBtn").addEventListener("click", async () => {
  const body = { interval_minutes: parseInt(document.getElementById("replyIntervalInput").value, 10) };
  const { ok, data, error } = await safeFetch(`${API}/scheduler/reply/start`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  document.getElementById("replySchedulerStatus").textContent = ok
    ? `started — checking every ${data.interval_minutes} min`
    : `failed: ${error}`;
});

document.getElementById("stopReplyBtn").addEventListener("click", async () => {
  const { ok, error } = await safeFetch(`${API}/scheduler/reply/stop`, { method: "POST" });
  document.getElementById("replySchedulerStatus").textContent = ok ? "stopped" : `failed: ${error}`;
  document.getElementById("replyCountdown").textContent = "";
});

// ── Browser login ─────────────────────────────────────────────
document.getElementById("browserLoginBtn").addEventListener("click", async () => {
  const el = document.getElementById("browserStatus");
  el.textContent = "opening browser…";
  const { ok, data, error } = await safeFetch(`${API}/browser/login`, { method: "POST" });
  if (!ok) { el.innerHTML = err(error); return; }
  el.textContent = data.message;
  pollLoginStatus();
});

async function pollLoginStatus() {
  const el = document.getElementById("browserStatus");
  const loginBtn = document.getElementById("browserLoginBtn");
  const { ok, data } = await safeFetch(`${API}/browser/status`);
  if (!ok) return;
  if (data.state === "done" || data.session_exists) {
    el.textContent = "Connected to Twitter ✓";
    if (loginBtn) loginBtn.textContent = "Re-login Twitter";
    return;
  }
  if (data.state === "error") {
    el.innerHTML = err(data.message);
    return;
  }
  el.textContent = data.message || "waiting for login…";
  setTimeout(pollLoginStatus, 3000);
}

// check session status on page load
pollLoginStatus();

// ── Feed reply scheduler ──────────────────────────────────────
document.getElementById("startFeedReplyBtn").addEventListener("click", async () => {
  const body = {
    interval_minutes: parseInt(document.getElementById("feedIntervalInput").value, 10),
    max_per_day: parseInt(document.getElementById("feedMaxPerDayInput").value, 10),
    active_hours_start: parseInt(document.getElementById("feedStartHourInput").value, 10),
    active_hours_end: parseInt(document.getElementById("feedEndHourInput").value, 10),
  };
  const { ok, data, error } = await safeFetch(`${API}/scheduler/feed_reply/start`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  document.getElementById("feedReplyStatus").textContent = ok
    ? `started — checks every ${data.interval_minutes} min, max ${data.max_per_day}/day`
    : `failed: ${error}`;
});

document.getElementById("stopFeedReplyBtn").addEventListener("click", async () => {
  const { ok, error } = await safeFetch(`${API}/scheduler/feed_reply/stop`, { method: "POST" });
  document.getElementById("feedReplyStatus").textContent = ok ? "stopped" : `failed: ${error}`;
  document.getElementById("feedReplyCountdown").textContent = "";
});

document.getElementById("feedReplyNowBtn").addEventListener("click", async () => {
  const { ok, error } = await safeFetch(`${API}/scheduler/feed_reply/run_now`, { method: "POST" });
  document.getElementById("feedReplyStatus").textContent = ok
    ? "triggered — check History + terminal for live logs"
    : `failed: ${error}`;
});

// ── History ───────────────────────────────────────────────────
function badge(s) {
  const known = ["posted", "drafted", "failed", "skipped"];
  const cls = known.includes(s) ? s : "skipped";
  return `<span class="badge badge-${cls}">${s}</span>`;
}

async function refreshHistory() {
  const { ok, data } = await safeFetch(`${API}/history`);
  const el = document.getElementById("historyList");
  if (!ok) { el.innerHTML = `<li class="error-text">could not load history</li>`; return 0; }
  el.innerHTML = data.history.slice().reverse().map(h => {
    const e = h.error ? `<div class="error-text">${h.error}</div>` : "";
    return `<li>${badge(h.status)}${h.text || "(no text)"}<div class="score">${h.posted_at}</div>${e}</li>`;
  }).join("") || "<li>(empty)</li>";
  return data.history.length;
}

document.getElementById("refreshHistoryBtn").addEventListener("click", refreshHistory);

// ── Live tick ─────────────────────────────────────────────────
let lastHistoryLen = 0;

function setBadge(id, on) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = on ? "ON" : "OFF";
  el.className = "scheduler-badge " + (on ? "on" : "off");
}

async function tick() {
  const { ok, data } = await safeFetch(`${API}/scheduler/status`);
  if (ok) {
    setBadge("postSchedulerBadge", data.post_running);
    setBadge("replySchedulerBadge", data.reply_running);
    setBadge("feedReplyBadge", data.feed_reply_running);

    const feedCd = document.getElementById("feedReplyCountdown");
    if (data.feed_reply_running && data.feed_reply_next_run) {
      const s = Math.max(0, Math.round((new Date(data.feed_reply_next_run) - new Date()) / 1000));
      feedCd.textContent = s > 60 ? `Next feed check in: ${Math.round(s/60)}m` : `Next feed check in: ${s}s`;
    } else { feedCd.textContent = ""; }

    const todayEl = document.getElementById("feedReplyTodayCount");
    if (todayEl && data.feed_reply_today !== undefined) {
      todayEl.textContent = `Replies today: ${data.feed_reply_today}`;
    }

    const postCd = document.getElementById("postCountdown");
    if (data.post_running && data.post_next_run) {
      const s = Math.max(0, Math.round((new Date(data.post_next_run) - new Date()) / 1000));
      postCd.textContent = s > 0 ? `Next post in: ${s}s` : "Posting now…";
    } else { postCd.textContent = ""; }

    const replyCd = document.getElementById("replyCountdown");
    if (data.reply_running && data.reply_next_run) {
      const s = Math.max(0, Math.round((new Date(data.reply_next_run) - new Date()) / 1000));
      replyCd.textContent = s > 60
        ? `Next mention check in: ${Math.round(s / 60)}m`
        : `Next mention check in: ${s}s`;
    } else { replyCd.textContent = ""; }
  }

  const newLen = await refreshHistory();
  if (newLen > lastHistoryLen) {
    document.getElementById("postCountdown").textContent = "Cycle just ran! See History below.";
  }
  lastHistoryLen = newLen;
}

loadSettings();
loadCorpusStats();
refreshHistory().then(n => (lastHistoryLen = n));
setInterval(tick, 3000);
