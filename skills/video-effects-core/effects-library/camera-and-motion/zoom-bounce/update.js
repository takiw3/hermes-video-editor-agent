/* zoom-bounce: a damped spring on scale from the window start. MIT, video-editor profile. */
HFX.define("zoom-bounce", {
  update: function (s, ctx) {
    var t = Math.max(0, s.local), w = Math.PI * 2 * Math.round(s.bounces) / 1.2;
    var z = s.active ? 1 + s.amount * Math.exp(-3.2 * t) * Math.abs(Math.cos(w * t)) : 1;
    ctx.el.style.transform = "scale(" + z.toFixed(5) + ")";
  },
});
