/* photo-card: the main layer scaled, tilted and given a white border and shadow. MIT, video-editor profile. */
HFX.define("photo-card", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }

    if (!s.active) { reset(ctx.el); return; }
    ctx.el.style.transform = "rotate(" + s.tilt.toFixed(3) + "deg) scale(" + s.fit.toFixed(4) + ")";
    ctx.el.style.boxShadow = "0 0 0 " + (8 / s.fit).toFixed(1) + "px #fafaf7, 0 " + (16 / s.fit).toFixed(1) + "px " + (40 / s.fit).toFixed(1) + "px rgba(0,0,0,0.5)";
  },
});
