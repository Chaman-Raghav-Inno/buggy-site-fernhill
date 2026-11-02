(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;
  const TYPES = /\.(pdf|txt|docx|py)$/;
  const MAX = 2 * 1024 * 1024;

  F.pages.assignment = async function () {
    const id = Number(F.params.get('id'));
    let a;

    const words = (text) => (text.trim() ? text.trim().split(' ').length : 0);

    function countWords() {
      const n = words($('#a-text').value);
      $('#a-words').textContent = a.min_words ? `${F.plural(n, 'word')} (at least ${a.min_words})` : F.plural(n, 'word');
    }

    function draw() {
      document.title = `${a.title} · Fernhill Academy`;
      $('#a-course').innerHTML = `<a href="/course?id=${a.course}">Python Basics</a>`;
      $('#a-title').textContent = a.title;
      $('#a-brief').textContent = a.brief;
      $('#a-facts').innerHTML = [
        ['Due', F.dateTime(a.due)], ['Points', a.points], ['Minimum words', a.min_words || '—'],
      ].map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join('');
      const s = a.submission;
      if (!s) {
        $('#a-status').innerHTML = '<p class="pill">Not submitted yet</p>';
      } else {
        const late = s.days_late ? ` · ${F.plural(s.days_late, 'day')} late` : '';
        const grade = s.score == null ? '<p class="pill">Waiting for a grade</p>'
          : `<p class="pill pill-ok">Grade: ${s.score} / ${a.points}${s.days_late ? ` (${s.raw} before the late penalty)` : ''}</p>`;
        $('#a-status').innerHTML = `<p>Submitted ${F.dateTime(s.submitted)}${late}${s.file ? ` · <code>${esc(s.file)}</code>` : ''}</p>${grade}`;
        $('#a-form-title').textContent = 'Resubmit';
        if (s.text && !$('#a-text').value) $('#a-text').value = s.text;
      }
      countWords();
    }

    $('#a-text').addEventListener('input', () => { if (a) countWords(); });
    $('#a-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const msg = $('#a-msg');
      const file = $('#a-file').files[0];
      const text = $('#a-text').value;
      if (!file && !text.trim()) return F.say(msg, 'Attach a file or write your answer.', 'error');
      if (file && !TYPES.test(file.name)) return F.say(msg, 'Upload a PDF, TXT, DOCX or PY file.', 'error');
      if (file && file.size > MAX) return F.say(msg, 'Files can be at most 2 MB.', 'error');
      if (a.min_words && words(text) < a.min_words) return F.say(msg, `Write at least ${a.min_words} words.`, 'error');
      const r = await F.api(`/api/assignments/${id}/submit`, { text, file: file ? file.name : '', size: file ? file.size : 0 });
      if (!r.ok) return F.say(msg, r.data.error || 'Could not submit.', 'error');
      a = r.data;
      draw();
      $('#a-file').value = '';
      F.say(msg, 'Submitted. You can resubmit until your instructor grades it.', 'success');
    });

    const r = await F.api(`/api/assignments/${id}`);
    if (!r.ok) {
      $('#loading').textContent = r.data.error || 'We couldn\'t find that assignment.';
      return;
    }
    a = r.data;
    draw();
    $('#loading').hidden = true;
    $('#assignment').hidden = false;
  };
})();
