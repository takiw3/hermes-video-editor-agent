/* comic-ink-posterize: posterized colour minus an edge map. MIT, video-editor profile. */
HFX.define("comic-ink-posterize", {
  setup: function (ctx, params) {
    ctx.funcs = Array.prototype.slice.call(ctx.q("steps").children);
  },
  update: function (s, ctx) {
    var n = Math.max(2, Math.round(s.levels)), table = [];
    for (var i = 0; i < n; i++) table.push((i / (n - 1)).toFixed(4));
    for (var j = 0; j < ctx.funcs.length; j++) ctx.funcs[j].setAttribute("tableValues", table.join(" "));
    HFX.attrs(ctx.q("ink"), { k3: (-1.5 * s.ink).toFixed(4) });
    HFX.mix(ctx, s, 1);
  },
});
