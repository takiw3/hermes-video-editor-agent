/* scan-bar: a screened gradient band whose position is a function of time. MIT, video-editor profile. */
HFX.define("scan-bar", {
  update: function (s, ctx) {
    var y = ((s.speed * Math.max(0, s.local)) % 1) * 118 - 18;
    var bar = ctx.q("bar").style;
    bar.top = y.toFixed(3) + "%";
    var a = s.active ? s.strength : 0;
    bar.background = "linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255," + a.toFixed(3) + ") 50%, rgba(255,255,255,0))";
  },
});
