(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;

  F.pages.grades = async function () {
    const id = Number(F.params.get('course'));
    const r = await F.api(`/api/grades/${id}`);
    if (!r.ok) return F.toast(r.data.error || 'Could not load your grades.', 'error');
    const g = r.data;
    $('#g-back').href = `/course?id=${id}`;
    $('#g-title').textContent = `Grades: ${g.course.title}`;
    $('#g-rows').innerHTML = g.items.length
      ? g.items.map((i) => `<tr${i.dropped ? ' class="dropped"' : ''}><td>${esc(i.title)}${i.dropped ? ' <span class="pill">Dropped</span>' : ''}</td>
          <td>${esc(i.status)}</td><td class="num">${i.pct == null ? '—' : `${Math.round(i.pct)}%`}</td></tr>`).join('')
      : '<tr><td colspan="3" class="muted">Nothing graded in this course.</td></tr>';
    $('#g-overall').textContent = g.overall == null ? 'No grade yet' : `${g.overall}%`;
  };
})();
