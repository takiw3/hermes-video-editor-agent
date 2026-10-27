/* duotone: grey levels mapped between two chosen hues. MIT, video-editor profile. */
HFX.define("duotone", {
  setup: function (ctx, params) {
    ctx.funcs = Array.prototype.slice.call(ctx.q("t").children);
  },
  update: function (s, ctx) {
    function rgb(h, l) {
      var c = (1 - Math.abs(2 * l - 1)) * 0.85, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2, r = 0, g = 0, b = 0;
      if (h < 60) { r = c; g = x; } else if (h < 120) { r = x; g = c; } else if (h < 180) { g = c; b = x; }
      else if (h < 240) { g = x; b = c; } else if (h < 300) { r = x; b = c; } else { r = c; b = x; }
      return [r + m, g + m, b + m];
    }
    var lo = rgb(s.shadow_hue, 0.18), hi = rgb(s.highlight_hue, 0.82);
    for (var j = 0; j < 3; j++) ctx.funcs[j].setAttribute("tableValues", lo[j].toFixed(4) + " " + hi[j].toFixed(4));
    HFX.mix(ctx, s, s.mix);
  },
});
