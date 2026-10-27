/* slide-up-reveal: per-word rise and fade, cubic ease-out. MIT, video-editor profile. */
HFX.define("slide-up-reveal", {
  setup: function (ctx, params) {
    ctx.wd = ctx.qa("word");
  },
  update: function (s, ctx) {
    for (var i = 0; i < ctx.wd.length; i++) {
      var k = Math.min(1, Math.max(0, (s.local - i * s.stagger) / 0.35));
      var e = 1 - Math.pow(1 - k, 3);
      ctx.wd[i].style.transform = "translateY(" + ((1 - e) * s.distance).toFixed(4) + "em)";
      ctx.wd[i].style.opacity = (s.local >= 0) ? e.toFixed(4) : "0";
    }
  },
});
