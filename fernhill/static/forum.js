(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;

  F.pages.forum = async function () {
    const course = Number(F.params.get('course'));
    let page = 1;
    $('#f-back').href = `/course?id=${course}`;

    async function load() {
      const r = await F.api(`/api/forum/${course}?page=${page}`);
      if (!r.ok) return F.toast(r.data.error || 'Could not load the discussion.', 'error');
      const d = r.data;
      $('#threads').innerHTML = d.threads.map((t) => `<li class="thread-item"><a href="/thread?id=${t.id}">${esc(t.title)}</a>
          <span class="muted small">${esc(t.author)} · ${F.date(new Date(t.created * 1000).toISOString())} · ${F.plural(t.reply_count, 'reply').replace('replys', 'replies')} · ♥ ${t.likes}</span></li>`).join('');
      $('#f-page').textContent = `Page ${d.page} of ${d.pages}`;
      $('#f-prev').disabled = d.page <= 1;
      $('#f-next').disabled = d.page >= d.pages;
    }
    $('#f-prev').addEventListener('click', () => { page -= 1; load(); });
    $('#f-next').addEventListener('click', () => { page += 1; load(); });
    $('#t-body').addEventListener('input', (e) => { $('#t-count').textContent = `${e.target.value.length} / 1000`; });
    $('#new-thread').addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = $('#t-title').value.trim();
      const body = $('#t-body').value.trim();
      if (!title || !body) return F.say($('#t-msg'), 'Write a title and a message.', 'error');
      const r = await F.api(`/api/forum/${course}`, { title, body });
      if (!r.ok) return F.say($('#t-msg'), r.data.error || 'Could not post.', 'error');
      location.href = `/thread?id=${r.data.id}`;
    });
    await load();
  };
})();
