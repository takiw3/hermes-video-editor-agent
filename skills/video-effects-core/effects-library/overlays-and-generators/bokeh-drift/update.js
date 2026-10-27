/* bokeh-drift: soft-edged discs that drift slowly. MIT, video-editor profile. */
HFX.define("bokeh-drift", {
  setup: function (ctx, params) {
    ctx.canvas = ctx.q("canvas");
    ctx.g = ctx.canvas.getContext("2d");
  },
  update: function (s, ctx) {
    var g = ctx.g, w = ctx.canvas.width, h = ctx.canvas.height;
    g.clearRect(0, 0, w, h);
    if (!s.active) return;
    for (var i = 0; i < Math.round(s.count); i++) {
      var r = HFX.px(ctx, s.size) * (0.5 + ctx.rand(i * 5 + 2));
      var x = ((ctx.rand(i * 5) + 0.04 * s.local * (ctx.rand(i * 5 + 3) - 0.5)) % 1 + 1) % 1 * w;
      var y = ((ctx.rand(i * 5 + 1) - 0.03 * s.local) % 1 + 1) % 1 * h;
      var hue = 30 + 30 * ctx.rand(i * 5 + 4);
      var grad = g.createRadialGradient(x, y, r * 0.6, x, y, r);
      grad.addColorStop(0, "hsla(" + hue + ",90%,75%," + s.opacity.toFixed(3) + ")");
      grad.addColorStop(1, "hsla(" + hue + ",90%,75%,0)");
      g.fillStyle = grad;
      g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    }
  },
});
