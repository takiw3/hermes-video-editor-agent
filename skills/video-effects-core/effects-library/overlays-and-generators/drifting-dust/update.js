/* drifting-dust: soft motes drifting by slow noise. MIT, video-editor profile. */
HFX.define("drifting-dust", {
  setup: function (ctx, params) {
    ctx.canvas = ctx.q("canvas");
    ctx.g = ctx.canvas.getContext("2d");
  },
  update: function (s, ctx) {
    var g = ctx.g, w = ctx.canvas.width, h = ctx.canvas.height;
    g.clearRect(0, 0, w, h);
    if (!s.active) return;
    var scale = h / 180, n = Math.round(s.count);
    for (var i = 0; i < n; i++) {
      var x = ((ctx.rand(i * 4) + 0.02 * s.local + 0.03 * HFX.noise1(ctx.seed + i, s.local * 0.3)) % 1) * w;
      var y = ((ctx.rand(i * 4 + 1) - 0.015 * s.local + 0.03 * HFX.noise1(ctx.seed + 99 + i, s.local * 0.3) + 1) % 1) * h;
      var r = (0.8 + 2.2 * ctx.rand(i * 4 + 2)) * scale;
      var grad = g.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, "rgba(255,240,210," + (0.7 * s.glow).toFixed(3) + ")");
      grad.addColorStop(1, "rgba(255,240,210,0)");
      g.fillStyle = grad;
      g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    }
  },
});
