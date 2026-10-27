/* word-pop: per-word scale with a sine overshoot, staggered. MIT, video-editor profile. */
HFX.define("word-pop", {
  setup: function (ctx, params) {
    ctx.wd = ctx.qa("word");
  },
  update: function (s, ctx) {
    for (var i = 0; i < ctx.wd.length; i++) {
      var k = Math.min(1, Math.max(0, (s.local - i * s.stagger) / 0.25));
      var sc = k >= 1 ? 1 : k + s.overshoot * Math.sin(Math.PI * k);
      ctx.wd[i].style.transform = "scale(" + Math.max(0, sc).toFixed(4) + ")";
      ctx.wd[i].style.opacity = k > 0 ? "1" : "0";
    }
  },
});
