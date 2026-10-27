/* blur-dissolve: a crossfade with blur peaking at the midpoint. MIT, video-editor profile. */
HFX.define("blur-dissolve", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    var b = HFX.px(ctx, s.blur) * Math.sin(Math.PI * s.u);
    ctx.to.style.opacity = String(e);
    ctx.to.style.filter = "blur(" + b.toFixed(3) + "px)";
    if (s.local < 0) return;
    ctx.from.style.filter = "blur(" + b.toFixed(3) + "px)";
  },
});
