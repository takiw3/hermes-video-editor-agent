/* blur-fill-reframe: the main layer scaled down over a blurred fill layer. MIT, video-editor profile. */
HFX.define("blur-fill-reframe", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }

    if (!s.active) { reset(ctx.el); reset(ctx.to); ctx.to.style.opacity = "0"; return; }
    ctx.to.style.opacity = "1";
    ctx.to.style.zIndex = "0";
    ctx.el.style.zIndex = "1";
    ctx.el.style.position = "absolute";
    ctx.to.style.transform = "scale(1.25)";
    ctx.to.style.filter = "blur(" + HFX.px(ctx, s.blur).toFixed(2) + "px) brightness(0.7)";
    ctx.el.style.transform = "scale(" + s.fit.toFixed(4) + ")";
    ctx.el.style.boxShadow = "0 10px 40px rgba(0,0,0,0.5)";
  },
});
