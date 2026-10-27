/* camera-shake: value noise of composition time on x, y and rotation, with a scale that hides the edges. MIT, video-editor profile. */
HFX.define("camera-shake", {
  update: function (s, ctx) {
    var a = s.active ? HFX.px(ctx, s.amplitude) : 0, f = s.frequency * s.local;
    var x = a * ctx.noise(1, f), y = a * ctx.noise(2, f + 11.3), r = s.active ? s.rotation * ctx.noise(3, f * 0.7 + 3.1) : 0;
    var z = s.active ? 1 + 2.2 * a / ctx.h + 0.02 * s.rotation : 1;
    ctx.el.style.transform = "translate(" + x.toFixed(3) + "px, " + y.toFixed(3) + "px) rotate(" + r.toFixed(4) + "deg) scale(" + z.toFixed(5) + ")";
  },
});
