/* progress-bar: width follows progress through the window. MIT, video-editor profile. */
HFX.define("progress-bar", {
  update: function (s, ctx) {
    var b = ctx.q("bar").style;
    b.height = HFX.px(ctx, s.thickness).toFixed(2) + "px";
    b.background = "hsl(" + s.hue + ",95%,55%)";
    b.width = (s.active ? s.u * 100 : 0).toFixed(3) + "%";
  },
});
