(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;

  F.pages.teach = async function () {
    let data;

    function draw() {
      $('#t-courses').innerHTML = data.courses.map((c) => `<article class="card course-card">
          <h3><a href="/course?id=${c.id}">${esc(c.title)}</a></h3>
          <p class="meta"><span>${c.enrolled} of ${c.seats} students</span><span>★ ${c.rating.toFixed(1)}</span></p>
          <p><a class="btn btn-small btn-ghost" href="/api/teach/roster/${c.id}.csv" download="roster-${c.id}.csv">Download roster (CSV)</a></p>
        </article>`).join('');
      const sel = $('#t-assignment');
      const ids = [...new Map(data.queue.map((q) => [q.assignment_id, q.assignment])).entries()];
      const keep = sel.value;
      sel.innerHTML = ids.map(([id, title]) => `<option value="${id}">${esc(title)}</option>`).join('');
      if (keep && ids.some(([id]) => String(id) === keep)) sel.value = keep;
      else if (ids.length) sel.value = String(ids[ids.length - 1][0]);
      const rows = data.queue.filter((q) => String(q.assignment_id) === sel.value);
      $('#t-queue').innerHTML = rows.map((q) => `<tr><td>${esc(q.student)}</td><td>${F.dateTime(q.submitted)}</td><td><code>${esc(q.file)}</code></td>
          <td><form class="grade-form row" data-id="${q.id}" novalidate><label class="sr-only" for="s-${q.id}">Score for ${esc(q.student)}</label>
            <input id="s-${q.id}" class="score" inputmode="decimal" value="${q.score == null ? '' : q.score}"><span class="muted">/ ${q.points}</span>
            <button type="submit" class="btn btn-small btn-ghost">Save</button></form></td>
          <td>${q.released ? 'Released' : q.score == null ? 'Not graded' : 'Graded'}</td></tr>`).join('');
    }

    const r = await F.api('/api/teach');
    if (!r.ok) return F.toast(r.data.error || 'Could not load your courses.', 'error');
    data = r.data;
    draw();

    $('#t-assignment').addEventListener('change', draw);
    $('#t-queue').addEventListener('submit', async (e) => {
      const form = e.target.closest('.grade-form');
      if (!form) return;
      const raw = form.querySelector('.score').value.trim();
      const score = parseInt(raw, 10);
      if (Number.isNaN(score)) return F.say($('#t-msg'), 'Enter a number.', 'error');
      const res = await F.api('/api/teach/grade', { submission: Number(form.dataset.id), score });
      if (!res.ok) return F.say($('#t-msg'), res.data.error || 'Could not save the score.', 'error');
      data = res.data;
      draw();
      F.say($('#t-msg'), `Saved ${score}.`, 'success');
    });
    $('#release').addEventListener('click', async () => {
      const res = await F.api('/api/teach/release', { assignment: Number($('#t-assignment').value) });
      if (!res.ok) return F.say($('#t-msg'), res.data.error || 'Could not release grades.', 'error');
      data = res.data;
      draw();
      F.say($('#t-msg'), 'Grades released to students.', 'success');
    });
  };
})();
