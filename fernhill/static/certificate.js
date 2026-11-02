(function () {
  'use strict';

  const F = window.Fernhill;
  const { $ } = F;

  F.pages.certificate = async function () {
    const id = Number(F.params.get('course'));
    const r = await F.api(`/api/certificates/${id}`);
    if (!r.ok) {
      $('#loading').textContent = r.data.error || 'We couldn\'t find that course.';
      return;
    }
    const c = r.data;
    $('#loading').hidden = true;
    $('#cert-wrap').hidden = false;
    if (!c.eligible) {
      $('#not-yet').hidden = false;
      $('#not-yet').innerHTML = `<h1>Not quite yet</h1><p>You've completed ${c.progress}% of <strong>${F.esc(c.course)}</strong>.
        Finish every lesson with a grade of 70% or more to get your certificate.</p><p><a class="btn" href="/course?id=${id}">Back to the course</a></p>`;
      return;
    }
    $('#cert').hidden = false;
    $('#cert-name').textContent = c.name;
    $('#cert-course').textContent = c.course;
    $('#cert-date').textContent = `Completed ${F.date(c.date)}`;
  };
})();
