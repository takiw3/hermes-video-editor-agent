/* diffusion-glow: a blurred copy screened over the picture. MIT, video-editor profile. */
HFX.define("diffusion-glow", {
  update: function (s, ctx) {
    ctx.q("blur").setAttribute("stdDeviation", HFX.px(ctx, s.radius).toFixed(3));
    HFX.attrs(ctx.q("haze"), { k2: s.strength.toFixed(4), k3: (1 - s.strength).toFixed(4) });
    HFX.mix(ctx, s, 1);
  },
});
