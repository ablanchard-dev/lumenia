/* Lumenia — SPA : consentement → parcours cognitif → chat multi-conversations */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const screens = {
    consent: $("screen-consent"),
    challenge: $("screen-challenge"),
    chat: $("screen-chat"),
  };

  const state = {
    parcours: null,       // {steps:[{id,dimension,label,kind,question}], i, results:[], failures}
    sending: false,
    convs: [],            // [{id,title,createdAt,messages:[{role,content}]}]
    activeId: null,
    consentAccepted: false,
  };

  /* ---------------- utilitaires ---------------- */

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function show(name) {
    Object.entries(screens).forEach(([k, el]) => { el.hidden = k !== name; });
    if (name === "chat") $("chat-input").focus();
    if (name === "challenge") $("challenge-input").focus();
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* Mini-rendu markdown sûr : échappe tout, puis gras/italique/listes. */
  function renderMarkdown(text) {
    const lines = escapeHtml(text).split("\n");
    let html = "", list = null;
    const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
    for (const raw of lines) {
      const line = raw.trim();
      const ul = line.match(/^[-•*]\s+(.*)/);
      const ol = line.match(/^\d+[.)]\s+(.*)/);
      if (ul || ol) {
        const tag = ul ? "ul" : "ol";
        if (list !== tag) { closeList(); html += `<${tag}>`; list = tag; }
        html += `<li>${inline(ul ? ul[1] : ol[1])}</li>`;
      } else if (line === "") {
        closeList();
      } else {
        closeList();
        html += `<p>${inline(line)}</p>`;
      }
    }
    closeList();
    return html;

    function inline(s) {
      return s
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/\*([^*]+)\*/g, "<em>$1</em>");
    }
  }

  /* ---------------- thème ---------------- */

  const savedTheme = localStorage.getItem("lumenia.theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;

  $("theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("lumenia.theme", next);
  });

  /* ---------------- écran 1 : consentement ---------------- */

  $("consent-checkbox").addEventListener("change", (e) => {
    $("consent-btn").disabled = !e.target.checked;
  });

  $("consent-btn").addEventListener("click", async () => {
    const btn = $("consent-btn");
    btn.disabled = true;
    btn.textContent = "Un instant…";
    try {
      await api("/consent?accepted=true", { method: "POST" });
      startParcours();
    } catch {
      $("consent-error").hidden = false;
      $("consent-error").textContent =
        "Impossible de joindre le serveur. Vérifie que le backend tourne, puis réessaie.";
      btn.textContent = "Continuer";
      btn.disabled = false;
    }
  });

  /* ---------------- écran d'intro animée ---------------- */

  const introEl = $("screen-splash");

  function dismissIntro(then) {
    introEl.classList.add("fade");
    setTimeout(() => { introEl.hidden = true; if (then) then(); }, 600);
  }

  function hideIntroNow() { introEl.hidden = true; }

  $("intro-enter").addEventListener("click", () => {
    dismissIntro(() => {
      if (state.consentAccepted) startParcours();
      else show("consent");
    });
  });

  /* ---------------- écran 2 : mini-parcours cognitif ---------------- */

  // Mémorise les épreuves déjà proposées sur cet appareil pour varier les tirages.
  const SEEN_KEY = "lumenia.seenChallenges";

  function loadSeen() {
    try {
      const a = JSON.parse(localStorage.getItem(SEEN_KEY));
      return Array.isArray(a) ? a : [];
    } catch { return []; }
  }

  async function startParcours() {
    show("challenge");
    $("challenge-step").textContent = "…";
    $("challenge-question").textContent = "…";
    try {
      const seen = loadSeen();
      const qs = seen.length ? "?exclude=" + encodeURIComponent(seen.join(",")) : "";
      const data = await api("/entry/parcours" + qs);
      const ids = data.steps.map((s) => s.id);
      localStorage.setItem(SEEN_KEY, JSON.stringify([...new Set([...seen, ...ids])].slice(-40)));
      state.parcours = { steps: data.steps, i: 0, results: [], failures: 0 };
      renderStep();
    } catch {
      $("challenge-question").textContent =
        "Le serveur ne répond pas. Vérifie que le backend tourne, puis recharge la page.";
    }
  }

  function currentStep() {
    const p = state.parcours;
    return p ? p.steps[p.i] : null;
  }

  function renderStep() {
    const p = state.parcours;
    const step = currentStep();
    p.failures = 0;

    const progress = $("parcours-progress");
    progress.innerHTML = "";
    p.steps.forEach((_, idx) => {
      const dot = document.createElement("span");
      dot.className = "p-dot" + (idx < p.i ? " done" : idx === p.i ? " current" : "");
      progress.appendChild(dot);
    });

    $("challenge-step").textContent = `Épreuve ${p.i + 1} sur ${p.steps.length} — ${step.label}`;
    $("challenge-question").textContent = step.question;
    $("challenge-input").value = "";
    $("challenge-input").placeholder =
      step.kind === "open" ? "Pas de bonne réponse — écris ce qui te vient…" : "Ta réponse…";
    $("challenge-feedback").textContent = "";
    $("challenge-feedback").classList.remove("ok");
    $("challenge-skip").hidden = true;
    $("challenge-btn").disabled = false;
    $("challenge-input").focus();
  }

  async function submitStep() {
    const step = currentStep();
    const answer = $("challenge-input").value.trim();
    if (!answer || !step) return;
    const p = state.parcours;
    const btn = $("challenge-btn");
    btn.disabled = true;
    const fb = $("challenge-feedback");
    fb.textContent = "…";
    try {
      const r = await api("/entry/verify", {
        method: "POST",
        body: JSON.stringify({ challenge_id: step.id, answer }),
      });
      if (r.ok) {
        p.results.push({
          id: step.id, dimension: step.dimension, ok: true,
          answer, attempts: p.failures + 1, skipped: false,
        });
        fb.classList.add("ok");
        fb.textContent = step.kind === "open" ? "Merci. On continue." : "C'est ça.";
        setTimeout(nextStep, 650);
      } else {
        p.failures += 1;
        fb.textContent =
          p.failures === 1
            ? "Pas tout à fait — tente une autre piste."
            : `Indice : ${r.hint || "pense autrement."}`;
        if (p.failures >= 2) $("challenge-skip").hidden = false;
        btn.disabled = false;
        $("challenge-input").select();
      }
    } catch {
      fb.textContent = "Erreur de connexion au serveur — réessaie.";
      btn.disabled = false;
    }
  }

  function skipStep() {
    const p = state.parcours;
    const step = currentStep();
    if (!step) return;
    p.results.push({
      id: step.id, dimension: step.dimension, ok: false,
      answer: $("challenge-input").value.trim(), attempts: p.failures, skipped: true,
    });
    nextStep();
  }

  function nextStep() {
    const p = state.parcours;
    if (p.i + 1 < p.steps.length) {
      p.i += 1;
      renderStep();
    } else {
      completeParcours();
    }
  }

  async function completeParcours() {
    const p = state.parcours;
    $("challenge-btn").disabled = true;
    $("challenge-skip").hidden = true;
    const fb = $("challenge-feedback");
    fb.classList.add("ok");
    const okCount = p.results.filter((r) => r.ok && !r.skipped).length;
    fb.textContent = okCount > 0
      ? "C'est ouvert. Bienvenue."
      : "Le seuil s'ouvre quand même — ce qui compte, c'est ta façon de chercher. Bienvenue.";
    try {
      await api("/entry/complete", {
        method: "POST",
        body: JSON.stringify({ results: p.results }),
      });
    } catch { /* l'entrée reste ouverte même si l'enregistrement échoue */ }
    localStorage.setItem("lumenia.entered", "1");
    setTimeout(enterChat, okCount > 0 ? 700 : 1600);
  }

  $("challenge-btn").addEventListener("click", submitStep);
  $("challenge-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); submitStep(); }
  });
  $("challenge-skip").addEventListener("click", skipStep);

  /* ---------------- conversations (localStorage) ---------------- */

  const CONVS_KEY = "lumenia.convs";
  const ACTIVE_KEY = "lumenia.activeConv";

  function loadConvs() {
    try {
      const data = JSON.parse(localStorage.getItem(CONVS_KEY));
      return Array.isArray(data) ? data : [];
    } catch { return []; }
  }

  function saveConvs() {
    localStorage.setItem(CONVS_KEY, JSON.stringify(state.convs));
  }

  function activeConv() {
    return state.convs.find((c) => c.id === state.activeId) || null;
  }

  function createConv() {
    const c = {
      id: "c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      title: "Nouvelle conversation",
      createdAt: Date.now(),
      messages: [],
    };
    state.convs.unshift(c);
    state.activeId = c.id;
    localStorage.setItem(ACTIVE_KEY, c.id);
    saveConvs();
    return c;
  }

  function ensureActiveConv() {
    if (!activeConv()) {
      state.activeId = localStorage.getItem(ACTIVE_KEY);
      if (!activeConv()) {
        if (state.convs.length) {
          state.activeId = state.convs[0].id;
          localStorage.setItem(ACTIVE_KEY, state.activeId);
        } else {
          createConv();
        }
      }
    }
    return activeConv();
  }

  function setActive(id) {
    closeNav();
    if (state.activeId === id) return;
    state.activeId = id;
    localStorage.setItem(ACTIVE_KEY, id);
    renderConvList();
    renderMessages();
    $("chat-input").focus();
  }

  function newConv() {
    closeNav();
    const cur = activeConv();
    if (cur && cur.messages.length === 0) {
      $("chat-input").focus();
      return; // la conversation vide en cours EST la nouvelle
    }
    createConv();
    renderConvList();
    renderMessages();
    $("chat-input").focus();
  }

  function deleteConv(id) {
    const conv = state.convs.find((c) => c.id === id);
    if (!conv) return;
    if (conv.messages.length && !window.confirm("Supprimer cette conversation ? Elle sera effacée de cet appareil.")) {
      return;
    }
    state.convs = state.convs.filter((c) => c.id !== id);
    if (state.activeId === id) {
      state.activeId = state.convs.length ? state.convs[0].id : null;
      if (!state.activeId) createConv();
      else localStorage.setItem(ACTIVE_KEY, state.activeId);
    }
    saveConvs();
    renderConvList();
    renderMessages();
  }

  function renderConvList() {
    const list = $("conv-list");
    list.innerHTML = "";
    state.convs.forEach((c) => {
      const item = document.createElement("div");
      item.className = "conv-item" + (c.id === state.activeId ? " active" : "");

      const open = document.createElement("button");
      open.className = "conv-open";
      open.type = "button";
      open.textContent = c.title;
      open.title = c.title;
      open.addEventListener("click", () => setActive(c.id));

      const del = document.createElement("button");
      del.className = "conv-del";
      del.type = "button";
      del.setAttribute("aria-label", "Supprimer cette conversation");
      del.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';
      del.addEventListener("click", (e) => { e.stopPropagation(); deleteConv(c.id); });

      item.appendChild(open);
      item.appendChild(del);
      list.appendChild(item);
    });
  }

  /* ---------------- écran 3 : chat ---------------- */

  function enterChat() {
    state.convs = loadConvs();
    state.activeId = localStorage.getItem(ACTIVE_KEY);
    ensureActiveConv();
    show("chat");
    renderConvList();
    renderMessages();
    refreshRisk();
  }

  async function refreshRisk() {
    try {
      const r = await api("/risk");
      if (r.risk_flag) $("safety-banner").hidden = false;
    } catch { /* non bloquant */ }
  }

  const input = $("chat-input");
  const sendBtn = $("send-btn");
  const messagesEl = $("messages");

  input.addEventListener("input", () => {
    sendBtn.disabled = input.value.trim() === "" || state.sending;
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 168) + "px";
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      $("composer").requestSubmit();
    }
  });

  const MARK_IMG = '<img class="mark-img" src="/static/logo-mark.png" alt="">';

  function appendMessageEl(role, text) {
    const welcome = messagesEl.querySelector(".welcome");
    if (welcome) welcome.remove();

    const msg = document.createElement("div");
    msg.className = `msg ${role}`;
    const body = document.createElement("div");
    body.className = "msg-body";

    if (role === "assistant") {
      const avatar = document.createElement("div");
      avatar.className = "msg-avatar";
      avatar.innerHTML = MARK_IMG;
      avatar.setAttribute("aria-hidden", "true");
      msg.appendChild(avatar);
      body.innerHTML = renderMarkdown(text);
    } else {
      body.textContent = text;
    }
    msg.appendChild(body);
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return body;
  }

  function renderMessages() {
    messagesEl.innerHTML = "";
    const conv = activeConv();
    if (!conv || conv.messages.length === 0) {
      messagesEl.appendChild($("welcome-tpl").content.cloneNode(true));
      return;
    }
    conv.messages.forEach((m) => appendMessageEl(m.role, m.content));
  }

  // Suggestions du message d'accueil (re-créées à chaque rendu → délégation).
  messagesEl.addEventListener("click", (e) => {
    const btn = e.target.closest(".suggestion");
    if (btn) send(btn.dataset.text);
  });

  function addTyping() {
    const msg = document.createElement("div");
    msg.className = "msg assistant";
    msg.id = "typing-msg";
    msg.innerHTML =
      '<div class="msg-avatar" aria-hidden="true">' + MARK_IMG + '</div>' +
      '<div class="msg-body"><span class="typing" role="status" aria-label="Lumenia écrit"><span></span><span></span><span></span></span></div>';
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function send(text) {
    if (state.sending) return;
    const conv = ensureActiveConv();
    const history = conv.messages.slice(-20);

    state.sending = true;
    sendBtn.disabled = true;
    appendMessageEl("user", text);
    conv.messages.push({ role: "user", content: text });
    if (conv.title === "Nouvelle conversation") {
      conv.title = text.length > 38 ? text.slice(0, 38) + "…" : text;
      renderConvList();
    }
    saveConvs();
    addTyping();
    try {
      const r = await api("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, history }),
      });
      $("typing-msg")?.remove();
      appendMessageEl("assistant", r.reply);
      conv.messages.push({ role: "assistant", content: r.reply });
      saveConvs();
      if (r.risk_flag) $("safety-banner").hidden = false;
    } catch {
      $("typing-msg")?.remove();
      appendMessageEl(
        "assistant",
        "La connexion au serveur a échoué. Ton message n'est pas perdu — réessaie dans un instant."
      );
    } finally {
      state.sending = false;
      sendBtn.disabled = input.value.trim() === "";
      input.focus();
    }
  }

  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    input.style.height = "auto";
    send(text);
  });

  $("new-chat").addEventListener("click", newConv);
  $("new-chat-mobile").addEventListener("click", newConv);

  $("safety-close").addEventListener("click", () => {
    $("safety-banner").hidden = true;
  });

  /* ---- volet conversations (fenêtres étroites) ---- */

  const appEl = $("screen-chat");
  const scrimEl = $("nav-scrim");

  function openNav() {
    appEl.classList.add("nav-open");
    scrimEl.hidden = false;
    $("nav-toggle").setAttribute("aria-expanded", "true");
  }

  function closeNav() {
    appEl.classList.remove("nav-open");
    scrimEl.hidden = true;
    $("nav-toggle").setAttribute("aria-expanded", "false");
  }

  $("nav-toggle").addEventListener("click", () => {
    appEl.classList.contains("nav-open") ? closeNav() : openNav();
  });
  scrimEl.addEventListener("click", closeNav);

  /* ---------------- routage initial ---------------- */

  (async function init() {
    let accepted = false;
    try {
      const c = await api("/consent");
      accepted = !!c.accepted;
    } catch { accepted = false; }
    state.consentAccepted = accepted;

    const entered = location.hash === "#chat" || localStorage.getItem("lumenia.entered") === "1";

    // raccourcis & retours : on saute l'intro animée
    if (location.hash === "#seuil") {
      hideIntroNow();
      return accepted ? startParcours() : show("consent");
    }
    if (entered && accepted) {
      hideIntroNow();
      return enterChat();
    }
    // première visite : l'intro s'anime, l'utilisateur clique « Entrer dans le seuil »
  })();
})();
