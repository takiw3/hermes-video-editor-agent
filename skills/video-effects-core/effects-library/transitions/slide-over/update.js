/* slide-over: the incoming scene slides over a still outgoing one. MIT, video-editor profile. */
HFX.define("slide-over", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;var d = Math.round(s.direction), dx = [-1, 1, 0, 0][d], dy = [0, 0, -1, 1][d];
    ctx.to.style.transform = "translate(" + (-dx * (1 - e) * 100) + "%, " + (-dy * (1 - e) * 100) + "%)";
  },
});
