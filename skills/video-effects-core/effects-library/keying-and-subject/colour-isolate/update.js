/* colour-isolate: a mask from one channel's lead over the others, colour over grey. MIT, video-editor profile. */
HFX.define("colour-isolate", {
  update: function (s, ctx) {
    var c = Math.round(s.channel), k = s.strength, row = [-k / 2, -k / 2, -k / 2];
    row[c] = k;
    ctx.q("mask").setAttribute("values", "0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  " + row.map(function (v) { return v.toFixed(4); }).join(" ") + " 0 -0.15");
    HFX.mix(ctx, s, 1);
  },
});
