/* letter-drop: gravity-style fall with one small bounce, staggered. MIT, video-editor profile. */
HFX.define("letter-drop", {
  setup: function (ctx, params) {
    ctx.ch = ctx.qa("ch");
  },
  update: function (s, ctx) {
    for (var i = 0; i < ctx.ch.length; i++) {
      var k = Math.min(1, Math.max(0, (s.local - i * s.stagger) / 0.5));
      var b = k < 0.7 ? Math.pow(k / 0.7, 2) : 1 - 0.12 * Math.sin(Math.PI * (k - 0.7) / 0.3);
      ctx.ch[i].style.transform = "translateY(" + (-(1 - b) * s.height).toFixed(4) + "em)";
      ctx.ch[i].style.opacity = (s.local >= 0) && k > 0 ? "1" : "0";
    }
  },
});
