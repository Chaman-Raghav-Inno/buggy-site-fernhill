(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;

  F.pages.course = async function () {
    const id = Number(F.params.get('id'));

    function draw(c) {
      document.title = `${c.title} · Fernhill Academy`;
      $('#c-topic').textContent = `${c.topic} · ${c.level}`;
      $('#c-title').textContent = c.title;
      $('#c-summary').textContent = c.summary;
      $('#c-meta').textContent = `★ ${c.rating.toFixed(1)} (${c.reviews} ratings) · ${F.plural(c.lessons, 'lesson')} · ${F.duration(c.minutes)}`;
      $('#c-instructor').textContent = `Taught by ${c.instructor}`;
      const full = c.enrolled >= c.seats;
      $('#c-seats').textContent = full ? `Course full (${c.enrolled} of ${c.seats} seats taken)` : `${c.seats - c.enrolled} of ${c.seats} seats left`;
      $('#c-seats').classList.toggle('full', full);
      if (c.prereq) {
        $('#c-prereq').hidden = false;
        $('#c-prereq').innerHTML = `Requires <a href="/course?id=${c.prereq.id}">${esc(c.prereq.title)}</a> to be completed first. ${c.prereq.met ? '✓ Done' : 'Not completed yet.'}`;
      }
      $('#enroll').hidden = c.enrolled_me;
      const first = c.modules[0].lessons[0].id;
      $('#continue').hidden = !c.enrolled_me;
      $('#continue').href = `/learn?course=${c.id}&lesson=${c.last || first}`;
      $('#c-progress').hidden = !c.enrolled_me;
      if (c.enrolled_me) {
        $('#c-pct').textContent = `${c.progress}%`;
        $('#c-bar').style.width = `${Math.min(100, c.progress)}%`;
      }
      const all = c.modules.flatMap((m) => m.lessons.map((l) => ({ ...l, module: m.title })));
      $('#c-count').textContent = `${F.plural(c.modules.length, 'module')} · ${F.plural(all.length, 'lesson')}`;
      let html = '';
      let module = '';
      for (let i = 1; i < all.length; i++) {
        const l = all[i];
        if (l.module !== module) {
          module = l.module;
          html += `<li class="module">${esc(module)}</li>`;
        }
        const done = c.done.includes(l.id);
        html += `<li class="lesson-item${done ? ' done' : ''}">${done ? '✓ ' : ''}${esc(l.title)} <span class="muted small">${l.minutes} min</span></li>`;
      }
      $('#syllabus').innerHTML = html;
      $('#work').hidden = !c.enrolled_me;
      $('#c-work').innerHTML = c.quizzes.map((q) => (q.open ? `<li><a href="/quiz?id=${q.id}">${esc(q.title)}</a></li>` : `<li>${esc(q.title)} <span class="muted small">closed</span></li>`)).join('') +
        c.assignments.map((a) => `<li><a href="/assignment?id=${a.id}">${esc(a.title)}</a> <span class="muted small">due ${F.date(a.due)}</span></li>`).join('');
      $('#c-grades').href = `/grades?course=${c.id}`;
      $('#c-forum').href = `/forum?course=${c.id}`;
      $('#c-cert').href = `/certificate?course=${c.id}`;
    }

    const r = await F.api(`/api/courses/${id}`);
    if (!r.ok) {
      $('#loading').textContent = r.data.error || 'We couldn\'t find that course.';
      return;
    }
    draw(r.data);
    $('#loading').hidden = true;
    $('#course').hidden = false;

    $('#enroll').addEventListener('click', async () => {
      if (F.role !== 'student') {
        if (!F.role) location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search);
        else F.say($('#c-msg'), 'Log in as a student to enroll.', 'error');
        return;
      }
      const res = await F.api(`/api/courses/${id}/enroll`, {});
      if (!res.ok) return F.say($('#c-msg'), res.data.error || 'Could not enroll you.', 'error');
      draw(res.data);
      F.say($('#c-msg'), 'You\'re enrolled. Enjoy the course!', 'success');
    });
  };
})();
