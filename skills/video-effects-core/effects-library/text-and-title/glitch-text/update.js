/* glitch-text: per-letter offsets and colour ghosts chosen by a hash of the time slot. MIT, video-editor profile. */
HFX.define("glitch-text", {
  setup: function (ctx, params) {
    ctx.ch = ctx.qa("ch");
  },
  update: function (s, ctx) {
    var slot = Math.floor(Math.max(0, s.local) * s.rate);
    for (var i = 0; i < ctx.ch.length; i++) {
      var on = s.active && ctx.rand(slot * 131 + i) < 0.35;
      var dx = on ? (ctx.rand(slot * 131 + i + 7) - 0.5) * 2 * s.amount : 0;
      ctx.ch[i].style.transform = "translateX(" + dx.toFixed(4) + "em)";
      ctx.ch[i].style.textShadow = on ? (s.amount * 0.6).toFixed(3) + "em 0 rgba(255,40,80,0.8), " + (-s.amount * 0.6).toFixed(3) + "em 0 rgba(40,200,255,0.8)" : "none";
    }
  },
});
