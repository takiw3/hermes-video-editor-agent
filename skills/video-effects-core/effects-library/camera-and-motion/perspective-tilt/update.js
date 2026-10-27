/* perspective-tilt: a 3D rotation in perspective, scaled down so the corners stay in frame. MIT, video-editor profile. */
HFX.define("perspective-tilt", {
  update: function (s, ctx) {
    var p = (s.depth * ctx.h / 1080).toFixed(1);
    ctx.el.style.transform = s.active ? "perspective(" + p + "px) rotateX(" + s.tilt_x.toFixed(3) + "deg) rotateY(" + s.tilt_y.toFixed(3) + "deg) scale(0.86)" : "none";
  },
});
