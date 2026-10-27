/* directional-blur: a one-axis Gaussian blur. MIT, video-editor profile. */
HFX.define("directional-blur", {
  update: function (s, ctx) {
    var b = HFX.px(ctx, s.amount).toFixed(3);
    ctx.q("blur").setAttribute("stdDeviation", Math.round(s.vertical) ? "0 " + b : b + " 0");
    HFX.mix(ctx, s, 1);
  },
});
