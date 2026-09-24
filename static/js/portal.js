/* Ospace driver portal — signature pad, upload niceties. No dependencies. */
(function () {
  // Signature pad ------------------------------------------------------------
  var pad = document.querySelector('.sig-pad');
  if (pad) {
    var canvas = pad.querySelector('canvas');
    var hidden = document.querySelector('input[name=signature]');
    var clearBtn = pad.querySelector('.sig-clear');
    var ctx = canvas.getContext('2d');
    var drawing = false, hasInk = false, last = null;

    function resize() {
      var ratio = Math.max(window.devicePixelRatio || 1, 1);
      var data = hasInk ? canvas.toDataURL() : null;
      canvas.width = canvas.offsetWidth * ratio;
      canvas.height = canvas.offsetHeight * ratio;
      ctx.scale(ratio, ratio);
      ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#1b1040';
      if (data) { var img = new Image(); img.onload = function () { ctx.drawImage(img, 0, 0, canvas.offsetWidth, canvas.offsetHeight); }; img.src = data; }
    }
    function pos(e) {
      var r = canvas.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    }
    function start(e) { drawing = true; last = pos(e); canvas.setPointerCapture(e.pointerId); e.preventDefault(); }
    function move(e) {
      if (!drawing) return;
      var p = pos(e);
      ctx.beginPath(); ctx.moveTo(last.x, last.y); ctx.lineTo(p.x, p.y); ctx.stroke();
      last = p; hasInk = true; pad.classList.add('has-ink');
      e.preventDefault();
    }
    function end() { if (drawing) { drawing = false; sync(); } }
    function sync() { hidden.value = hasInk ? canvas.toDataURL('image/png') : ''; }
    function clear() { ctx.clearRect(0, 0, canvas.width, canvas.height); hasInk = false; pad.classList.remove('has-ink'); sync(); }

    canvas.addEventListener('pointerdown', start);
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', end);
    canvas.addEventListener('pointercancel', end);
    canvas.addEventListener('pointerleave', end);
    if (clearBtn) clearBtn.addEventListener('click', function (e) { e.preventDefault(); clear(); });
    window.addEventListener('resize', resize);
    resize();

    var form = pad.closest('form');
    var submit = form.querySelector('[type=submit]');
    var scrollBox = document.querySelector('.agreement-doc');
    var scrolled = !scrollBox || scrollBox.scrollHeight <= scrollBox.clientHeight + 4;
    if (scrollBox && !scrolled) {
      scrollBox.addEventListener('scroll', function () {
        if (scrollBox.scrollTop + scrollBox.clientHeight >= scrollBox.scrollHeight - 12) { scrolled = true; gate(); }
      });
    }
    function gate() {
      var ok = scrolled && hasInk && form.querySelector('[name=typed_name]').value.trim().length > 2 && form.querySelector('[name=consent]').checked;
      submit.disabled = !ok;
      var g = document.querySelector('[data-scroll-hint]');
      if (g) g.style.display = scrolled ? 'none' : '';
    }
    form.addEventListener('input', gate);
    canvas.addEventListener('pointerup', gate);
    gate();
    form.addEventListener('submit', function (e) { sync(); if (!hidden.value) { e.preventDefault(); alert('Please draw your signature.'); } });
  }

  // Show chosen file name + auto-submit when a file is picked ----------------
  document.querySelectorAll('.upload-form input[type=file]').forEach(function (input) {
    input.addEventListener('change', function () {
      var form = input.closest('form');
      var needsDate = form.querySelector('input[type=date]');
      if (!needsDate || needsDate.value) form.submit();
      else { form.querySelector('[type=submit]').style.display = ''; needsDate.focus(); }
    });
  });

  // Auto-hide flash messages
  document.querySelectorAll('.messages .alert').forEach(function (el) {
    setTimeout(function () { el.style.transition = 'opacity .5s'; el.style.opacity = '0'; setTimeout(function () { el.remove(); }, 500); }, 7000);
  });
})();
