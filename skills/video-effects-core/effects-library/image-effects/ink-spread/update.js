/* ink-spread: morphological erosion: dark grows into light. MIT, video-editor profile. */
HFX.define("ink-spread", {
  update: function (s, ctx) {
    ctx.q("m").setAttribute("radius", HFX.px(ctx, s.radius).toFixed(3));
    HFX.mix(ctx, s, 1);
  },
});
