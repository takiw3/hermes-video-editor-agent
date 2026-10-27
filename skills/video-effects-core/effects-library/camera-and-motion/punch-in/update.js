/* punch-in: scale up around a chosen point with a short eased ramp. MIT, video-editor profile. */
HFX.define("punch-in", {
  update: function (s, ctx) {
    var k = s.ramp > 0 ? Math.min(1, Math.max(0, s.local / s.ramp)) : 1;
    k = 1 - Math.pow(1 - k, 3);
    var z = s.active ? 1 + (s.zoom - 1) * k : 1;
    ctx.el.style.transformOrigin = (s.cx * 100) + "% " + (s.cy * 100) + "%";
    ctx.el.style.transform = "scale(" + z.toFixed(5) + ")";
  },
});
