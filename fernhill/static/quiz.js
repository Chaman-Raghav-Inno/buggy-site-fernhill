(function () {
  'use strict';

  const F = window.Fernhill;
  const { $, $$, esc } = F;

  F.pages.quiz = async function () {
    const id = Number(F.params.get('id'));
    const md = (s) => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
    const r = await F.api(`/api/quizzes/${id}`);
    if (!r.ok) {
      $('#loading').textContent = r.data.error || 'We couldn\'t find that quiz.';
      return;
    }
    const quiz = r.data;
    const n = quiz.questions.length;
    let attempt = null;
    let current = 0;
    let answers = [];
    let flags = new Set();
    let deadline = 0;
    let ticker;

    document.title = `${quiz.title} · Fernhill Academy`;
    $('#q-title').textContent = quiz.title;
    $('#q-rules').innerHTML = [
      `${F.plural(n, 'question')}`,
      `${quiz.minutes} minutes once you start`,
      `${quiz.max_attempts} attempts; your best attempt counts`,
    ].map((x) => `<li>${x}</li>`).join('');
    $('#q-history').innerHTML = quiz.attempts.map((a, i) => `<li>Attempt ${i + 1}: ${a.score} / ${a.total}</li>`).join('');
    $('#start').hidden = quiz.used > quiz.max_attempts;
    if (quiz.used > quiz.max_attempts) F.say($('#q-msg'), 'You\'ve used all your attempts.', 'error');
    $('#loading').hidden = true;
    $('#intro').hidden = false;

    function answered(i) {
      const a = answers[i];
      return Array.isArray(a) ? a.length > 0 : a !== undefined && a !== '';
    }

    function drawNav() {
      $('#qnav').innerHTML = quiz.questions.map((_, i) => `<button type="button" class="qbtn${i === current ? ' current' : ''}${answered(i) ? ' answered' : ''}${flags.has(i) ? ' flagged' : ''}" data-i="${i}" aria-label="Question ${i + 1}${flags.has(i) ? ', flagged' : ''}">${i + 1}${flags.has(i) ? '⚑' : ''}</button>`).join('');
      $('#q-progress').textContent = `Question ${current + 1} of ${n}`;
      $('#flag').setAttribute('aria-pressed', String(flags.has(current)));
      $('#q-prev').disabled = current === 0;
      $('#q-next').hidden = current === n - 1;
    }

    function drawQuestion() {
      const q = quiz.questions[current];
      const a = answers[current];
      let input = '';
      if (q.type === 'single' || q.type === 'multi') {
        const kind = q.type === 'single' ? 'radio' : 'checkbox';
        input = q.options.map((o, i) => `<label class="check option"><input type="${kind}" name="opt" value="${i}"${Array.isArray(a) && a.includes(i) ? ' checked' : ''}> <code>${esc(o)}</code></label>`).join('');
      } else {
        input = `<div class="field"><label for="ans">Your answer</label><input id="ans" ${q.type === 'number' ? 'inputmode="decimal"' : ''} autocomplete="off" value="${esc(a == null ? '' : a)}"></div>`;
      }
      $('#question').innerHTML = `<fieldset><legend>${current + 1}. ${md(q.text)}</legend>${input}</fieldset>`;
      drawNav();
    }

    function collect() {
      const q = quiz.questions[current];
      if (q.type === 'single' || q.type === 'multi') {
        answers[current] = $$('#question input:checked').map((x) => Number(x.value));
      } else {
        answers[current] = $('#ans').value;
      }
    }

    function goTo(i) {
      collect();
      current = i;
      drawQuestion();
    }

    function tick() {
      const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      $('#timer').textContent = `⏱ ${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')} left`;
      if (left === 0) {
        clearInterval(ticker);
        finish();
      }
    }

    $('#start').addEventListener('click', async () => {
      const s = await F.api(`/api/quizzes/${id}/start`, {});
      if (!s.ok) return F.say($('#q-msg'), s.data.error || 'Could not start the quiz.', 'error');
      attempt = s.data.attempt;
      answers = [];
      flags = new Set();
      current = 0;
      deadline = Date.now() + s.data.minutes * 60000;
      $('#intro').hidden = true;
      $('#taking').hidden = false;
      drawQuestion();
      tick();
      ticker = setInterval(tick, 1000);
    });

    $('#qnav').addEventListener('click', (e) => {
      const b = e.target.closest('.qbtn');
      if (!b) return;
      flags = new Set();
      goTo(Number(b.dataset.i));
    });
    $('#q-next').addEventListener('click', () => goTo(current + 1));
    $('#q-prev').addEventListener('click', () => goTo(current - 1));
    $('#flag').addEventListener('click', () => {
      if (flags.has(current)) flags.delete(current);
      else flags.add(current);
      drawNav();
    });
    $('#question').addEventListener('change', () => { collect(); drawNav(); });

    const confirm = $('#confirm');
    $$('button', confirm).forEach((b) => b.addEventListener('click', () => confirm.close(b.dataset.value)));
    confirm.addEventListener('close', () => { if (confirm.returnValue === 'submit') finish(); });
    $('#submit').addEventListener('click', () => {
      collect();
      const missing = answers.filter((a) => a === '' || (Array.isArray(a) && a.length === 0)).length;
      $('#confirm-text').textContent = missing
        ? `You have ${F.plural(missing, 'unanswered question')}. You can't change your answers after submitting.`
        : 'You have answered every question. You can\'t change your answers after submitting.';
      confirm.returnValue = '';
      confirm.showModal();
    });

    async function finish() {
      clearInterval(ticker);
      collect();
      const res = await F.api(`/api/quizzes/${id}/submit`, { attempt, answers });
      if (!res.ok) return F.toast(res.data.error || 'Could not submit the quiz.', 'error');
      const { score, total, review } = res.data;
      const pct = Math.floor((100 * score) / total);
      const show = (q, v) => {
        if (v == null || v === '' || (Array.isArray(v) && !v.length)) return '<em>No answer</em>';
        return Array.isArray(v) ? v.map((i) => `<code>${esc(q.options[i])}</code>`).join(', ') : `<code>${esc(v)}</code>`;
      };
      $('#taking').hidden = true;
      $('#result').hidden = false;
      $('#result').innerHTML = `<h1>You scored ${score} / ${total} (${pct}%)</h1>
        <p><a href="/grades?course=${quiz.course}">See your grades</a> · <a href="/quiz?id=${id}">Back to the quiz</a></p>
        <ol class="review">${review.map((x, i) => {
          const q = quiz.questions[i];
          const correct = q.type === 'single' && !x.ok ? x.given : x.answer;
          return `<li class="${x.ok ? 'ok' : 'wrong'}"><p>${md(q.text)}</p>
            <p>Your answer: ${show(q, x.given)} ${x.ok ? '✓' : '✗'}</p>
            ${x.ok ? '' : `<p>Correct answer: ${show(q, correct)}</p>`}</li>`;
        }).join('')}</ol>`;
    }
  };
})();
