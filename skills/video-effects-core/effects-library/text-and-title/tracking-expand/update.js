/* tracking-expand: letter-spacing eased across the window. MIT, video-editor profile. */
HFX.define("tracking-expand", {
  update: function (s, ctx) {
    var k = s.local >= 0 ? s.u : 0;
    var e = 1 - Math.pow(1 - k, 2);
    ctx.el.style.letterSpacing = (s.from + (s.to - s.from) * e).toFixed(4) + "em";
    ctx.el.style.opacity = (s.local >= 0) ? Math.min(1, s.local / 0.4).toFixed(4) : "0";
  },
});
