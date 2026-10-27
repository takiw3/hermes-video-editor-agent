/* unsharp-sharpen: a 3x3 sharpening kernel. MIT, video-editor profile. */
HFX.define("unsharp-sharpen", {
  update: function (s, ctx) {
    var k = s.amount;
    ctx.q("k").setAttribute("kernelMatrix", [0, -k, 0, -k, 1 + 4 * k, -k, 0, -k, 0].map(function (v) { return v.toFixed(4); }).join(" "));
    HFX.mix(ctx, s, 1);
  },
});
