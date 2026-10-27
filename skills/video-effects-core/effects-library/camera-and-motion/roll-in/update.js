/* roll-in: rotation that eases out to level. MIT, video-editor profile. */
HFX.define("roll-in", {
  update: function (s, ctx) {
    function cover(ctx, deg) {
      var a = Math.abs(deg) * Math.PI / 180, r = ctx.w / ctx.h;
      return Math.max(Math.cos(a) + r * Math.sin(a), Math.cos(a) + Math.sin(a) / r);
    }
    var k = Math.min(1, Math.max(0, s.local / s.time));
    var d = s.active ? s.angle * Math.pow(1 - k, 3) : 0;
    ctx.el.style.transform = "rotate(" + d.toFixed(4) + "deg) scale(" + cover(ctx, d).toFixed(5) + ")";
  },
});
