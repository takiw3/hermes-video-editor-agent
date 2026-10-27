/* blinds: a repeating stripe mask whose stripes widen. MIT, video-editor profile. */
HFX.define("blinds", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    var size = 100 / Math.round(s.count), open = (e * size).toFixed(3);
    var mask = "repeating-linear-gradient(" + s.angle + "deg, #000 0%, #000 " + open + "%, rgba(0,0,0,0) " + open + "%, rgba(0,0,0,0) " + size.toFixed(3) + "%)";
    ctx.to.style.webkitMaskImage = ctx.to.style.maskImage = mask;
  },
});
