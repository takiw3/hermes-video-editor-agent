/* luma-key: alpha from relative luminance against a movable cut point. MIT, video-editor profile. */
HFX.define("luma-key", {
  update: function (s, ctx) {
    var g = 1 / Math.max(0.02, s.softness), inv = Math.round(s.invert) ? -1 : 1;
    var w = [0.2126, 0.7152, 0.0722].map(function (c) { return (inv * c * g).toFixed(4); });
    var bias = inv === 1 ? -s.threshold * g : s.threshold * g;
    ctx.q("key").setAttribute("values", "0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  " + w.join(" ") + " 0 " + bias.toFixed(4));
    HFX.mix(ctx, s, 1);
  },
});
