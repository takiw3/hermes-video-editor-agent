/* spin-rotate: rotation and scale on both scenes with a crossfade. MIT, video-editor profile. */
HFX.define("spin-rotate", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    ctx.to.style.opacity = String(e);
    ctx.to.style.transform = "rotate(" + (-(1 - e) * s.angle).toFixed(3) + "deg) scale(" + (0.7 + 0.3 * e).toFixed(4) + ")";
    if (s.local < 0) return;
    ctx.from.style.transform = "rotate(" + (e * s.angle).toFixed(3) + "deg) scale(" + (1 - 0.3 * e).toFixed(4) + ")";
  },
});
