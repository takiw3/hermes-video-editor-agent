/* posterize: n flat steps per channel. MIT, video-editor profile. */
HFX.define("posterize", {
  setup: function (ctx, params) {
    ctx.funcs = Array.prototype.slice.call(ctx.q("steps").children);
  },
  update: function (s, ctx) {
    var n = Math.max(2, Math.round(s.levels));
    var table = [];
    for (var i = 0; i < n; i++) table.push((i / (n - 1)).toFixed(4));
    for (var j = 0; j < ctx.funcs.length; j++) ctx.funcs[j].setAttribute("tableValues", table.join(" "));
    HFX.mix(ctx, s, 1);
  },
});
