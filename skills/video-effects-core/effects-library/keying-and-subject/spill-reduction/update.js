/* spill-reduction: green pulled toward the mean of red and blue. MIT, video-editor profile. */
HFX.define("spill-reduction", {
  update: function (s, ctx) {
    var a = s.amount;
    ctx.q("spill").setAttribute("values", "1 0 0 0 0  " + (a / 2).toFixed(4) + " " + (1 - a).toFixed(4) + " " + (a / 2).toFixed(4) + " 0 0  0 0 1 0 0  0 0 0 1 0");
    HFX.mix(ctx, s, 1);
  },
});
