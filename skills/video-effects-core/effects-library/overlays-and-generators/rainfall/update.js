/* rainfall: streaks placed by hash and moved by time. MIT, video-editor profile. */
HFX.define("rainfall", {
  setup: function (ctx, params) {
    ctx.canvas = ctx.q("canvas");
    ctx.g = ctx.canvas.getContext("2d");
  },
  update: function (s, ctx) {
    var g = ctx.g, w = ctx.canvas.width, h = ctx.canvas.height;
    g.clearRect(0, 0, w, h);
    if (!s.active) return;
    var scale = h / 180, n = Math.round(s.count), len = 9 * scale;
    g.strokeStyle = "rgba(220,230,255,0.55)";
    g.lineWidth = Math.max(0.6, 0.7 * scale);
    for (var i = 0; i < n; i++) {
      var depth = 0.5 + 0.5 * ctx.rand(i * 3 + 2);
      var y = (ctx.rand(i * 3 + 1) * (h + len) + s.speed * h * depth * s.local) % (h + len) - len;
      var x = (ctx.rand(i * 3) * w * 1.4 - w * 0.2 + s.slant * y + w) % w;
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + s.slant * len * depth, y + len * depth); g.stroke();
    }
  },
});
