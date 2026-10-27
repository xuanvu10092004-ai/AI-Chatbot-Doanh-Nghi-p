(function () {
  'use strict';
  var body = document.body;
  if (!body || !body.classList.contains('auth-body')) return;

  var ambient = document.createElement('div');
  ambient.className = 'login-ambient';
  ambient.setAttribute('aria-hidden', 'true');
  ['orb orb-one', 'orb orb-two', 'ring ring-one', 'glow glow-one'].forEach(function (className) {
    var item = document.createElement('span');
    item.className = 'login-object ' + className;
    item.setAttribute('data-login-object', 'true');
    ambient.appendChild(item);
  });
body.prepend(ambient);

  var streams = [];
  var streamKinds = ['stream-a', 'stream-b', 'stream-c', 'stream-d', 'stream-a', 'stream-b'];
  var streamColors = ['red', 'white', 'silver'];
  streamKinds.forEach(function (kind, streamIndex) {
    var stream = document.createElement('div');
    stream.className = 'particle-stream ' + kind;
    stream.setAttribute('aria-hidden', 'true');
    stream.style.setProperty('--stream-duration', (15 + (streamIndex % 4) * 2.5) + 's');
    stream.style.setProperty('--stream-delay', (-streamIndex * 2.1) + 's');
    for (var dotIndex = 0; dotIndex < 22; dotIndex += 1) {
      var dot = document.createElement('span');
      dot.className = 'stream-dot ' + streamColors[(dotIndex + streamIndex) % streamColors.length];
      if (dotIndex % 7 === 0) dot.classList.add('trail');
      dot.style.setProperty('--dot-delay', (-((dotIndex * 0.62 + streamIndex * 0.35) % 14)).toFixed(2) + 's');
      dot.style.setProperty('--dot-scale', (0.62 + ((dotIndex * 13) % 55) / 100).toFixed(2));
      stream.appendChild(dot);
    }
    ambient.appendChild(stream);
    streams.push(stream);
  });

  var ribbons = [];
  for (var ribbonIndex = 0; ribbonIndex < 7; ribbonIndex += 1) {
    var ribbon = document.createElement('span');
    ribbon.className = 'light-ribbon light-ribbon-' + (ribbonIndex % 3);
    ribbon.setAttribute('aria-hidden', 'true');
    ribbon.style.left = (-18 + ribbonIndex * 15) + '%';
    ribbon.style.top = (12 + (ribbonIndex % 4) * 22) + '%';
    ribbon.style.setProperty('--ribbon-angle', (-18 + (ribbonIndex % 5) * 9) + 'deg');
    ribbon.style.setProperty('--ribbon-duration', (18 + (ribbonIndex % 4) * 3) + 's');
    ribbon.style.setProperty('--ribbon-delay', (-ribbonIndex * 2.4) + 's');
    ambient.appendChild(ribbon);
    ribbons.push(ribbon);
  }

  var card = document.querySelector('.auth-card');
  var inner = document.createElement('div');
  inner.className = 'login-inner-particles';
  inner.setAttribute('aria-hidden', 'true');
  if (card) card.appendChild(inner);
  var innerStreams = [];
  function updateInnerStreamPaths() {
    if (!card) return;
    var width = card.clientWidth;
    var height = card.clientHeight;
    innerStreams.forEach(function (stream, index) {
      var paths = index % 2 === 0
        ? [[-30, height * .22], [width * .22, height * .04], [width * .56, height * .32], [width + 30, height * .12]]
        : [[-30, height * .76], [width * .25, height * .52], [width * .58, height * .84], [width + 30, height * .62]];
      paths.forEach(function (point, pointIndex) {
        stream.style.setProperty('--inner-p' + pointIndex + '-x', point[0].toFixed(1) + 'px');
        stream.style.setProperty('--inner-p' + pointIndex + '-y', point[1].toFixed(1) + 'px');
      });
    });
  }
  if (card) {
    for (var innerStreamIndex = 0; innerStreamIndex < 3; innerStreamIndex += 1) {
      var innerStream = document.createElement('div');
      innerStream.className = 'inner-stream ' + (innerStreamIndex % 2 === 0 ? 'inner-stream-a' : 'inner-stream-b');
      innerStream.setAttribute('aria-hidden', 'true');
      innerStream.style.setProperty('--inner-duration', (10 + innerStreamIndex * 1.8) + 's');
      for (var innerDotIndex = 0; innerDotIndex < 13; innerDotIndex += 1) {
        var innerDot = document.createElement('span');
        innerDot.className = 'inner-stream-dot ' + (innerDotIndex % 3 === 0 ? 'red' : innerDotIndex % 3 === 1 ? 'white' : 'silver');
        if (innerDotIndex % 6 === 0) innerDot.classList.add('trail');
        innerDot.style.setProperty('--inner-delay', (-innerDotIndex * .52 - innerStreamIndex * 1.7).toFixed(2) + 's');
        innerStream.appendChild(innerDot);
      }
      inner.appendChild(innerStream);
      innerStreams.push(innerStream);
    }
    updateInnerStreamPaths();
    window.addEventListener('resize', updateInnerStreamPaths, { passive: true });
  }

  var particles = [];
  function addParticle(container, index, inside) {
    var particle = document.createElement('span');
    particle.className = inside ? 'light-particle light-particle-inner' : 'light-particle';
    particle.setAttribute('aria-hidden', 'true');
    var seed = (index * 37 + (inside ? 11 : 3)) % 100;
    var x = 4 + (seed * 0.91) % 92;
    var y = inside ? 8 + ((index * 29) % 80) : 8 + ((index * 47) % 82);
    var x1 = 35 + ((index * 17) % 105);
    var x2 = 80 + ((index * 23) % 160);
    var y1 = -45 + ((index * 31) % 90);
    var y2 = -25 + ((index * 19) % 100);
    particle.style.left = x.toFixed(2) + '%';
    particle.style.top = y.toFixed(2) + '%';
    particle.style.setProperty('--x1', x1.toFixed(1) + 'px');
    particle.style.setProperty('--x2', x2.toFixed(1) + 'px');
    particle.style.setProperty('--y1', y1.toFixed(1) + 'px');
    particle.style.setProperty('--y2', y2.toFixed(1) + 'px');
    particle.style.setProperty('--particle-duration', (inside ? 9 + (index % 5) * 1.4 : 11 + (index % 8) * 1.6) + 's');
    particle.style.setProperty('--particle-delay', (-((index * 1.7) % 14)).toFixed(2) + 's');
    particle.style.setProperty('--particle-depth', (inside ? 0.12 + (index % 3) * 0.04 : 0.2 + (index % 5) * 0.08).toFixed(2));
    if (index % 5 === 0) particle.classList.add('light-particle-trail');
    container.appendChild(particle);
    particles.push(particle);
  }

  for (var outerIndex = 0; outerIndex < 42; outerIndex += 1) addParticle(ambient, outerIndex, false);
  if (card) {
    for (var innerIndex = 0; innerIndex < 14; innerIndex += 1) addParticle(inner, innerIndex, true);
  }

  var objects = Array.prototype.slice.call(ambient.querySelectorAll('[data-login-object="true"]'));
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var pointerX = 0;
  var pointerY = 0;
  var frame = null;

  function render() {
    frame = null;
    if (innerStreams.length) {
      inner.style.setProperty('--inner-shift-x', (pointerX * 0.08).toFixed(2) + 'px');
      inner.style.setProperty('--inner-shift-y', (pointerY * 0.08).toFixed(2) + 'px');
    }
    if (reducedMotion.matches) return;
    objects.forEach(function (item, index) {
      if (item.classList.contains('is-dragging')) return;
      var depth = (index + 1) * 0.18;
      item.style.setProperty('--pointer-x', (pointerX * depth).toFixed(2) + 'px');
      item.style.setProperty('--pointer-y', (pointerY * depth).toFixed(2) + 'px');
    });
streams.forEach(function (stream, index) {
      var depth = 0.12 + (index % 4) * 0.045;
      stream.style.setProperty('--stream-shift-x', (pointerX * depth).toFixed(2) + 'px');
      stream.style.setProperty('--stream-shift-y', (pointerY * depth).toFixed(2) + 'px');
      stream.style.setProperty('--stream-tilt', (pointerX * (0.008 + index * 0.002)).toFixed(2) + 'deg');
    });
    ribbons.forEach(function (ribbon, index) {
      ribbon.style.setProperty('--ribbon-tilt', (pointerX * (0.025 + index * 0.004)).toFixed(2) + 'deg');
      ribbon.style.setProperty('--ribbon-py', (pointerY * (0.08 + index * 0.02)).toFixed(2) + 'px');
    });
    particles.forEach(function (particle) {
      var depth = parseFloat(particle.style.getPropertyValue('--particle-depth')) || 0.2;
      particle.style.setProperty('--particle-px', (pointerX * depth).toFixed(2) + 'px');
      particle.style.setProperty('--particle-py', (pointerY * depth).toFixed(2) + 'px');
    });
  }

  body.addEventListener('pointermove', function (event) {
    pointerX = (event.clientX / window.innerWidth - 0.5) * 34;
    pointerY = (event.clientY / window.innerHeight - 0.5) * 26;
    if (!frame) frame = window.requestAnimationFrame(render);
  }, { passive: true });
  body.addEventListener('pointerleave', function () {
    pointerX = 0;
    pointerY = 0;
    if (!frame) frame = window.requestAnimationFrame(render);
  });

  objects.forEach(function (item) {
    var startX = 0;
    var startY = 0;
    var originX = 0;
    var originY = 0;
    item.addEventListener('pointerdown', function (event) {
      if (reducedMotion.matches) return;
      event.preventDefault();
      item.classList.add('is-dragging');
      item.setPointerCapture(event.pointerId);
      startX = event.clientX;
      startY = event.clientY;
      originX = parseFloat(item.dataset.x || '0');
      originY = parseFloat(item.dataset.y || '0');
    });
    item.addEventListener('pointermove', function (event) {
      if (!item.classList.contains('is-dragging')) return;
      var x = originX + event.clientX - startX;
      var y = originY + event.clientY - startY;
      item.dataset.x = x;
      item.dataset.y = y;
      item.style.setProperty('--drag-x', x + 'px');
      item.style.setProperty('--drag-y', y + 'px');
    });
    item.addEventListener('pointerup', function (event) {
      if (!item.classList.contains('is-dragging')) return;
      item.classList.remove('is-dragging');
      item.releasePointerCapture(event.pointerId);
    });
  });
}());