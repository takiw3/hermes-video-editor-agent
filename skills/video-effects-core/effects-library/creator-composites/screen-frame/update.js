/* screen-frame: the main layer scaled under a window title bar, over a gradient on the composition background. MIT, video-editor profile. */
HFX.define("screen-frame", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }

    var bar = ctx.q("bar");
    if (!s.active) { reset(ctx.el); bar.style.opacity = "0"; ctx.root.style.background = ""; return; }
    bar.style.opacity = "1";
    ctx.root.style.background = "linear-gradient(135deg, hsl(" + s.hue + ",70%,45%), hsl(" + (s.hue + 40) + ",70%,30%))";
    var top = 0.07, fh = s.fit;
    ctx.el.style.transform = "translateY(" + (top * 50).toFixed(3) + "%) scale(" + fh.toFixed(4) + ")";
    ctx.el.style.borderRadius = "0 0 " + (1.2 / fh).toFixed(2) + "% " + (1.2 / fh).toFixed(2) + "%";
    var bw = fh * 100, bh = top * fh * 100, left = (100 - bw) / 2, ytop = 50 - fh * 50 + top * 50 - bh;
    bar.style.left = left.toFixed(3) + "%"; bar.style.width = bw.toFixed(3) + "%";
    bar.style.top = ytop.toFixed(3) + "%"; bar.style.height = bh.toFixed(3) + "%";
  },
});
