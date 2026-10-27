/* blueprint-grid: a CSS grid revealed left to right. MIT, video-editor profile. */
HFX.define("blueprint-grid", {
  update: function (s, ctx) {
    var step = ctx.w / Math.round(s.cells), k = s.active ? Math.min(1, Math.max(0, s.local / 0.6)) : 0;
    var g = ctx.q("grid").style, c = "rgba(170,210,255," + (s.opacity * k).toFixed(3) + ")";
    g.backgroundImage = "linear-gradient(" + c + " 1px, rgba(0,0,0,0) 1px), linear-gradient(90deg, " + c + " 1px, rgba(0,0,0,0) 1px)";
    g.backgroundSize = step.toFixed(3) + "px " + step.toFixed(3) + "px";
    g.clipPath = "inset(0 " + ((1 - k) * 100).toFixed(3) + "% 0 0)";
  },
});
