/* highlight-sweep: a background bar whose width follows progress. MIT, video-editor profile. */
HFX.define("highlight-sweep", {
  update: function (s, ctx) {
    var k = (s.local >= 0) ? Math.min(1, Math.max(0, s.local / s.time)) : 0;
    k = 1 - Math.pow(1 - k, 2);
    var c = "hsla(" + s.hue + ",95%,55%,0.85)";
    ctx.el.style.backgroundImage = "linear-gradient(" + c + ", " + c + ")";
    ctx.el.style.backgroundRepeat = "no-repeat";
    ctx.el.style.backgroundPosition = "0 85%";
    ctx.el.style.backgroundSize = (k * 100).toFixed(3) + "% 40%";
    ctx.el.style.boxDecorationBreak = "clone";
  },
});
