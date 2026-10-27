/*
 * fx-runtime.js: effect instances for HyperFrames compositions.
 * Part of the Hermes video-editor profile. MIT License, Copyright 2026 Taki Wong / TakiGPT AI Inc.
 *
 * Every effect here is a pure function of composition time and its parameters.
 * Nothing reads a clock, Math.random, or state left over from an earlier frame,
 * so a frame seeked alone matches the same frame reached in sequence.
 *
 *   HFX.define(id, { setup(ctx, params), update(state, ctx) })
 *   HFX.run(timeline, instances)
 *
 * An instance is { iid, effect, target, start, duration, params, animate }.
 * `animate` maps a parameter key to keyframes [[seconds, value], ...] measured
 * from the composition start, with an optional ease name per key.
 */
(function () {
  "use strict";

  var defs = {};

  // Integer hash to [0, 1). Same inputs, same output, on every machine.
  function hash(seed, n) {
    var h = (seed | 0) ^ Math.imul(n | 0, 0x9e3779b1);
    h = Math.imul(h ^ (h >>> 16), 0x85ebca6b);
    h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  }

  function seedOf(text) {
    var h = 2166136261;
    for (var i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h | 0;
  }

  // Smooth 1-D value noise in [-1, 1].
  function noise1(seed, x) {
    var i = Math.floor(x);
    var f = x - i;
    var a = hash(seed, i) * 2 - 1;
    var b = hash(seed, i + 1) * 2 - 1;
    var s = f * f * (3 - 2 * f);
    return a + (b - a) * s;
  }

  function clamp(v, lo, hi) {
    return v < lo ? lo : v > hi ? hi : v;
  }

  function easeFn(name) {
    if (!name || name === "none" || name === "linear") return function (x) { return x; };
    if (typeof gsap !== "undefined" && gsap.parseEase) {
      var e = gsap.parseEase(name);
      if (e) return e;
    }
    return function (x) { return x; };
  }

  // Value of a keyframed parameter at composition time t.
  function keyed(keys, ease, t) {
    if (t <= keys[0][0]) return keys[0][1];
    for (var i = 1; i < keys.length; i++) {
      if (t <= keys[i][0]) {
        var a = keys[i - 1], b = keys[i];
        var span = b[0] - a[0];
        var x = span > 0 ? (t - a[0]) / span : 1;
        return a[1] + (b[1] - a[1]) * ease(x);
      }
    }
    return keys[keys.length - 1][1];
  }

  function rootElement() {
    return document.querySelector("[data-composition-id]");
  }

  function makeContext(spec) {
    var root = rootElement();
    var ctx = {
      iid: spec.iid,
      effect: spec.effect,
      seed: seedOf(spec.iid + ":" + spec.effect),
      root: root,
      w: Number(root.getAttribute("data-width")) || root.offsetWidth,
      h: Number(root.getAttribute("data-height")) || root.offsetHeight,
      start: spec.start,
      duration: spec.duration,
      vars: spec.vars || null,
      varsHost: spec.varsHost || null,
      el: spec.target ? document.querySelector(spec.target) : null,
      from: spec.from ? document.querySelector(spec.from) : null,
      to: spec.to ? document.querySelector(spec.to) : null,
      q: function (name) {
        return document.querySelector(".fx-" + spec.iid + "-" + name);
      },
      qa: function (name) {
        return Array.prototype.slice.call(document.querySelectorAll(".fx-" + spec.iid + "-" + name));
      },
      rand: function (n) {
        return hash(ctx.seed, n);
      },
      noise: function (channel, x) {
        return noise1(ctx.seed + channel * 7919, x);
      },
    };
    if (spec.target && !ctx.el) throw new Error("[fx] " + spec.iid + ": target not found: " + spec.target);
    return ctx;
  }

  var HFX = {
    version: "1.1.0",
    hash: hash,
    noise1: noise1,
    clamp: clamp,

    // Set several attributes on one element.
    attrs: function (el, values) {
      for (var k in values) el.setAttribute(k, String(values[k]));
    },

    // Wet/dry for an SVG filter that ends in
    // <feComposite operator="arithmetic" class="fx-<iid>-mix">: amount 1 is the
    // full effect, 0 is the untouched source. Outside its window an instance
    // passes the source through.
    mix: function (ctx, s, amount) {
      var node = ctx.q("mix");
      if (!node) return;
      var m = s.active ? clamp(amount, 0, 1) : 0;
      node.setAttribute("k2", String(m));
      node.setAttribute("k3", String(1 - m));
    },

    // Frame-height-relative pixels, so a value means the same at 180p and 1080p.
    px: function (ctx, percentOfHeight) {
      return (percentOfHeight / 100) * ctx.h;
    },

    define: function (id, def) {
      if (typeof def.update !== "function") throw new Error("[fx] " + id + ": update() is required");
      defs[id] = def;
    },

    defined: function (id) {
      return Object.prototype.hasOwnProperty.call(defs, id);
    },

    run: function (tl, instances) {
      if (!tl) throw new Error("[fx] no registered timeline; register window.__timelines first");
      var root = rootElement();
      var total = Number(root.getAttribute("data-duration"));
      if (!(total > 0)) throw new Error("[fx] the composition root needs data-duration");

      // Earlier instances first, so a later transition that shares a scene
      // with an earlier one has the last word once its own window starts.
      instances = instances.slice().sort(function (a, b) { return a.start - b.start; });
      var live = instances.map(function (spec) {
        var def = defs[spec.def || spec.effect];
        if (!def) throw new Error("[fx] unknown effect: " + spec.effect + " (is its script loaded?)");
        var ctx = makeContext(spec);
        var anim = [];
        var animate = spec.animate || {};
        Object.keys(animate).forEach(function (key) {
          var a = animate[key];
          var keys = a.keys.slice().sort(function (x, y) { return x[0] - y[0]; });
          anim.push({ key: key, keys: keys, ease: easeFn(a.ease) });
        });
        if (def.setup) def.setup(ctx, spec.params);
        return { spec: spec, def: def, ctx: ctx, anim: anim };
      });

      function tick(t) {
        for (var i = 0; i < live.length; i++) {
          var it = live[i];
          var s = it.spec;
          var state = {};
          for (var k in s.params) state[k] = s.params[k];
          for (var j = 0; j < it.anim.length; j++) {
            state[it.anim[j].key] = keyed(it.anim[j].keys, it.anim[j].ease, t);
          }
          var local = t - s.start;
          state.t = t;
          state.local = local;
          state.active = local >= 0 && local <= s.duration;
          state.u = s.duration > 0 ? clamp(local / s.duration, 0, 1) : 1;
          it.def.update(state, it.ctx);
        }
      }

      // One clock for every instance. HyperFrames seeks the registered timeline
      // for every frame it captures, and GSAP calls onUpdate with the seeked time.
      var clock = { t: 0 };
      tl.fromTo(
        clock,
        { t: 0 },
        {
          t: total,
          duration: total,
          ease: "none",
          immediateRender: false,
          onUpdate: function () {
            tick(clock.t);
          },
        },
        0
      );
      tick(0);
      return live.length;
    },
  };

  // Generic driver for effects written entirely in CSS: every numeric parameter
  // becomes --fx-<iid>-<key> on the target (or the composition root), with
  // --fx-<iid>-u (window progress 0..1) and --fx-<iid>-on (1 inside the window).
  // `vars` maps a parameter to a fixed property name, for HyperFrames' own
  // animatable properties such as --hf-color-grading-blur.
  HFX.define("css-vars", {
    setup: function (ctx) {
      ctx.host = ctx.el || ctx.root;
      // An overlay that carries its own data-vfx-chain is a sibling of the
      // target, so mapped vars go on the overlay itself.
      ctx.mapHost = (ctx.varsHost && ctx.q(ctx.varsHost)) || ctx.host;
    },
    update: function (s, ctx) {
      var style = ctx.host.style;
      var vars = ctx.vars || {};
      for (var k in s) {
        if (k === "t" || k === "local" || k === "active" || typeof s[k] !== "number") continue;
        style.setProperty("--fx-" + ctx.iid + "-" + k, String(s[k]));
        if (vars[k]) ctx.mapHost.style.setProperty(vars[k], String(s[k]));
      }
      style.setProperty("--fx-" + ctx.iid + "-on", s.active ? "1" : "0");
    },
  });

  window.HFX = HFX;
})();
