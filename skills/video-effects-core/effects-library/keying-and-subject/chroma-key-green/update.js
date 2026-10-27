/* chroma-key-green: alpha from how much green beats red and blue, with spill pulled back. MIT, video-editor profile. */
HFX.define("chroma-key-green", {
  update: function (s, ctx) {
    var k = s.strength;
    // alpha = 1 + k * (mean of the other two channels - the screen channel)
    var row = 1 === 1 ? [k / 2, -k, k / 2] : [k / 2, k / 2, -k];
    ctx.q("key").setAttribute("values", "0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  " + row.map(function (v) { return v.toFixed(4); }).join(" ") + " 0 1");
    var sp = s.spill;
    var g = 1 === 1 ? [sp / 2, 1 - sp, sp / 2] : [0, 1, 0], b = 1 === 2 ? [sp / 2, sp / 2, 1 - sp] : [0, 0, 1];
    ctx.q("spill").setAttribute("values", "1 0 0 0 0  " + g.join(" ") + " 0 0  " + b.join(" ") + " 0 0  0 0 0 1 0");
    var slope = 1 / Math.max(0.02, s.softness);
    HFX.attrs(ctx.q("edge").children[0], { slope: slope.toFixed(4), intercept: (-(slope - 1) * 0.5).toFixed(4) });
    HFX.mix(ctx, s, 1);
  },
});
