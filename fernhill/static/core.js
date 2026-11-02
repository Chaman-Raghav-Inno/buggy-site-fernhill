(function () {
  'use strict';

  const F = (window.Fernhill = window.Fernhill || {});
  F.pages = F.pages || {};
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  F.$ = $;
  F.$$ = $$;
  F.esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ENTITIES[c]);
  F.params = new URLSearchParams(location.search);
  F.role = document.body.dataset.role || '';
  F.EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  document.addEventListener('submit', (e) => {
    if (!e.target.matches('[data-native]')) e.preventDefault();
  }, true);

  F.api = async function (path, body) {
    const opts = body === undefined
      ? { credentials: 'same-origin' }
      : { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    let res;
    try {
      res = await fetch(path, opts);
    } catch (e) {
      return { ok: false, status: 0, data: { error: 'You appear to be offline. Try again.' } };
    }
    if (res.status === 401 && !path.startsWith('/api/login')) {
      location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search);
    }
    let data = {};
    try {
      data = await res.json();
    } catch (e) {
      data = {};
    }
    return { ok: res.ok, status: res.status, data };
  };

  let toastTimer;
  F.toast = function (text, kind) {
    const el = $('#toast');
    el.textContent = text;
    el.className = 'toast' + (kind ? ' toast-' + kind : '');
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 3500);
  };
  F.say = function (el, text, kind) {
    el.textContent = text || '';
    el.classList.toggle('error', kind === 'error');
    el.classList.toggle('success', kind === 'success');
  };
  F.plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  F.date = (iso) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  F.dateTime = (iso) => new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  F.duration = (minutes) => `${Math.round(minutes / 60)}h ${minutes % 60}m`;

  F.card = (c) => `<article class="card course-card">
      <p class="eyebrow">${F.esc(c.topic)} · ${F.esc(c.level)}</p>
      <h3><a href="/course?id=${c.id}">${F.esc(c.title)}</a></h3>
      <p class="muted">${F.esc(c.summary)}</p>
      <p class="meta"><span>★ ${c.rating.toFixed(1)} (${c.reviews})</span><span>${F.plural(c.lessons, 'lesson')} · ${F.duration(c.minutes)}</span></p>
    </article>`;

  function setupChrome() {
    const page = document.body.dataset.page;
    $$('.nav a').forEach((a) => { if (a.dataset.nav === page) a.setAttribute('aria-current', 'page'); });
    const logout = $('#logout');
    if (logout) {
      logout.addEventListener('click', async () => {
        await F.api('/api/logout', {});
        location.href = '/';
      });
    }
  }

  document.addEventListener('DOMContentLoaded', async () => {
    setupChrome();
    const run = F.pages[document.body.dataset.page];
    if (!run) return;
    document.body.classList.add('is-loading');
    try {
      await run();
    } finally {
      document.body.classList.remove('is-loading');
    }
  });
})();
