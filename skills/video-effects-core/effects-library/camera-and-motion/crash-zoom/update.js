/* crash-zoom: a quartic ease-out zoom at the start of the window. MIT, video-editor profile. */
HFX.define("crash-zoom", {
  update: function (s, ctx) {
    var k = Math.min(1, Math.max(0, s.local / s.time));
    k = 1 - Math.pow(1 - k, 4);
    var z = s.active ? 1 + (s.zoom - 1) * k : 1;
    ctx.el.style.transformOrigin = "50% 45%";
    ctx.el.style.transform = "scale(" + z.toFixed(5) + ")";
  },
});
