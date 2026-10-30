(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;

  F.pages.thread = async function () {
    const id = Number(F.params.get('id'));
    let t;
    const when = (ts) => F.dateTime(new Date(ts * 1000).toISOString());
    const post = (p, opening) => `<p class="post-meta"><strong>${esc(p.author)}</strong> · ${when(p.created)}</p>
      ${opening ? `<h1>${esc(t.title)}</h1>` : ''}<p class="post-body">${esc(p.body)}</p>
      <p class="post-actions"><button type="button" class="link like" data-id="${p.id}">♥ Like</button> <span class="muted">${p.likes}</span>
      ${p.author === t.me ? `<button type="button" class="link edit" data-id="${p.id}">Edit</button>` : ''}</p>`;

    function draw() {
      document.title = `${t.title} · Fernhill Academy`;
      $('#t-back').href = `/forum?course=${t.course}`;
      $('#opening').innerHTML = post(t, true);
      $('#opening').dataset.id = t.id;
      $('#r-count').textContent = t.replies.length ? F.plural(t.replies.length, 'reply').replace('replys', 'replies') : 'No replies yet';
      $('#replies').innerHTML = t.replies.map((r) => `<li class="card post" data-id="${r.id}">${post(r, false)}</li>`).join('');
    }

    const r = await F.api(`/api/threads/${id}`);
    if (!r.ok) {
      $('#loading').textContent = r.data.error || 'We couldn\'t find that discussion.';
      return;
    }
    t = r.data;
    draw();
    $('#loading').hidden = true;
    $('#thread').hidden = false;

    $('#thread').addEventListener('click', async (e) => {
      const like = e.target.closest('.like');
      if (like) {
        const res = await F.api(`/api/posts/${like.dataset.id}/like`, {});
        if (res.ok) { t = res.data; draw(); }
        return;
      }
      const edit = e.target.closest('.edit');
      if (edit) {
        const holder = edit.closest('.post');
        const body = holder.querySelector('.post-body');
        holder.insertAdjacentHTML('beforeend', `<form class="edit-form" novalidate><label class="sr-only" for="e-${edit.dataset.id}">Edit</label>
          <textarea id="e-${edit.dataset.id}" rows="4">${esc(body.textContent)}</textarea><p class="hint">Up to 1000 characters.</p>
          <div class="actions"><button type="submit" class="btn btn-small">Save</button></div></form>`);
        edit.hidden = true;
      }
    });
    $('#thread').addEventListener('submit', async (e) => {
      const form = e.target.closest('.edit-form');
      if (!form) return;
      const pid = form.closest('.post').dataset.id;
      const res = await F.api(`/api/posts/${pid}/edit`, { body: form.querySelector('textarea').value.trim() });
      if (!res.ok) return F.toast(res.data.error || 'Could not save your edit.', 'error');
      t = res.data;
      draw();
      F.toast('Post updated.', 'success');
    });
    $('#r-body').addEventListener('input', (e) => { $('#r-chars').textContent = `${e.target.value.length} / 1000`; });
    $('#reply-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const body = $('#r-body').value.trim();
      if (!body) return F.say($('#r-msg'), 'Write a reply first.', 'error');
      const res = await F.api(`/api/threads/${id}/reply`, { body });
      if (!res.ok) return F.say($('#r-msg'), res.data.error || 'Could not post your reply.', 'error');
      t = res.data;
      draw();
      $('#r-body').value = '';
      F.say($('#r-msg'), 'Reply posted.', 'success');
    });
  };
})();
