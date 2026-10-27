/* fade-through-black: a black layer rises and falls; the scenes swap at the darkest point. MIT, video-editor profile. */
HFX.define("fade-through-black", {
  update: function (s, ctx) {
    var h = s.hold, u = s.u, dark;
    if (u < 0.5 - h / 2) dark = u / (0.5 - h / 2);
    else if (u <= 0.5 + h / 2) dark = 1;
    else dark = (1 - u) / (0.5 - h / 2);
    ctx.q("cover").style.opacity = String(s.local < 0 ? 0 : Math.min(1, Math.max(0, dark)));
    ctx.to.style.opacity = s.u >= 0.5 ? "1" : "0";
  },
});
