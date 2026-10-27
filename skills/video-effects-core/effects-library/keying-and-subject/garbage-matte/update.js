/* garbage-matte: a rounded inset clip on the layer. MIT, video-editor profile. */
HFX.define("garbage-matte", {
  update: function (s, ctx) {
    var r = HFX.px(ctx, s.round).toFixed(2);
    ctx.el.style.clipPath = s.active ? "inset(" + (s.top * 100) + "% " + (s.right * 100) + "% " + (s.bottom * 100) + "% " + (s.left * 100) + "% round " + r + "px)" : "none";
  },
});
