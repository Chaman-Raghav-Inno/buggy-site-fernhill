(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, esc } = F;

  F.pages.learn = async function () {
    const courseId = Number(F.params.get('course'));
    let lessonId = Number(F.params.get('lesson'));
    let data;
    let saveTimer;

    function place() {
      const mods = data.course.modules;
      for (let mi = 0; mi < mods.length; mi++) {
        const li = mods[mi].lessons.findIndex((l) => l.id === lessonId);
        if (li >= 0) return { mi, li };
      }
      return { mi: 0, li: 0 };
    }

    function neighbour(step) {
      const mods = data.course.modules;
      const { mi, li } = place();
      const here = mods[mi].lessons;
      if (step > 0) {
        if (li + 1 < here.length) return here[li + 1].id;
        return mi + 1 < mods.length ? mods[mi + 1].lessons[1].id : null;
      }
      if (li > 0) return here[li - 1].id;
      return mi > 0 ? mods[mi - 1].lessons[mods[mi - 1].lessons.length - 1].id : null;
    }

    function draw() {
      const l = data.lesson;
      const { mi } = place();
      document.title = `${l.title} · Fernhill Academy`;
      $('#back-course').href = `/course?id=${data.course.id}`;
      $('#l-course').textContent = data.course.title;
      $('#l-bar').style.width = `${Math.min(100, data.progress)}%`;
      $('#l-pct').textContent = `${data.progress}% complete`;
      $('#l-module').textContent = `Module ${mi + 1}: ${data.course.modules[mi].title}`;
      $('#l-title').textContent = l.title;
      $('#l-minutes').textContent = `${l.minutes} minutes`;
      $('#l-body').innerHTML = `<p>${esc(l.body)}</p>`;
      $('#l-done').checked = data.done.includes(l.id);
      $('#notes').value = data.notes;
      $('#notes-state').textContent = '';
      $('#outline').innerHTML = data.course.modules.map((m, i) => `<p class="outline-module">${i + 1}. ${esc(m.title)}</p><ol>${m.lessons.map((x) =>
        `<li><a href="/learn?course=${courseId}&amp;lesson=${x.id}" data-id="${x.id}"${x.id === l.id ? ' aria-current="page"' : ''}>${data.done.includes(x.id) ? '✓ ' : ''}${esc(x.title)}</a></li>`).join('')}</ol>`).join('');
      $('#prev').disabled = !neighbour(-1);
      $('#next').disabled = !neighbour(1);
    }

    async function open(id) {
      const r = await F.api(`/api/lessons/${id}`);
      if (!r.ok) {
        $('#loading').hidden = false;
        $('#loading').textContent = r.data.error || 'We couldn\'t open that lesson.';
        $('#player').hidden = true;
        return;
      }
      lessonId = id;
      data = r.data;
      history.replaceState(null, '', `/learn?course=${courseId}&lesson=${id}`);
      draw();
      $('#loading').hidden = true;
      $('#player').hidden = false;
    }

    async function go(step) {
      const id = neighbour(step);
      if (!id) return;
      if (step > 0) await F.api('/api/progress', { lesson: lessonId, done: true });
      open(id);
    }

    $('#prev').addEventListener('click', () => go(-1));
    $('#next').addEventListener('click', () => go(1));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    });
    $('#outline').addEventListener('click', (e) => {
      const a = e.target.closest('a[data-id]');
      if (!a) return;
      e.preventDefault();
      open(Number(a.dataset.id));
    });
    $('#l-done').addEventListener('change', async (e) => {
      const r = await F.api('/api/progress', { lesson: lessonId, done: e.target.checked });
      if (!r.ok) return F.toast(r.data.error || 'Could not save your progress.', 'error');
      data.done = r.data.done;
      data.progress = r.data.progress;
      draw();
    });
    $('#notes').addEventListener('input', () => {
      $('#notes-state').textContent = 'Saving…';
      clearTimeout(saveTimer);
      const id = lessonId;
      saveTimer = setTimeout(async () => {
        const text = $('#notes').value;
        const r = await F.api('/api/notes', { lesson: id, text });
        if (r.ok && id === lessonId) {
          data.notes = text;
          $('#notes-state').textContent = 'Saved.';
        }
      }, 1000);
    });

    await open(lessonId);
  };
})();
