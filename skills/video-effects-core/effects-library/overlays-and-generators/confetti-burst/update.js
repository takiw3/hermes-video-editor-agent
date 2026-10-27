/* confetti-burst: ballistic pieces: position is a closed-form function of time since the burst. MIT, video-editor profile. */
HFX.define("confetti-burst", {
  setup: function (ctx, params) {
    ctx.canvas = ctx.q("canvas");
    ctx.g = ctx.canvas.getContext("2d");
  },
  update: function (s, ctx) {
    var g = ctx.g, w = ctx.canvas.width, h = ctx.canvas.height;
    g.clearRect(0, 0, w, h);
    if (!s.active) return;
    var t = Math.max(0, s.local), colours = ["#FD5323", "#1D58F6", "#FAFAF7", "#F4C430", "#2A9D8F"];
    for (var i = 0; i < Math.round(s.count); i++) {
      var a = -Math.PI / 2 + (ctx.rand(i * 6) - 0.5) * 1.6, v = h * s.power * (0.9 + 1.1 * ctx.rand(i * 6 + 1));
      var x = s.cx * w + Math.cos(a) * v * t * 0.6, y = h * 0.95 + Math.sin(a) * v * t + 0.9 * h * t * t;
      var size = h * 0.018 * (0.6 + ctx.rand(i * 6 + 2)), spin = t * 10 * (ctx.rand(i * 6 + 3) - 0.5);
      g.save(); g.translate(x, y); g.rotate(spin);
      g.fillStyle = colours[Math.floor(ctx.rand(i * 6 + 4) * colours.length)];
      g.fillRect(-size / 2, -size / 4, size, size / 2);
      g.restore();
    }
  },
});
