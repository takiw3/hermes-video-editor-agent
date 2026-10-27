/* ken-burns-pan: a fixed zoom with a translation that crosses the spare margin. MIT, video-editor profile. */
HFX.define("ken-burns-pan", {
  update: function (s, ctx) {
    var z = s.scale, travel = (z - 1) / 2 * 100 / z;
    var x = s.active ? -s.pan * travel * (s.u * 2 - 1) : 0, y = s.active ? -s.tilt * travel * (s.u * 2 - 1) : 0;
    ctx.el.style.transform = s.active ? "scale(" + z + ") translate(" + x.toFixed(4) + "%, " + y.toFixed(4) + "%)" : "none";
  },
});
