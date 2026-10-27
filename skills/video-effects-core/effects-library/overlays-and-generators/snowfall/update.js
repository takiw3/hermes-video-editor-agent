/* snowfall: flakes placed by a hash of their index, moved as a function of time. MIT, video-editor profile. */
HFX.define("snowfall", {
  setup: function (ctx, params) {
    ctx.canvas = ctx.q("canvas");
    ctx.g = ctx.canvas.getContext("2d");
  },
  update: function (s, ctx) {
    var g = ctx.g, w = ctx.canvas.width, h = ctx.canvas.height;
    g.clearRect(0, 0, w, h);
    if (!s.active) return;
    var scale = h / 180, n = Math.round(s.count);
    g.fillStyle = "#ffffff";
    for (var i = 0; i < n; i++) {
      var depth = 0.4 + 0.6 * ctx.rand(i * 4 + 3), r = s.size * scale * depth;
      var y = (ctx.rand(i * 4 + 1) * (h + 2 * r) + s.speed * h * depth * s.local) % (h + 2 * r) - r;
      var x = ctx.rand(i * 4) * w + 6 * scale * HFX.noise1(ctx.seed + i, s.local * 0.7);
      g.globalAlpha = 0.55 + 0.4 * depth;
      g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    }
    g.globalAlpha = 1;
  },
});
