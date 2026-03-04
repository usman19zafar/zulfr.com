/* ══════════════════════════════════════════════
   ZULFR — Main Script
   Semantic Intelligence Platform
══════════════════════════════════════════════ */

/* ── Tab switching ───────────────────────────
   Shows the selected panel and marks its tab
   as active. Scrolls to top on every switch.
─────────────────────────────────────────────── */
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(function(t) {
    t.classList.toggle('active', t.dataset.tab === tab);
  });
  document.querySelectorAll('.panel').forEach(function(p) {
    p.classList.toggle('active', p.id === 'panel-' + tab);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── Paper expand / collapse ─────────────────
   Clicking a paper card expands its body.
   Clicking again, or clicking another card,
   collapses the previously opened one.
─────────────────────────────────────────────── */
function togglePaper(card) {
  var wasExpanded = card.classList.contains('expanded');
  document.querySelectorAll('.paper-card').forEach(function(c) {
    c.classList.remove('expanded');
  });
  if (!wasExpanded) {
    card.classList.add('expanded');
  }
}

/* ── Filter research papers ──────────────────
   Shows only cards whose data-type attribute
   matches the selected filter value.
─────────────────────────────────────────────── */
function filterPapers(type, btn) {
  document.querySelectorAll('.filter-btn').forEach(function(b) {
    b.classList.remove('active');
  });
  btn.classList.add('active');

  document.querySelectorAll('.paper-card').forEach(function(card) {
    card.style.display = (type === 'all' || card.dataset.type === type) ? '' : 'none';
  });
}

/* ── Model switcher ──────────────────────────
   Swaps the visible model detail panel and
   highlights the corresponding pill button.
─────────────────────────────────────────────── */
function switchModel(id) {
  document.querySelectorAll('.model-pill').forEach(function(p) {
    p.classList.toggle('active', p.dataset.model === id);
  });
  document.querySelectorAll('.model-detail').forEach(function(d) {
    d.classList.toggle('active', d.id === 'model-' + id);
  });
}
