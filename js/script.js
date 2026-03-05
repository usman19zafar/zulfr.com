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

/* ══════════════════════════════════════════════
   CONTACT FORM — Async submission
   POSTs JSON to the ZULFR backend on Render.
   Shows inline success / error feedback.
   No page reload. No third-party dependency.
══════════════════════════════════════════════ */

var BACKEND_URL = 'https://zulfr-backend.onrender.com/send';

/* Helper — show the feedback banner */
function showFeedback(type, message) {
  var banner  = document.getElementById('form-feedback');
  var icon    = document.getElementById('feedback-icon');
  var msg     = document.getElementById('feedback-msg');

  banner.classList.remove('success', 'error', 'visible');
  icon.textContent  = (type === 'success') ? '✓' : '✕';
  msg.textContent   = message;
  banner.classList.add(type, 'visible');
}

/* Helper — clear all field-level errors */
function clearFieldErrors() {
  document.querySelectorAll('.form-row input, .form-row textarea, .form-row select')
    .forEach(function(el) { el.classList.remove('invalid'); });
  document.querySelectorAll('.field-error')
    .forEach(function(el) { el.classList.remove('visible'); });
}

/* Helper — mark a single field invalid */
function markInvalid(inputId, errorId) {
  var input = document.getElementById(inputId);
  var error = document.getElementById(errorId);
  if (input)  input.classList.add('invalid');
  if (error)  error.classList.add('visible');
}

/* Helper — basic email format check */
function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

/* ── Client-side validation ─────────────────── */
function validateForm(data) {
  var valid = true;
  clearFieldErrors();

  if (!data.name || data.name.trim() === '') {
    markInvalid('f-name', 'err-name');
    valid = false;
  }
  if (!data.email || !isValidEmail(data.email)) {
    markInvalid('f-email', 'err-email');
    valid = false;
  }
  return valid;
}

/* ── Set button loading state ───────────────── */
function setLoading(isLoading) {
  var btn = document.getElementById('submit-btn');
  if (!btn) return;
  btn.disabled = isLoading;
  if (isLoading) {
    btn.classList.add('loading');
  } else {
    btn.classList.remove('loading');
  }
}

/* ── Reset the form after success ───────────── */
function resetForm() {
  var form = document.getElementById('inquiry-form');
  if (form) form.reset();
}

/* ── Main submit handler ────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
  var form = document.getElementById('inquiry-form');
  if (!form) return;

  form.addEventListener('submit', function(e) {
    e.preventDefault(); // prevent browser default POST

    /* Hide any previous feedback */
    var banner = document.getElementById('form-feedback');
    if (banner) banner.classList.remove('visible');

    /* Collect field values */
    var data = {
      name:    document.getElementById('f-name')    ? document.getElementById('f-name').value    : '',
      org:     document.getElementById('f-org')     ? document.getElementById('f-org').value     : '',
      email:   document.getElementById('f-email')   ? document.getElementById('f-email').value   : '',
      type:    document.getElementById('f-type')    ? document.getElementById('f-type').value    : '',
      message: document.getElementById('f-message') ? document.getElementById('f-message').value : ''
    };

    /* Validate before sending */
    if (!validateForm(data)) return;

    /* Show loading spinner on button */
    setLoading(true);

    /* ── Render free tier cold-start notice ──────
       If the backend takes more than 8s to respond,
       show an inline notice so the user knows it's
       waking up and doesn't abandon the form.
    ─────────────────────────────────────────────── */
    var coldStartTimer = setTimeout(function() {
      showFeedback('error', 'Server is waking up — this can take up to 30 seconds on first request. Please wait...');
      /* Keep spinner running — don't abort */
    }, 8000);

    /* ── AbortController — 65s timeout ──────────
       Render free tier cold starts take up to 60s.
       65s gives enough headroom before we give up.
    ─────────────────────────────────────────────── */
    var controller = new AbortController();
    var timeoutId  = setTimeout(function() { controller.abort(); }, 65000);

    /* Send JSON to backend */
    fetch(BACKEND_URL, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(data),
      signal:  controller.signal
    })
    .then(function(response) {
      clearTimeout(coldStartTimer);
      clearTimeout(timeoutId);

      if (response.ok) {
        /* Success — show confirmation, reset form */
        showFeedback('success', 'Message transmitted. We will respond within 2 business days.');
        resetForm();
        clearFieldErrors();
      } else {
        /* Server returned an error status */
        return response.json().then(function(body) {
          var detail = (body && body.error) ? body.error : 'Server error (' + response.status + '). Please try again.';
          showFeedback('error', detail);
        }).catch(function() {
          showFeedback('error', 'Server error (' + response.status + '). Please try again.');
        });
      }
    })
    .catch(function(err) {
      clearTimeout(coldStartTimer);
      clearTimeout(timeoutId);
      console.error('ZULFR form error:', err);

      if (err.name === 'AbortError') {
        /* Hit our 65s timeout — server didn't respond in time */
        showFeedback('error', 'Request timed out. The server may be starting up — please try again in 30 seconds.');
      } else {
        /* Genuine network failure or CORS block */
        showFeedback('error', 'Could not reach the server. Please check your connection and try again.');
      }
    })
    .finally(function() {
      setLoading(false);
    });
  });

  /* ── Clear field error on input ─────────────
     As soon as the user starts correcting a
     field, remove the red highlight immediately.
  ─────────────────────────────────────────────── */
  ['f-name', 'f-email'].forEach(function(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', function() {
      el.classList.remove('invalid');
      var errId = 'err-' + id.replace('f-', '');
      var errEl = document.getElementById(errId);
      if (errEl) errEl.classList.remove('visible');
    });
  });
});
