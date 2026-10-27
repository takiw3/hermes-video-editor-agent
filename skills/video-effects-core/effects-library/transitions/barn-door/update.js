/* barn-door: a centre band mask that widens to the edges. MIT, video-editor profile. */
HFX.define("barn-door", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    var half = e * 50, f = s.feather, dir = Math.round(s.vertical) ? "to bottom" : "to right";
    var mask = "linear-gradient(" + dir + ", rgba(0,0,0,0) " + (50 - half - f) + "%, #000 " + (50 - half) + "%, #000 " + (50 + half) + "%, rgba(0,0,0,0) " + (50 + half + f) + "%)";
    if (e <= 0) mask = "linear-gradient(rgba(0,0,0,0), rgba(0,0,0,0))";
    ctx.to.style.webkitMaskImage = ctx.to.style.maskImage = mask;
  },
});
