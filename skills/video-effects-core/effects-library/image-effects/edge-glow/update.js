/* edge-glow: edges from a Laplacian kernel, added back to the picture. MIT, video-editor profile. */
HFX.define("edge-glow", {
  update: function (s, ctx) {
    HFX.attrs(ctx.q("add"), { k2: s.gain.toFixed(4) });
    HFX.mix(ctx, s, s.mix);
  },
});
