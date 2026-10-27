/* solarize: a tone curve that reverses above a threshold. MIT, video-editor profile. */
HFX.define("solarize", {
  setup: function (ctx, params) {
    ctx.funcs = Array.prototype.slice.call(ctx.q("t").children);
  },
  update: function (s, ctx) {
    var n = 32, values = [];
    for (var i = 0; i <= n; i++) {
      var v = i / n;
      values.push((v < s.threshold ? v : 1 - v).toFixed(4));
    }
    for (var j = 0; j < ctx.funcs.length; j++) ctx.funcs[j].setAttribute("tableValues", values.join(" "));
    HFX.mix(ctx, s, 1);
  },
});
