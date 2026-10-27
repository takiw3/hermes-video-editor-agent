/* handheld-drift: slow value noise on position. MIT, video-editor profile. */
HFX.define("handheld-drift", {
  update: function (s, ctx) {
    var a = s.active ? HFX.px(ctx, s.amplitude) : 0, f = s.speed * s.local;
    var x = a * ctx.noise(1, f), y = a * ctx.noise(2, f + 5.7);
    var z = s.active ? 1 + 2.2 * a / ctx.h : 1;
    ctx.el.style.transform = "translate(" + x.toFixed(3) + "px, " + y.toFixed(3) + "px) scale(" + z.toFixed(5) + ")";
  },
});
