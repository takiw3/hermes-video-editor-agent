/* cube-rotate: two scenes on neighbouring faces of a box in perspective. MIT, video-editor profile. */
HFX.define("cube-rotate", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    var p = (s.depth * ctx.h / 1080).toFixed(1);
    ctx.to.style.transformOrigin = "left center";
    ctx.to.style.backfaceVisibility = "hidden";
    ctx.to.style.transform = "perspective(" + p + "px) translateX(" + ((1 - e) * 100).toFixed(3) + "%) rotateY(" + ((1 - e) * 90).toFixed(3) + "deg)";
    if (s.local < 0) return;
    ctx.from.style.transformOrigin = "right center";
    ctx.from.style.backfaceVisibility = "hidden";
    ctx.from.style.transform = "perspective(" + p + "px) translateX(" + (-e * 100).toFixed(3) + "%) rotateY(" + (-e * 90).toFixed(3) + "deg)";
  },
});
