/* film-halation: bright areas, tinted red, blurred and added back. MIT, video-editor profile. */
HFX.define("film-halation", {
  update: function (s, ctx) {
    var knee = 1 / Math.max(0.05, 1 - s.threshold);
    HFX.attrs(ctx.q("knee").children[0], { slope: knee.toFixed(4), intercept: (-s.threshold * knee).toFixed(4) });
    HFX.attrs(ctx.q("knee").children[1], { slope: knee.toFixed(4), intercept: (-s.threshold * knee).toFixed(4) });
    HFX.attrs(ctx.q("knee").children[2], { slope: knee.toFixed(4), intercept: (-s.threshold * knee).toFixed(4) });
    ctx.q("tint").setAttribute("values", "1 0 0 0 0  0 0.35 0 0 0  0 0 0.12 0 0  0 0 0 1 0");
    ctx.q("blur").setAttribute("stdDeviation", HFX.px(ctx, s.radius).toFixed(3));
    HFX.attrs(ctx.q("add"), { k2: s.strength.toFixed(4) });
    HFX.mix(ctx, s, 1);
  },
});
