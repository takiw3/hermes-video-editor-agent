/* slow-push: linear scale across the window. MIT, video-editor profile. */
HFX.define("slow-push", {
  update: function (s, ctx) {
    var z = s.active ? 1 + s.amount * s.u : 1;
    ctx.el.style.transformOrigin = "50% 45%";
    ctx.el.style.transform = "scale(" + z.toFixed(5) + ")";
  },
});
