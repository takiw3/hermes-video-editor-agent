/* zoom-through: the outgoing scene scales up as the incoming one settles. MIT, video-editor profile. */
HFX.define("zoom-through", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    ctx.to.style.opacity = String(Math.min(1, Math.max(0, (e - 0.35) / 0.4)));
    ctx.to.style.transform = "scale(" + (1 + s.zoom * 0.5 * (1 - e)).toFixed(4) + ")";
    if (s.local < 0) return;
    ctx.from.style.transform = "scale(" + (1 + s.zoom * e).toFixed(4) + ")";
  },
});
