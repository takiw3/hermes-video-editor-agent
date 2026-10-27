/* kinetic-scale: scale from large to 1 with a quartic ease-out. MIT, video-editor profile. */
HFX.define("kinetic-scale", {
  update: function (s, ctx) {
    var k = Math.min(1, Math.max(0, s.local / s.time));
    var e = 1 - Math.pow(1 - k, 4);
    ctx.el.style.transform = "scale(" + ((s.local >= 0) ? s.from + (1 - s.from) * e : 1).toFixed(4) + ")";
    ctx.el.style.opacity = (s.local >= 0) && s.local >= 0 ? "1" : "0";
  },
});
