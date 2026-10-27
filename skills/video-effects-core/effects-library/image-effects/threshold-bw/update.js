/* threshold-bw: luminance cut to two levels at a movable point. MIT, video-editor profile. */
HFX.define("threshold-bw", {
  setup: function (ctx, params) {
    ctx.funcs = Array.prototype.slice.call(ctx.q("t").children);
  },
  update: function (s, ctx) {
    var n = 64, values = [];
    for (var i = 0; i < n; i++) values.push((i + 0.5) / n >= s.threshold ? "1" : "0");
    for (var j = 0; j < ctx.funcs.length; j++) ctx.funcs[j].setAttribute("tableValues", values.join(" "));
    HFX.mix(ctx, s, 1);
  },
});
