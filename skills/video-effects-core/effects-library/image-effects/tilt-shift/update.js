/* tilt-shift: two backdrop-blurred bands with soft masks. MIT, video-editor profile. */
HFX.define("tilt-shift", {
  update: function (s, ctx) {
    var b = s.active ? HFX.px(ctx, s.blur) : 0;
    var edge = (50 * (1 - s.band)).toFixed(2);
    var top = ctx.q("top").style, bottom = ctx.q("bottom").style;
    top.backdropFilter = bottom.backdropFilter = "blur(" + b.toFixed(3) + "px)";
    top.webkitBackdropFilter = bottom.webkitBackdropFilter = top.backdropFilter;
    top.maskImage = top.webkitMaskImage = "linear-gradient(to bottom, #000 0%, rgba(0,0,0,0) " + (edge * 2) + "%)";
    bottom.maskImage = bottom.webkitMaskImage = "linear-gradient(to top, #000 0%, rgba(0,0,0,0) " + (edge * 2) + "%)";
  },
});
