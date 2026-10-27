/* rec-hud: viewfinder marks with a timecode and a one-hertz REC dot. MIT, video-editor profile. */
HFX.define("rec-hud", {
  update: function (s, ctx) {
    var hud = ctx.q("hud").style;
    hud.opacity = s.active ? String(s.opacity) : "0";
    var sec = Math.floor(s.offset + Math.max(0, s.local));
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    ctx.q("tc").textContent = pad(Math.floor(sec / 3600)) + ":" + pad(Math.floor(sec / 60) % 60) + ":" + pad(sec % 60);
    ctx.q("dot").style.opacity = (Math.floor(Math.max(0, s.local) * 2) % 2 === 0) ? "1" : "0.15";
  },
});
