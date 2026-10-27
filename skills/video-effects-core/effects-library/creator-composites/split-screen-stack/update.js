/* split-screen-stack: each layer's middle half, clipped and slid up or down. MIT, video-editor profile. */
HFX.define("split-screen-stack", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }
    var k = Math.min(1, Math.max(0, s.local / Math.max(0.01, s.intro))), e = 1 - Math.pow(1 - k, 3);
    if (!s.active) { reset(ctx.el); reset(ctx.to); ctx.to.style.opacity = "0"; return; }
    var g = s.gap / 2;
    ctx.el.style.clipPath = "inset(25% 0 " + (25 + g) + "% 0)";
    ctx.el.style.transform = "translateY(" + (-25 - (1 - e) * 50).toFixed(3) + "%)";
    ctx.to.style.opacity = "1";
    ctx.to.style.clipPath = "inset(" + (25 + g) + "% 0 25% 0)";
    ctx.to.style.transform = "translateY(" + (25 + (1 - e) * 50).toFixed(3) + "%)";
  },
});
