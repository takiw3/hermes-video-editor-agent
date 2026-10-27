/* face-cam-bubble: a circular clip on the second layer and a ring drawn at the same place. MIT, video-editor profile. */
HFX.define("face-cam-bubble", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }
    var k = Math.min(1, Math.max(0, s.local / Math.max(0.01, s.intro))), e = 1 - Math.pow(1 - k, 3);var c = Math.round(s.corner), sx = (c === 1 || c === 3) ? 1 : -1, sy = c >= 2 ? 1 : -1;
    reset(ctx.el);
    var ring = ctx.q("ring");
    if (!s.active) { reset(ctx.to); ctx.to.style.opacity = "0"; ring.style.opacity = "0"; return; }
    var d = s.size * ctx.h * (0.5 + 0.5 * e), m = 0.05 * ctx.h;
    var cx = sx < 0 ? m + d / 2 : ctx.w - m - d / 2, cy = sy < 0 ? m + d / 2 : ctx.h - m - d / 2;
    ctx.to.style.opacity = "1";
    ctx.to.style.clipPath = "circle(" + (d / 2).toFixed(2) + "px at " + cx.toFixed(2) + "px " + cy.toFixed(2) + "px)";
    ring.style.opacity = "1";
    ring.style.left = (cx - d / 2).toFixed(2) + "px"; ring.style.top = (cy - d / 2).toFixed(2) + "px";
    ring.style.width = ring.style.height = d.toFixed(2) + "px";
  },
});
