/* gradient-wash: a soft-light gradient whose angle drifts slowly. MIT, video-editor profile. */
HFX.define("gradient-wash", {
  update: function (s, ctx) {
    var ang = 120 + 40 * HFX.noise1(ctx.seed, s.local * 0.2);
    var w = ctx.q("wash").style;
    w.opacity = s.active ? String(s.strength) : "0";
    w.background = "linear-gradient(" + ang.toFixed(2) + "deg, hsl(" + s.hue + ",90%,55%), hsl(" + s.hue2 + ",90%,55%))";
  },
});
