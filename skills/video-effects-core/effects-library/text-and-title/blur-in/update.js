/* blur-in: per-letter blur and fade, staggered. MIT, video-editor profile. */
HFX.define("blur-in", {
  setup: function (ctx, params) {
    ctx.ch = ctx.qa("ch");
  },
  update: function (s, ctx) {
    for (var i = 0; i < ctx.ch.length; i++) {
      var k = Math.min(1, Math.max(0, (s.local - i * s.stagger) / 0.4));
      ctx.ch[i].style.filter = "blur(" + ((1 - k) * s.blur).toFixed(4) + "em)";
      ctx.ch[i].style.opacity = (s.local >= 0) ? k.toFixed(4) : "0";
    }
  },
});
