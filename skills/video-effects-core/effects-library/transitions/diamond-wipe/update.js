/* diamond-wipe: a growing diamond clip on the incoming scene. MIT, video-editor profile. */
HFX.define("diamond-wipe", {
  update: function (s, ctx) {
    var e = s.u < 0.5 ? 2 * s.u * s.u : 1 - Math.pow(-2 * s.u + 2, 2) / 2;
    var r = e * 160, x = s.cx * 100, y = s.cy * 100;
    ctx.to.style.clipPath = "polygon(" + x + "% " + (y - r) + "%, " + (x + r) + "% " + y + "%, " + x + "% " + (y + r) + "%, " + (x - r) + "% " + y + "%)";
  },
});
