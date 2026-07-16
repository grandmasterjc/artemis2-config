/* artemistracker.app — site logic
   Data comes from the same repo GitHub Pages serves:
   config.json (mission state), updates/manifest.json (articles),
   merch/manifest.json (gear). Space weather from NOAA SWPC. */

(function () {
  'use strict';

  // Site root: '/' on the custom domain, '/artemis2-config/' on
  // grandmasterjc.github.io project pages.
  var BASE = location.hostname.endsWith('github.io') ? '/artemis2-config/' : '/';
  window.SITE_BASE = BASE;

  var APP_STORE_URL = 'https://apps.apple.com/app/id6761183798';
  var PLAY_STORE_URL = 'https://play.google.com/store/apps/details?id=no.bitfactory.artemisii';

  // Fallbacks if config.json is unreachable; overwritten on load.
  var LAUNCH_MS = Date.parse('2026-04-01T22:35:12Z');
  var SPLASHDOWN_MS = Date.parse('2026-04-11T00:07:27Z');
  var A3_TARGET_MS = Date.parse('2027-06-30T00:00:00Z');
  var missionComplete = true;

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  // ── Tabs ─────────────────────────────────────────────────────────
  var TABS = ['mission', 'tracking', 'media', 'timeline', 'crew', 'missions', 'gear'];

  function showTab(id, push) {
    if (TABS.indexOf(id) < 0) id = 'mission';
    $$('main[data-screen]').forEach(function (m) {
      m.classList.toggle('visible', m.getAttribute('data-screen') === id);
    });
    $$('.site-nav a').forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('data-tab') === id);
    });
    if (push !== false) {
      var hash = id === 'mission' ? '' : '#' + id;
      if (('#' + id) !== location.hash && !(id === 'mission' && !location.hash)) {
        history.pushState(null, '', location.pathname + hash);
      }
    }
    window.scrollTo(0, 0);
  }

  function currentTabFromHash() {
    var h = (location.hash || '').replace('#', '');
    return TABS.indexOf(h) >= 0 ? h : 'mission';
  }

  // ── Clocks ───────────────────────────────────────────────────────
  function split(ms) {
    var s = Math.max(0, Math.floor(ms / 1000));
    var pad = function (n) { return String(Math.floor(n)).padStart(2, '0'); };
    return {
      days: String(Math.floor(s / 86400)).padStart(2, '0'),
      hrs: pad((s % 86400) / 3600),
      min: pad((s % 3600) / 60),
      sec: pad(s % 60)
    };
  }

  function tick() {
    var now = Date.now();
    // Mission elapsed time: frozen at splashdown once the mission is complete.
    var metEnd = missionComplete ? SPLASHDOWN_MS : now;
    var t2 = split(metEnd - LAUNCH_MS);
    ['days', 'hrs', 'min', 'sec'].forEach(function (k) {
      $$('[data-t2="' + k + '"]').forEach(function (n) { n.textContent = t2[k]; });
    });
    $$('[data-t2="short"]').forEach(function (n) {
      n.textContent = String(parseInt(t2.days, 10)) + 'd ' + t2.hrs + 'h';
    });

    var t3 = split(A3_TARGET_MS - now);
    $$('[data-t3="days"]').forEach(function (n) { n.textContent = String(parseInt(t3.days, 10)); });
    $$('[data-t3="full"]').forEach(function (n) {
      n.textContent = t3.days + ':' + t3.hrs + ':' + t3.min + ':' + t3.sec;
    });
  }

  // ── Data loads ───────────────────────────────────────────────────
  function loadJSON(path) {
    return fetch(BASE + path, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(path + ' -> HTTP ' + r.status);
      return r.json();
    });
  }

  function loadConfig() {
    return loadJSON('config.json').then(function (cfg) {
      var m = cfg.mission || {};
      if (m.launch && m.launch.date) LAUNCH_MS = Date.parse(m.launch.date);
      if (m.splashdown && m.splashdown.date) SPLASHDOWN_MS = Date.parse(m.splashdown.date);
      missionComplete = (m.state === 'complete');
      if (m.launch && m.launch.date) {
        var d = new Date(LAUNCH_MS);
        var caption = 'Launched ' + d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' }) +
          ' • ' + d.toISOString().slice(11, 16) + ' UTC · LC-39B, Kennedy Space Center';
        var cap = $('#met-caption');
        if (cap) cap.textContent = caption;
      }
    }).catch(function () { /* fallbacks already set */ });
  }

  function loadNews() {
    return loadJSON('updates/manifest.json').then(function (data) {
      var updates = (data.updates || []).filter(function (u) { return u && u.id; });
      var fmt = function (iso) {
        var d = new Date(iso);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
      };
      var makeCard = function (u) {
        var a = el('a', 'card clickable news-card');
        a.href = BASE + 'u/' + encodeURIComponent(u.id);
        a.style.position = 'relative';
        if (u.premium) a.appendChild(el('span', 'plus-badge', 'PLUS'));
        var img = el('img', 'thumb');
        img.loading = 'lazy';
        img.alt = '';
        if (u.hero_image) img.src = u.hero_image;
        var body = el('div', 'body');
        body.appendChild(el('div', 'title', u.title || u.id));
        body.appendChild(el('div', 'date', fmt(u.date)));
        a.appendChild(img);
        a.appendChild(body);
        return a;
      };
      var home = $('#news-home');
      if (home) {
        home.textContent = '';
        updates.slice(0, 3).forEach(function (u) { home.appendChild(makeCard(u)); });
      }
      var all = $('#news-all');
      if (all) {
        all.textContent = '';
        updates.forEach(function (u) { all.appendChild(makeCard(u)); });
      }
    }).catch(function () { /* leave empty */ });
  }

  function loadGear() {
    return loadJSON('merch/manifest.json').then(function (m) {
      var banner = $('#gear-banner-cta');
      if (banner && m.store_url) banner.href = m.banner && m.banner.cta_url ? m.banner.cta_url : m.store_url;
      var grid = $('#gear-grid');
      if (!grid) return;
      grid.textContent = '';
      (m.products || [])
        .filter(function (p) { return p.active !== false; })
        .sort(function (a, b) { return (a.order || 0) - (b.order || 0); })
        .forEach(function (p) {
          var a = el('a', 'card clickable gear-card');
          a.href = p.url || m.store_url || '#';
          a.target = '_blank';
          a.rel = 'noopener';
          if (p.badge) a.appendChild(el('span', 'badge', p.badge));
          var shot;
          if (p.image_url) {
            shot = el('div', 'shot');
            var img = el('img');
            img.loading = 'lazy';
            img.alt = p.title || '';
            img.src = p.image_url;
            shot.appendChild(img);
          } else {
            shot = el('div', 'shot empty', (p.title || 'ITEM').toUpperCase());
          }
          var body = el('div', 'body');
          body.appendChild(el('div', 't', p.title || ''));
          body.appendChild(el('div', 's', p.subtitle || ''));
          a.appendChild(shot);
          a.appendChild(body);
          grid.appendChild(a);
        });
    }).catch(function () { /* leave defaults */ });
  }

  // ── Space weather (NOAA SWPC, browser-side) ──────────────────────
  function loadSpaceWeather() {
    fetch('https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json')
      .then(function (r) { return r.json(); })
      .then(function (rows) {
        // rows[0] is a header row; last row is the latest estimated Kp.
        var last = rows[rows.length - 1];
        var kp = Math.round(parseFloat(last[1]));
        if (!isFinite(kp)) return;
        $$('[data-sw="kp"]').forEach(function (n) { n.textContent = String(kp); });
        var level = kp >= 6 ? 'SEVERE' : kp >= 4 ? 'ELEVATED RISK' : 'NOMINAL';
        var color = kp >= 6 ? 'var(--red)' : kp >= 4 ? 'var(--amber)' : 'var(--green)';
        var bg = kp >= 6 ? 'var(--red-dim)' : kp >= 4 ? 'var(--amber-dim)' : 'var(--green-dim)';
        var border = kp >= 6 ? 'var(--red-border)' : kp >= 4 ? 'var(--amber-border)' : 'var(--green-border)';
        $$('[data-sw="title"]').forEach(function (n) { n.textContent = 'SPACE WEATHER: ' + level; });
        $$('[data-sw="detail"]').forEach(function (n) { n.textContent = 'Kp index ' + kp + ' · NOAA SWPC, live'; });
        $$('.weather-strip, .weather-card').forEach(function (n) {
          n.style.background = bg;
          n.style.borderColor = border;
        });
        $$('[data-sw="accent"]').forEach(function (n) { n.style.color = color; });
      })
      .catch(function () { /* keep static defaults */ });
  }

  // ── Trajectory canvas (same design-space model as the apps) ──────
  // Cubic Béziers in a 1000×500 design space, scale-to-fit.
  var TRAJ = {
    earth: { x: 190, y: 215, r: 75 },
    moon: { x: 800, y: 300, r: 32 },
    segments: [
      { color: '#4CC9F0', dotted: true, curves: [
        [[205, 143], [80, 138], [72, 292], [195, 297]],
        [[195, 297], [330, 302], [335, 148], [205, 143]]
      ] },
      { color: '#4CC9F0', curves: [
        [[205, 143], [145, 141], [55, 95], [55, 215]],
        [[55, 215], [55, 290], [110, 350], [190, 350]],
        [[190, 350], [300, 350], [330, 180], [430, 175]]
      ] },
      { color: '#4CC9F0', label: 'OUTBOUND', labelAt: [565, 138], curves: [
        [[430, 175], [560, 168], [640, 225], [750, 240]]
      ] },
      { color: '#C9A0F0', label: 'FLYBY', labelAt: [925, 232], curves: [
        [[750, 240], [805, 248], [868, 255], [865, 315]],
        [[865, 315], [862, 345], [820, 362], [755, 350]]
      ] },
      { color: '#E05828', label: 'RETURN', labelAt: [645, 372], curves: [
        [[755, 350], [645, 335], [540, 290], [500, 170]],
        [[500, 170], [460, 50], [90, 90], [60, 230]]
      ] },
      { color: '#E05828', curves: [
        [[60, 230], [50, 280], [130, 338], [200, 335]],
        [[200, 335], [280, 330], [330, 280], [330, 215]],
        [[330, 215], [330, 160], [270, 130], [250, 152]]
      ] }
    ],
    markers: [
      { x: 205, y: 143, color: '#2CE771', label: 'LAUNCH', dy: -14 },
      { x: 242, y: 161, color: '#E05828', label: 'SPLASHDOWN', dy: 22 }
    ]
  };

  function drawTrajectory() {
    var canvas = $('#trajectory-canvas');
    if (!canvas) return;
    var wrap = canvas.parentElement;
    var dpr = window.devicePixelRatio || 1;
    var w = wrap.clientWidth, h = wrap.clientHeight;
    if (!w || !h) return;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    var ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    // Fit 1000×500 into w×h with padding.
    var pad = 18;
    var s = Math.min((w - pad * 2) / 1000, (h - pad * 2) / 500);
    var ox = (w - 1000 * s) / 2, oy = (h - 500 * s) / 2;
    var X = function (x) { return ox + x * s; };
    var Y = function (y) { return oy + y * s; };

    ctx.clearRect(0, 0, w, h);

    // Star field (deterministic).
    ctx.fillStyle = 'rgba(255,255,255,0.35)';
    var seed = 42;
    var rand = function () { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    for (var i = 0; i < 90; i++) {
      var sx = rand() * w, sy = rand() * h, sr = rand() * 1.1 + 0.2;
      ctx.globalAlpha = 0.15 + rand() * 0.5;
      ctx.beginPath(); ctx.arc(sx, sy, sr, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Earth
    var eg = ctx.createRadialGradient(X(TRAJ.earth.x) - 14 * s, Y(TRAJ.earth.y) - 14 * s, 6 * s, X(TRAJ.earth.x), Y(TRAJ.earth.y), TRAJ.earth.r * s);
    eg.addColorStop(0, '#3D7BD9'); eg.addColorStop(0.6, '#1D4E9E'); eg.addColorStop(1, '#0B2352');
    ctx.fillStyle = eg;
    ctx.beginPath(); ctx.arc(X(TRAJ.earth.x), Y(TRAJ.earth.y), TRAJ.earth.r * s, 0, Math.PI * 2); ctx.fill();
    // Moon
    var mg = ctx.createRadialGradient(X(TRAJ.moon.x) - 6 * s, Y(TRAJ.moon.y) - 6 * s, 3 * s, X(TRAJ.moon.x), Y(TRAJ.moon.y), TRAJ.moon.r * s);
    mg.addColorStop(0, '#C9CDD6'); mg.addColorStop(1, '#6E7480');
    ctx.fillStyle = mg;
    ctx.beginPath(); ctx.arc(X(TRAJ.moon.x), Y(TRAJ.moon.y), TRAJ.moon.r * s, 0, Math.PI * 2); ctx.fill();

    ctx.font = '600 ' + Math.max(9, 11 * s * 2) + 'px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(242,245,250,0.75)';
    ctx.fillText('EARTH', X(TRAJ.earth.x), Y(TRAJ.earth.y + TRAJ.earth.r + 26));
    ctx.fillText('MOON', X(TRAJ.moon.x), Y(TRAJ.moon.y + TRAJ.moon.r + 26));

    // Segments
    TRAJ.segments.forEach(function (seg) {
      ctx.strokeStyle = seg.color;
      ctx.lineWidth = Math.max(1.5, 2.2 * s * 2);
      ctx.lineCap = 'round';
      ctx.setLineDash(seg.dotted ? [3 * s * 2, 7 * s * 2] : []);
      ctx.globalAlpha = seg.dotted ? 0.7 : 0.95;
      ctx.beginPath();
      seg.curves.forEach(function (c, idx) {
        if (idx === 0) ctx.moveTo(X(c[0][0]), Y(c[0][1]));
        ctx.bezierCurveTo(X(c[1][0]), Y(c[1][1]), X(c[2][0]), Y(c[2][1]), X(c[3][0]), Y(c[3][1]));
      });
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
      if (seg.label && seg.labelAt) {
        ctx.fillStyle = seg.color;
        ctx.globalAlpha = 0.9;
        ctx.fillText(seg.label, X(seg.labelAt[0]), Y(seg.labelAt[1]));
        ctx.globalAlpha = 1;
      }
    });

    // Markers
    TRAJ.markers.forEach(function (mk) {
      ctx.fillStyle = mk.color;
      ctx.beginPath(); ctx.arc(X(mk.x), Y(mk.y), Math.max(3, 4.5 * s * 2), 0, Math.PI * 2); ctx.fill();
      ctx.fillText(mk.label, X(mk.x), Y(mk.y) + mk.dy * s * 1.4);
    });
  }

  // ── Init ─────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // Store links
    $$('[data-store="ios"]').forEach(function (a) { a.href = APP_STORE_URL; });
    $$('[data-store="android"]').forEach(function (a) { a.href = PLAY_STORE_URL; });

    // Nav
    $$('.site-nav a, [data-tab]').forEach(function (a) {
      var t = a.getAttribute('data-tab');
      if (!t) return;
      a.addEventListener('click', function (e) {
        e.preventDefault();
        showTab(t);
        if (t === 'tracking') requestAnimationFrame(drawTrajectory);
        var scrollTo = a.getAttribute('data-scroll');
        if (scrollTo) {
          requestAnimationFrame(function () {
            var target = document.getElementById(scrollTo);
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          });
        }
      });
    });
    window.addEventListener('popstate', function () { showTab(currentTabFromHash(), false); });
    window.addEventListener('hashchange', function () { showTab(currentTabFromHash(), false); });
    window.addEventListener('resize', drawTrajectory);

    showTab(currentTabFromHash(), false);

    loadConfig().then(tick);
    tick();
    setInterval(tick, 1000);
    loadNews();
    loadGear();
    loadSpaceWeather();
    requestAnimationFrame(drawTrajectory);
  });
})();
