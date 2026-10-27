/* linear-wipe: a soft straight edge reveals the incoming scene. MIT, video-editor profile. */
HFX.define("linear-wipe", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    var f = s.feather, pos = e * (100 + 2 * f) - f;
    var mask = "linear-gradient(" + s.angle + "deg, #000 " + (pos - f) + "%, rgba(0,0,0,0) " + (pos + f + (f === 0 ? 0.001 : 0)) + "%)";
    ctx.to.style.webkitMaskImage = ctx.to.style.maskImage = mask;
  },
});
