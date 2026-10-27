/* dust-and-scratches: specks re-drawn eight times a second from a hash of the time slot; scratches wander by noise. MIT, video-editor profile. */
HFX.define("dust-and-scratches", {
  setup: function (ctx, params) {
    ctx.canvas = ctx.q("canvas");
    ctx.g = ctx.canvas.getContext("2d");
  },
  update: function (s, ctx) {
    var g = ctx.g, w = ctx.canvas.width, h = ctx.canvas.height;
    g.clearRect(0, 0, w, h);
    if (!s.active) return;
    var scale = h / 180, slot = Math.floor(s.local * 8), n = Math.round(30 * s.amount);
    for (var i = 0; i < n; i++) {
      var k = slot * 101 + i;
      g.fillStyle = ctx.rand(k * 5 + 4) < 0.5 ? "rgba(20,15,10,0.55)" : "rgba(250,245,230,0.45)";
      g.beginPath();
      g.arc(ctx.rand(k * 5) * w, ctx.rand(k * 5 + 1) * h, (0.4 + 1.4 * ctx.rand(k * 5 + 2)) * scale, 0, Math.PI * 2);
      g.fill();
    }
    g.strokeStyle = "rgba(240,235,220,0.35)";
    g.lineWidth = 0.6 * scale;
    for (var j = 0; j < Math.round(s.scratches); j++) {
      var x = (ctx.rand(j * 7) * w + 3 * scale * HFX.noise1(ctx.seed + j, s.local * 2)) % w;
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x + 2 * scale * HFX.noise1(ctx.seed + 50 + j, s.local), h); g.stroke();
    }
  },
});
