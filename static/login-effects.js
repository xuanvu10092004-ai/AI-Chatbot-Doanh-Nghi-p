// Hiệu ứng ánh sáng và chuyển động nền công nghệ cho trang đăng nhập Honda AI
(function () {
  'use strict';
  var body = document.body;
  if (!body || !body.classList.contains('auth-body')) return;

  // Khung chứa hiệu ứng nền ambient
  var ambient = document.createElement('div');
  ambient.className = 'login-ambient';
  ambient.setAttribute('aria-hidden', 'true');

  ['orb orb-one', 'orb orb-two', 'glow glow-one'].forEach(function (className) {
    var item = document.createElement('span');
    item.className = 'login-object ' + className;
    item.setAttribute('data-login-object', 'true');
    ambient.appendChild(item);
  });
  body.prepend(ambient);

  // Các dải hạt sáng chuyển động nhẹ nhàng theo đường cong
  var streams = [];
  var streamKinds = ['stream-a', 'stream-b', 'stream-c'];
  var streamColors = ['red', 'white', 'silver'];
  streamKinds.forEach(function (kind, streamIndex) {
    var stream = document.createElement('div');
    stream.className = 'particle-stream ' + kind;
    stream.setAttribute('aria-hidden', 'true');
    stream.style.setProperty('--stream-duration', (16 + streamIndex * 3) + 's');
    stream.style.setProperty('--stream-delay', (-streamIndex * 2.5) + 's');
    for (var dotIndex = 0; dotIndex < 14; dotIndex += 1) {
      var dot = document.createElement('span');
      dot.className = 'stream-dot ' + streamColors[(dotIndex + streamIndex) % streamColors.length];
      if (dotIndex % 5 === 0) dot.classList.add('trail');
      dot.style.setProperty('--dot-delay', (-((dotIndex * 0.8 + streamIndex * 0.4) % 12)).toFixed(2) + 's');
      dot.style.setProperty('--dot-scale', (0.6 + ((dotIndex * 15) % 45) / 100).toFixed(2));
      stream.appendChild(dot);
    }
    ambient.appendChild(stream);
    streams.push(stream);
  });

  // Dải ruy-băng ánh sáng đỏ phía sau card
  var ribbons = [];
  for (var ribbonIndex = 0; ribbonIndex < 4; ribbonIndex += 1) {
    var ribbon = document.createElement('span');
    ribbon.className = 'light-ribbon light-ribbon-' + (ribbonIndex % 3);
    ribbon.setAttribute('aria-hidden', 'true');
    ribbon.style.left = (-10 + ribbonIndex * 22) + '%';
    ribbon.style.top = (15 + (ribbonIndex % 3) * 25) + '%';
    ribbon.style.setProperty('--ribbon-angle', (-15 + (ribbonIndex % 4) * 10) + 'deg');
    ribbon.style.setProperty('--ribbon-duration', (20 + ribbonIndex * 4) + 's');
    ribbon.style.setProperty('--ribbon-delay', (-ribbonIndex * 3) + 's');
    ambient.appendChild(ribbon);
    ribbons.push(ribbon);
  }

  // Hạt bụi sáng bay nhẹ ở background (không nằm trong card)
  var particles = [];
  function addParticle(container, index) {
    var particle = document.createElement('span');
    particle.className = 'light-particle';
    particle.setAttribute('aria-hidden', 'true');
    var seed = (index * 37 + 7) % 100;
    var x = 2 + (seed * 0.95) % 96;
    var y = 5 + ((index * 31) % 90);
    var x1 = 30 + ((index * 19) % 80);
    var x2 = 60 + ((index * 29) % 120);
    var y1 = -35 + ((index * 23) % 70);
    var y2 = -20 + ((index * 17) % 80);
    particle.style.left = x.toFixed(2) + '%';
    particle.style.top = y.toFixed(2) + '%';
    particle.style.setProperty('--x1', x1.toFixed(1) + 'px');
    particle.style.setProperty('--x2', x2.toFixed(1) + 'px');
    particle.style.setProperty('--y1', y1.toFixed(1) + 'px');
    particle.style.setProperty('--y2', y2.toFixed(1) + 'px');
    particle.style.setProperty('--particle-duration', (12 + (index % 6) * 2) + 's');
    particle.style.setProperty('--particle-delay', (-((index * 1.5) % 12)).toFixed(2) + 's');
    particle.style.setProperty('--particle-depth', (0.15 + (index % 4) * 0.08).toFixed(2));
    if (index % 6 === 0) particle.classList.add('light-particle-trail');
    container.appendChild(particle);
    particles.push(particle);
  }

  for (var outerIndex = 0; outerIndex < 24; outerIndex += 1) {
    addParticle(ambient, outerIndex);
  }

  // Hiệu ứng tương tác chuột (Parallax tinh tế)
  var objects = Array.prototype.slice.call(ambient.querySelectorAll('[data-login-object="true"]'));
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var pointerX = 0;
  var pointerY = 0;
  var frame = null;

  function render() {
    frame = null;
    if (reducedMotion.matches) return;
    objects.forEach(function (item, index) {
      var depth = (index + 1) * 0.12;
      item.style.setProperty('--pointer-x', (pointerX * depth).toFixed(2) + 'px');
      item.style.setProperty('--pointer-y', (pointerY * depth).toFixed(2) + 'px');
    });
    streams.forEach(function (stream, index) {
      var depth = 0.08 + (index % 3) * 0.03;
      stream.style.setProperty('--stream-shift-x', (pointerX * depth).toFixed(2) + 'px');
      stream.style.setProperty('--stream-shift-y', (pointerY * depth).toFixed(2) + 'px');
    });
    ribbons.forEach(function (ribbon, index) {
      ribbon.style.setProperty('--ribbon-tilt', (pointerX * (0.015 + index * 0.003)).toFixed(2) + 'deg');
      ribbon.style.setProperty('--ribbon-py', (pointerY * (0.05 + index * 0.015)).toFixed(2) + 'px');
    });
    particles.forEach(function (particle) {
      var depth = parseFloat(particle.style.getPropertyValue('--particle-depth')) || 0.15;
      particle.style.setProperty('--particle-px', (pointerX * depth).toFixed(2) + 'px');
      particle.style.setProperty('--particle-py', (pointerY * depth).toFixed(2) + 'px');
    });
  }

  body.addEventListener('pointermove', function (event) {
    pointerX = (event.clientX / window.innerWidth - 0.5) * 24;
    pointerY = (event.clientY / window.innerHeight - 0.5) * 18;
    if (!frame) frame = window.requestAnimationFrame(render);
  }, { passive: true });

  body.addEventListener('pointerleave', function () {
    pointerX = 0;
    pointerY = 0;
    if (!frame) frame = window.requestAnimationFrame(render);
  });

  // Toggle hiện/ẩn mật khẩu
  var pwdInput = document.getElementById('password');
  var toggleBtn = document.getElementById('togglePasswordBtn');
  if (pwdInput && toggleBtn) {
    var eyeShow = toggleBtn.querySelector('.eye-show');
    var eyeHide = toggleBtn.querySelector('.eye-hide');

    toggleBtn.addEventListener('click', function (e) {
      e.preventDefault();
      var isPassword = pwdInput.type === 'password';
      pwdInput.type = isPassword ? 'text' : 'password';
      if (eyeShow && eyeHide) {
        eyeShow.style.display = isPassword ? 'none' : 'block';
        eyeHide.style.display = isPassword ? 'block' : 'none';
      }
      toggleBtn.setAttribute('aria-label', isPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
      pwdInput.focus();
    });
  }
}());