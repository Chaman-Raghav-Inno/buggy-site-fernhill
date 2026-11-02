(function () {
  'use strict';

  const F = window.Fernhill;
  const { $ } = F;
  const PER_PAGE = 5;

  F.pages.catalog = async function () {
    let pages = 0;
    let total = 0;
    let shown = 0;

    function filters() {
      const q = new URLSearchParams();
      if ($('#q').value.trim()) q.set('q', $('#q').value.trim());
      if ($('#topic').value) q.set('topic', $('#topic').value);
      if ($('#level').value) q.set('level', $('#level').value);
      q.set('sort', $('#sort').value);
      return q;
    }

    async function first() {
      const r = await F.api('/api/courses?' + filters().toString());
      if (!r.ok) return F.toast(r.data.error || 'Could not load courses.', 'error');
      pages = 1;
      total = r.data.total;
      shown = r.data.courses.length;
      $('#courses').innerHTML = r.data.courses.map(F.card).join('');
      $('#count').textContent = total ? `${F.plural(total, 'course')}` : 'No courses match. Try another search.';
      $('#more').hidden = shown >= total;
    }

    async function more() {
      const q = new URLSearchParams({ sort: $('#sort').value, offset: pages * PER_PAGE });
      const r = await F.api('/api/courses?' + q.toString());
      if (!r.ok) return F.toast(r.data.error || 'Could not load more courses.', 'error');
      pages += 1;
      shown += r.data.courses.length;
      $('#courses').insertAdjacentHTML('beforeend', r.data.courses.map(F.card).join(''));
      $('#more').hidden = shown >= total || r.data.courses.length === 0;
    }

    let timer;
    $('#q').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(first, 250); });
    ['#topic', '#level', '#sort'].forEach((s) => $(s).addEventListener('change', first));
    $('#more').addEventListener('click', more);
    await first();
  };
})();
