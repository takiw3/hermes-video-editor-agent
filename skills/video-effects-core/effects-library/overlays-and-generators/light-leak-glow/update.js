/* light-leak-glow: a screened radial gradient whose centre drifts by slow noise. MIT, video-editor profile. */
HFX.define("light-leak-glow", {
  update: function (s, ctx) {
    var x = 10 + 70 * (0.5 + 0.5 * HFX.noise1(ctx.seed, s.local * 0.35)), y = 30 + 30 * HFX.noise1(ctx.seed + 5, s.local * 0.25);
    var a = s.active ? s.strength : 0;
    ctx.q("leak").style.background = "radial-gradient(ellipse 60% 80% at " + x.toFixed(2) + "% " + y.toFixed(2) + "%, hsla(" + s.hue + ",100%,60%," + a.toFixed(3) + "), hsla(" + (s.hue + 20) + ",100%,50%,0) 70%)";
  },
});
