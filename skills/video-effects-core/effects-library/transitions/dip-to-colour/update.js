/* dip-to-colour: a coloured layer rises and falls; the scenes swap at its peak. MIT, video-editor profile. */
HFX.define("dip-to-colour", {
  update: function (s, ctx) {
    var dark = 1 - Math.abs(2 * s.u - 1);
    var cover = ctx.q("cover").style;
    cover.backgroundColor = "hsl(" + s.hue + ", 85%, " + Math.round(s.lightness * 100) + "%)";
    cover.opacity = String(s.local < 0 ? 0 : dark);
    ctx.to.style.opacity = s.u >= 0.5 ? "1" : "0";
  },
});
