/* Lumenia — SPA : consentement → parcours cognitif → chat multi-conversations */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const screens = {
    consent: $("screen-consent"),
    challenge: $("screen-challenge"),
    fail: $("screen-fail"),
    chat: $("screen-chat"),
  };

  // Test ÉLIMINATOIRE : part minimale de bonnes réponses (épreuves notées
  // seulement) pour ouvrir l'accès. Valeur fixée par le protocole clinique de
  // Blandine (psychologue) : seuil exigeant pour que réussir = sensation d'accomplir
  // quelque chose, et non de passer à la moitié. En dessous : accès fermé, retente
  // possible. (Sur 30 questions tirées, 0.85 ⇒ il faut 26/30 bonnes réponses.)
  const ENTRY_PASS_RATIO = 0.85;

  const state = {
    parcours: null,       // {steps:[{id,dimension,label,kind,question}], i, results:[], failures}
    sending: false,
    convs: [],            // [{id,title,createdAt,messages:[{role,content}]}]
    activeId: null,
    consentAccepted: false,
  };

  /* ---------------- utilitaires ---------------- */

  // Qui parle au backend. Sans compte : un UUIDv4 tiré une fois par navigateur. Le backend
  // ne rend que ce qui appartient à CET identifiant (journal, drapeau de risque, parcours).
  // Avant le 23/09/2026, tout était global : chacun lisait le journal des autres.
  const VISITEUR = (() => {
    let id = localStorage.getItem("lumenia.id");
    if (!id) { id = crypto.randomUUID(); localStorage.setItem("lumenia.id", id); }
    return id;
  })();

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: { "Content-Type": "application/json", "X-Lumenia-Id": VISITEUR },
    });
    if (!res.ok) {
      // Le statut et le message du serveur voyagent avec l'erreur : sans eux, chaque panne
      // se disait avec la même phrase (voir `panne`).
      let detail = "";
      try { const b = await res.json(); if (typeof b.detail === "string") detail = b.detail; } catch { /* corps non JSON */ }
      throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status, detail });
    }
    return res.json();
  }

  /* 23/09/2026 — UNE PANNE, SA PHRASE. Trop de demandes, session perdue, souci du serveur et
     coupure réseau affichaient tous « Impossible de joindre le serveur. Vérifie que le backend
     tourne » : faux trois fois sur quatre (le serveur avait répondu), et du jargon. Chaque cas dit
     maintenant ce qui se passe et quoi faire. Le 3114 reste dans toutes. */
  const TOUJOURS_3114 = "Si ça urge, le 3114 (gratuit, 24h/24) répond tout de suite, même quand Lumenia est en panne.";
  function panne(err, avant = "") {
    const s = err && err.status;
    let quoi;
    if (s === 429) quoi = (err.detail || "Beaucoup de demandes en peu de temps : attends une minute, puis réessaie.").replace(/\*\*/g, "");
    else if (s === 401) quoi = "Ta session s'est perdue. Recharge la page pour reprendre.";
    else if (s >= 500) quoi = "Lumenia a rencontré un problème de son côté. Réessaie dans un instant.";
    else if (s) quoi = "Ta demande n'a pas pu être traitée. Réessaie.";
    else quoi = "Pas de connexion à Lumenia : vérifie ton réseau, puis réessaie.";
    if (!quoi.includes("3114")) quoi += " " + TOUJOURS_3114;
    return (avant ? avant + " " : "") + quoi;
  }

  // Un lien nu ne présente pas VISITEUR : on passe par fetch, puis le navigateur
  // enregistre le fichier sous le nom annoncé par `download`.
  $("export-journal")?.addEventListener("click", async (e) => {
    e.preventDefault();
    const a = e.currentTarget;
    const res = await fetch(a.getAttribute("href"), { headers: { "X-Lumenia-Id": VISITEUR } });
    if (!res.ok) return;
    const url = URL.createObjectURL(await res.blob());
    const tmp = Object.assign(document.createElement("a"), { href: url, download: a.getAttribute("download") });
    tmp.click();
    URL.revokeObjectURL(url);
  });

  function show(name) {
    Object.entries(screens).forEach(([k, el]) => { el.hidden = k !== name; });
    if (name === "chat") $("chat-input").focus();
    if (name === "challenge") $("challenge-input").focus();
  }

  function escapeHtml(s) {
    // Guillemets et apostrophes aussi (23/09/2026, audit M-2) : sans eux, la première
    // interpolation dans un attribut ouvrirait un XSS. `&` d'abord, sinon il ré-échappe les autres.
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
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
    } catch (err) {
      $("consent-error").hidden = false;
      $("consent-error").textContent = panne(err);
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
      if (!state.consentAccepted) show("consent");
      else if (localStorage.getItem("lumenia.entryPassed") === "1") enterChat();
      else startParcours();
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

  // 23/09/2026 — la pause (L-UI-3). Le parcours est gardé sur CE navigateur à chaque épreuve et
  // repris là où on l'a laissé. La reprise ne retire PAS de parcours : `GET /entry/parcours`
  // efface ce que le serveur a constaté (garde du 17/09).
  const PARCOURS_KEY = "lumenia.parcours";

  function garderParcours() {
    const p = state.parcours;
    try { localStorage.setItem(PARCOURS_KEY, JSON.stringify({ steps: p.steps, i: p.i, results: p.results })); }
    catch { /* stockage plein ou refusé : la pause ne sera simplement pas gardée */ }
  }

  function parcoursGarde() {
    try {
      const g = JSON.parse(localStorage.getItem(PARCOURS_KEY));
      const valide = g && Array.isArray(g.steps) && g.steps.length && Array.isArray(g.results)
        && Number.isInteger(g.i) && g.i >= 0 && g.i < g.steps.length;
      return valide ? g : null;
    } catch { return null; }
  }

  function oublierParcours() {
    try { localStorage.removeItem(PARCOURS_KEY); } catch { /* rien à oublier */ }
  }

  function annoncerReprise() {
    const g = parcoursGarde();
    const note = $("intro-reprise");
    note.hidden = !g;
    note.textContent = g ? `Ton parcours est gardé sur ce navigateur : tu reprendras à l'épreuve ${g.i + 1} sur ${g.steps.length}.` : "";
  }

  async function startParcours(nouveau = false) {
    show("challenge");
    const garde = nouveau ? null : parcoursGarde();
    if (garde) {
      state.parcours = { steps: garde.steps, i: garde.i, results: garde.results, failures: 0 };
      renderStep();
      return;
    }
    oublierParcours();
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
    } catch (err) {
      $("challenge-question").textContent = panne(err);
    }
  }

  function currentStep() {
    const p = state.parcours;
    return p ? p.steps[p.i] : null;
  }


  /* Une seule porte pour griser « Valider ».
     17/09/2026 — le bouton demarrait grise sur chaque QCM sans dire pourquoi :
     on voit une action, on la clique, rien. Et sur le web une infobulle `title`
     ne s'affiche PAS sur un bouton `disabled` (le navigateur ne lui envoie aucun
     evenement de pointeur), donc la reponse doit etre une ligne VISIBLE — ici la
     zone `role="status"`, deja annoncee aux lecteurs d'ecran. */
  let raisonAffichee = "";

  function boutonValider(actif, raison = "") {
    $("challenge-btn").disabled = !actif;
    const zone = $("challenge-feedback");
    if (!actif && raison) {
      zone.textContent = raison;
      zone.classList.remove("ok");
      raisonAffichee = raison;
    } else if (actif && raisonAffichee && zone.textContent === raisonAffichee) {
      // Vu dans le navigateur : la phrase « Choisis une réponse » restait affichée
      // APRÈS le choix — elle devenait fausse. On efface, mais UNIQUEMENT notre
      // propre message : l'indice d'une mauvaise réponse vit dans la même zone et
      // doit survivre.
      zone.textContent = "";
      raisonAffichee = "";
    }
  }

  function renderStep() {
    const p = state.parcours;
    const step = currentStep();
    p.failures = 0;
    p.selected = null;
    garderParcours();

    const progress = $("parcours-progress");
    const pct = Math.round(((p.i + 1) / p.steps.length) * 100);
    // 17/09/2026 — la largeur était posée par un attribut `style="width:…"` dans la
    // chaîne HTML. Notre propre CSP (`style-src 'self'`) bloque les attributs de style :
    // la barre restait VIDE pendant tout le parcours d'entrée, sans rien signaler.
    // La propriété DOM, elle, n'est pas concernée par la CSP.
    progress.innerHTML = `<span class="p-bar"><span class="p-bar-fill"></span></span>`;
    progress.querySelector(".p-bar-fill").style.width = `${pct}%`;

    // 23/09/2026 — plus de sur-titre en capitales : la barre annonce l'épreuve et son intitulé,
    // le compteur visible reste discret à côté d'elle.
    progress.setAttribute("aria-valuenow", String(p.i + 1));
    progress.setAttribute("aria-valuemax", String(p.steps.length));
    progress.setAttribute("aria-valuetext", `Épreuve ${p.i + 1} sur ${p.steps.length} : ${step.label}`);
    $("challenge-step").textContent = `${p.i + 1} sur ${p.steps.length}`;

    const consigne = $("challenge-consigne");
    consigne.hidden = !step.consigne;
    consigne.textContent = step.consigne || "";

    $("challenge-question").textContent = step.question;
    $("challenge-feedback").textContent = "";
    $("challenge-feedback").classList.remove("ok");
    $("challenge-skip").hidden = true;

    const input = $("challenge-input");
    const choices = $("challenge-choices");

    if (step.kind === "qcm") {
      input.hidden = true;
      input.value = "";
      buildChoices(step);
      choices.hidden = false;
      boutonValider(false, "Choisis une réponse pour continuer.");   // réactivé dès qu'un choix est pris
      const first = choices.querySelector(".choice");
      if (first) first.focus();
    } else {
      choices.hidden = true;
      choices.innerHTML = "";
      input.hidden = false;
      input.value = "";
      input.placeholder =
        step.kind === "open" ? "Pas de bonne réponse — écris ce qui te vient…" : "Ta réponse…";
      boutonValider(true);
      input.focus();
    }
  }

  /* ---- QCM : 4 choix A-D, sélection unique, clavier ---- */

  function buildChoices(step) {
    const group = $("challenge-choices");
    group.classList.remove("is-locked");
    group.innerHTML = "";
    ["A", "B", "C", "D"].forEach((L) => {
      const text = step.choices && step.choices[L];
      if (!text) return;
      const opt = document.createElement("button");
      opt.type = "button";
      opt.className = "choice";
      opt.setAttribute("role", "radio");
      opt.setAttribute("aria-checked", "false");
      opt.dataset.letter = L;
      const key = document.createElement("span");
      key.className = "choice-key";
      key.setAttribute("aria-hidden", "true");
      key.textContent = L;
      const span = document.createElement("span");
      span.className = "choice-text";
      span.textContent = text;          // textContent = pas d'injection
      opt.append(key, span);
      opt.addEventListener("click", () => selectChoice(L));
      group.appendChild(opt);
    });
  }

  function selectChoice(letter) {
    const p = state.parcours;
    if (!p) return;
    p.selected = letter;
    $("challenge-choices").querySelectorAll(".choice").forEach((el) => {
      const on = el.dataset.letter === letter;
      el.classList.toggle("selected", on);
      el.classList.remove("wrong");
      el.setAttribute("aria-checked", on ? "true" : "false");
    });
    boutonValider(true);
  }

  function lockChoices(correctLetter) {
    const group = $("challenge-choices");
    group.classList.add("is-locked");
    group.querySelectorAll(".choice").forEach((el) => {
      el.disabled = true;
      if (el.dataset.letter === correctLetter) {
        el.classList.add("correct");
        el.classList.remove("wrong", "selected");
      }
    });
  }

  // Flèches pour naviguer entre les choix ; touches A-D / 1-4 pour sélectionner.
  $("challenge-choices").addEventListener("keydown", (e) => {
    const opts = [...$("challenge-choices").querySelectorAll(".choice")];
    if (!opts.length) return;
    const idx = opts.indexOf(document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowRight") {
      e.preventDefault();
      opts[(idx + 1 + opts.length) % opts.length].focus();
    } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
      e.preventDefault();
      opts[(idx - 1 + opts.length) % opts.length].focus();
    } else {
      const byLetter = { A: 0, B: 1, C: 2, D: 3 };
      const k = e.key.toUpperCase();
      const i = k in byLetter ? byLetter[k] : "1234".indexOf(e.key);
      if (i >= 0 && i < opts.length) {
        e.preventDefault();
        opts[i].focus();
        selectChoice(opts[i].dataset.letter);
      }
    }
  });

  async function submitStep() {
    const step = currentStep();
    if (!step) return;
    const p = state.parcours;
    const isQcm = step.kind === "qcm";
    // QCM : on envoie le TEXTE choisi. L'ordre et les lettres changent à chaque tirage.
    const answer = isQcm ? ((p.selected && step.choices[p.selected]) || "") : $("challenge-input").value.trim();
    if (!answer) return;
    // Pendant la verification : le bouton se grise, et « … » dit pourquoi.
    boutonValider(false);
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
        if (isQcm) lockChoices(answer);
        setTimeout(nextStep, 700);
      } else {
        p.failures += 1;
        fb.textContent =
          p.failures === 1
            ? "Pas tout à fait — tente une autre piste."
            : `Indice : ${r.hint || "pense autrement."}`;
        if (isQcm) {
          const sel = $("challenge-choices").querySelector(`.choice[data-letter="${answer}"]`);
          if (sel) sel.classList.add("wrong");
          // Par la porte, comme partout : sinon la phrase et l'etat du bouton divergent.
          boutonValider(!!p.selected, "Choisis une reponse pour continuer.");
        } else {
          boutonValider(true);
          $("challenge-input").select();
        }
        if (p.failures >= 2) $("challenge-skip").hidden = false;
      }
    } catch (err) {
      fb.textContent = panne(err);
      boutonValider(true);
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
    oublierParcours();
    boutonValider(false);
    $("challenge-skip").hidden = true;

    // Score : seules les épreuves NOTÉES comptent (l'expression libre `libre` n'a
    // pas de bonne réponse). Réussite = part de bonnes réponses ≥ ENTRY_PASS_RATIO.
    const objective = p.results.filter((r) => r.dimension !== "libre");
    const correct = objective.filter((r) => r.ok && !r.skipped).length;
    const ratio = objective.length ? correct / objective.length : 0;
    const passed = ratio >= ENTRY_PASS_RATIO;

    const fb = $("challenge-feedback");
    fb.classList.add("ok");
    fb.textContent = passed ? "C'est ouvert. Bienvenue." : "Parcours terminé.";

    try {
      await api("/entry/complete", {
        method: "POST",
        body: JSON.stringify({ results: p.results }),
      });
    } catch { /* enregistrement non bloquant */ }

    if (passed) {
      // Réussi = accès ouvert, test plus jamais reproposé sur cet appareil.
      localStorage.setItem("lumenia.entryPassed", "1");
      setTimeout(enterChat, 700);
    } else {
      // Échec = test éliminatoire : le seuil ne s'ouvre pas, mais on peut retenter.
      localStorage.removeItem("lumenia.entryPassed");
      $("fail-score").textContent = `${correct} / ${objective.length}`;
      setTimeout(() => show("fail"), 900);
    }
  }

  $("challenge-btn").addEventListener("click", submitStep);
  $("challenge-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); submitStep(); }
  });
  $("challenge-skip").addEventListener("click", skipStep);
  $("fail-retry").addEventListener("click", () => startParcours(true));
  $("challenge-pause").addEventListener("click", () => {
    garderParcours();
    show("aucun");
    annoncerReprise();
    introEl.classList.remove("fade");
    introEl.hidden = false;
    $("intro-enter").focus();
  });

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
        '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';
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
      if (r.risk_flag) showSafetyBanner();
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

  const MARK_IMG = '<img class="mark-img" src="/static/logo-mark.svg" alt="">';

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
    scrollToEnd();
  }

  // À la (ré)ouverture on atterrit sur le dernier échange, sans animation (le
  // défilement doux est réservé aux nouveaux messages). Rappelé quand le bandeau
  // de sécurité apparaît : il réduit la zone et laissait l'historique en haut.
  function scrollToEnd() {
    messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: "instant" });
  }

  function showSafetyBanner() {
    $("safety-banner").hidden = false;
    scrollToEnd();
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
      if (r.risk_flag) showSafetyBanner();
    } catch (err) {
      $("typing-msg")?.remove();
      appendMessageEl("assistant", panne(err, "Ton message n'est pas perdu."));
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

    // raccourcis (bypass de l'intro) : #chat saute au chat, #seuil rejoue le parcours
    if (location.hash === "#chat" && accepted) {
      hideIntroNow();
      return enterChat();
    }
    if (location.hash === "#seuil") {
      hideIntroNow();
      return accepted ? startParcours() : show("consent");
    }
    if (location.hash === "#fail") {  // aperçu de l'écran « seuil non franchi » (dev)
      hideIntroNow();
      $("fail-score").textContent = "22 / 30";
      return show("fail");
    }
    // sinon : l'intro animée se joue à CHAQUE ouverture, puis « Entrer dans le seuil »
    //   → consentement (1ʳᵉ fois) → parcours (si pas encore réussi) → chat (si réussi)
    if (accepted && localStorage.getItem("lumenia.entryPassed") !== "1") annoncerReprise();
  })();
})();
