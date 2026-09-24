/* Ospace marketing site — small vanilla helpers. */
(function () {
  // Mobile nav
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', nav.classList.contains('open'));
    });
  }

  // Auto-hide flash messages
  document.querySelectorAll('.messages .alert').forEach(function (el) {
    setTimeout(function () { el.style.transition = 'opacity .5s'; el.style.opacity = '0'; setTimeout(function () { el.remove(); }, 500); }, 6000);
  });

  // Earnings calculator ($25 per ride: "$50 per minimum 2 rides")
  var calc = document.querySelector('[data-calc]');
  if (calc) {
    var PER_RIDE = 25;
    var rides = calc.querySelector('[name=rides]');
    var days = calc.querySelector('[name=days]');
    var fmt = function (n) { return '$' + Math.round(n).toLocaleString('en-US'); };
    var update = function () {
      var r = +rides.value, d = +days.value;
      calc.querySelector('[data-out=rides]').textContent = r + (r === 1 ? ' ride' : ' rides');
      calc.querySelector('[data-out=days]').textContent = d + (d === 1 ? ' day' : ' days');
      var daily = r * PER_RIDE;
      calc.querySelector('[data-out=daily]').textContent = fmt(daily);
      calc.querySelector('[data-out=weekly]').textContent = fmt(daily * d);
      calc.querySelector('[data-out=monthly]').textContent = fmt(daily * d * 4.33);
    };
    rides.addEventListener('input', update);
    days.addEventListener('input', update);
    update();
  }

  // Requirements self-check
  var check = document.querySelector('[data-selfcheck]');
  if (check) {
    var boxes = check.querySelectorAll('input[type=checkbox]');
    var verdict = check.querySelector('.check-verdict');
    var total = boxes.length;
    var refresh = function () {
      var n = 0;
      boxes.forEach(function (b) { b.closest('.check-item').classList.toggle('on', b.checked); if (b.checked) n++; });
      if (n === total) {
        verdict.className = 'check-verdict ok';
        verdict.innerHTML = 'You meet every requirement. <a href="' + check.dataset.applyUrl + '">Start your application &rarr;</a>';
      } else if (n === 0) {
        verdict.className = 'check-verdict';
        verdict.textContent = 'Tick each box that applies to you.';
      } else {
        verdict.className = 'check-verdict';
        verdict.textContent = (total - n) + ' to go. Not sure about one? Apply anyway and we will talk you through it.';
      }
    };
    boxes.forEach(function (b) { b.addEventListener('change', refresh); });
    refresh();
  }

  // Active nav link
  var path = location.pathname.replace(/\/$/, '') || '/';
  document.querySelectorAll('.nav a').forEach(function (a) {
    var href = a.getAttribute('href').replace(/\/$/, '') || '/';
    if (href === path || (href !== '/' && path.indexOf(href) === 0)) a.classList.add('active');
  });
})();
