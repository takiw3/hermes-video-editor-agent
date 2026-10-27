/* outline-reveal: text stroke first, fill colour faded in later. MIT, video-editor profile. */
HFX.define("outline-reveal", {
  update: function (s, ctx) {
    var k = (s.local >= 0) ? Math.min(1, Math.max(0, (s.u - s.fill_at) / 0.3)) : 0;
    ctx.el.style.webkitTextStroke = (s.local >= 0) ? s.stroke.toFixed(4) + "em currentColor" : "0";
    ctx.el.style.webkitTextFillColor = "rgba(255,255,255," + k.toFixed(4) + ")";
  },
});
