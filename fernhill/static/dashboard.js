(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;

  F.pages.dashboard = async function () {
    const r = await F.api('/api/dashboard');
    if (!r.ok) return F.toast(r.data.error || 'Could not load your courses.', 'error');
    $('#mine').innerHTML = r.data.courses.map((c) => `<article class="card course-card">
        <h3><a href="/course?id=${c.id}">${esc(c.title)}</a></h3>
        <div class="bar"><span style="width: ${Math.min(100, c.progress)}%"></span></div>
        <p class="meta"><span>${c.progress}% complete</span><span>${c.grade == null ? 'No grade yet' : `Grade ${c.grade}%`}</span></p>
        <p class="actions"><a class="btn btn-small" href="/learn?course=${c.id}&amp;lesson=${c.first}">Continue where you left off</a>
          <a href="/grades?course=${c.id}">Grades</a> <a href="/certificate?course=${c.id}">Certificate</a></p>
      </article>`).join('') || '<p class="muted">You haven\'t enrolled in anything yet. <a href="/">Browse courses</a></p>';
    $('#due').innerHTML = r.data.due.map((a) => `<li><a href="/assignment?id=${a.id}">${esc(a.title)}</a>
        <span class="muted small">due ${F.dateTime(a.due)}${a.submitted ? ' · submitted' : ''}</span></li>`).join('') || '<li class="muted">Nothing due.</li>';
  };
})();
