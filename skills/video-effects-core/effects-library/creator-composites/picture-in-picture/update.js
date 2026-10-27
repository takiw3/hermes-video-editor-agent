/* picture-in-picture: the second layer scaled into a corner with an eased pop. MIT, video-editor profile. */
HFX.define("picture-in-picture", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }
    var k = Math.min(1, Math.max(0, s.local / Math.max(0.01, s.intro))), e = 1 - Math.pow(1 - k, 3);var c = Math.round(s.corner), sx = (c === 1 || c === 3) ? 1 : -1, sy = c >= 2 ? 1 : -1;
    reset(ctx.el);
    if (!s.active) { reset(ctx.to); ctx.to.style.opacity = "0"; return; }
    var m = 0.04, z = s.size * (0.6 + 0.4 * e);
    var tx = sx * (50 - s.size * 50 - m * 100), ty = sy * (50 - s.size * 50 - m * 100 * ctx.w / ctx.h);
    ctx.to.style.opacity = String(e);
    ctx.to.style.transform = "translate(" + tx.toFixed(3) + "%, " + ty.toFixed(3) + "%) scale(" + z.toFixed(4) + ")";
    ctx.to.style.borderRadius = (6 / z).toFixed(2) + "%";
    ctx.to.style.boxShadow = "0 " + (12 / z).toFixed(1) + "px " + (40 / z).toFixed(1) + "px rgba(0,0,0,0.45)";
  },
});
