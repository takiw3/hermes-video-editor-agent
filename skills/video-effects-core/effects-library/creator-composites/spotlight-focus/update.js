/* spotlight-focus: a radial-gradient shade over the frame. MIT, video-editor profile. */
HFX.define("spotlight-focus", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }

    var o = ctx.q("shade").style;
    if (!s.active) { o.opacity = "0"; return; }
    var k = Math.min(1, Math.max(0, s.local / 0.4));
    o.opacity = String(k);
    var r = s.radius * 100;
    o.background = "radial-gradient(circle at " + (s.cx * 100) + "% " + (s.cy * 100) + "%, rgba(0,0,0,0) " + (r * 0.8).toFixed(2) + "%, rgba(0,0,0," + s.dark + ") " + (r * 1.15).toFixed(2) + "%)";
  },
});
