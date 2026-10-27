/* pulsing-bloom: a smooth cosine pulse on HyperFrames' animatable bloom property. MIT, video-editor profile. */
HFX.define("pulsing-bloom", {
  update: function (s, ctx) {
    var phase = 0.5 - 0.5 * Math.cos(2 * Math.PI * s.rate * s.local);
    var v = s.active ? s.amount * (0.25 + 0.75 * phase) : 0;
    ctx.el.style.setProperty("--hf-color-grading-bloom", String(v));
  },
});
