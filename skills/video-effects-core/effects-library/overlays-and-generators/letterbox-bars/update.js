/* letterbox-bars: two bars sized from the target aspect ratio. MIT, video-editor profile. */
HFX.define("letterbox-bars", {
  update: function (s, ctx) {
    var bar = Math.max(0, (ctx.h - ctx.w / s.ratio) / 2);
    var k = s.time > 0 ? Math.min(1, Math.max(0, s.local / s.time)) : 1;
    k = s.active ? 1 - Math.pow(1 - k, 3) : 0;
    ctx.q("top").style.height = ctx.q("bottom").style.height = (bar * k).toFixed(3) + "px";
  },
});
