/* lower-third: a two-line name bar revealed left to right. MIT, video-editor profile. */
HFX.define("lower-third", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }
    var k = Math.min(1, Math.max(0, s.local / Math.max(0.01, s.intro))), e = 1 - Math.pow(1 - k, 3);
    var bar = ctx.q("bar");
    if (!s.active) { bar.style.opacity = "0"; return; }
    bar.style.opacity = "1";
    bar.style.borderLeftColor = "hsl(" + s.hue + ",95%,55%)";
    bar.style.clipPath = "inset(0 " + ((1 - e) * 100).toFixed(2) + "% 0 0)";
    bar.style.transform = "translateX(" + (-(1 - e) * 12).toFixed(2) + "px)";
  },
});
