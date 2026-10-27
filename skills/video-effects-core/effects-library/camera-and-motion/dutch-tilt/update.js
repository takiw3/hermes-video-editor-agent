/* dutch-tilt: rotation with the smallest scale that still covers the frame. MIT, video-editor profile. */
HFX.define("dutch-tilt", {
  update: function (s, ctx) {
    function cover(ctx, deg) {
      var a = Math.abs(deg) * Math.PI / 180, r = ctx.w / ctx.h;
      return Math.max(Math.cos(a) + r * Math.sin(a), Math.cos(a) + Math.sin(a) / r);
    }
    var d = s.active ? s.angle : 0;
    ctx.el.style.transform = "rotate(" + d.toFixed(4) + "deg) scale(" + cover(ctx, d).toFixed(5) + ")";
  },
});
