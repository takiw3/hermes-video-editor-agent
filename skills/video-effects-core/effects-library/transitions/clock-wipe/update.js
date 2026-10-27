/* clock-wipe: a conic mask sweeps through a full turn. MIT, video-editor profile. */
HFX.define("clock-wipe", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    var a = e * (360 + s.feather);
    var mask = "conic-gradient(from 0deg at 50% 50%, #000 " + (a - s.feather) + "deg, rgba(0,0,0,0) " + (a + 0.001) + "deg)";
    ctx.to.style.webkitMaskImage = ctx.to.style.maskImage = mask;
  },
});
