/* emboss: a directional relief kernel. MIT, video-editor profile. */
HFX.define("emboss", {
  update: function (s, ctx) {
    var d = s.strength;
    ctx.q("k").setAttribute("kernelMatrix", [-2 * d, -d, 0, -d, 1, d, 0, d, 2 * d].map(function (v) { return v.toFixed(4); }).join(" "));
    HFX.mix(ctx, s, s.mix);
  },
});
