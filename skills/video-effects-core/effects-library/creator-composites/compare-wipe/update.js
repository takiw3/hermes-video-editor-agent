/* compare-wipe: a moving clip edge on the second layer, with a divider line. MIT, video-editor profile. */
HFX.define("compare-wipe", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }

    var line = ctx.q("line");
    reset(ctx.el);
    if (!s.active) { reset(ctx.to); ctx.to.style.opacity = "0"; line.style.opacity = "0"; return; }
    var k = Math.min(1, Math.max(0, s.local / s.sweep)), e = 1 - Math.pow(1 - k, 3), x = (1 - e) + e * s.pos;
    ctx.to.style.opacity = "1";
    ctx.to.style.clipPath = "inset(0 0 0 " + (x * 100).toFixed(3) + "%)";
    line.style.opacity = "1";
    line.style.left = "calc(" + (x * 100).toFixed(3) + "% - 1px)";
  },
});
