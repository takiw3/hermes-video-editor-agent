/* scramble-text: letters drawn from a hash of the time slot until each one's settle time. MIT, video-editor profile. */
HFX.define("scramble-text", {
  setup: function (ctx, params) {
    ctx.ch = ctx.qa("ch");
    ctx.orig = ctx.ch.map(function (c) { return c.textContent; });
  },
  update: function (s, ctx) {
    var glyphs = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#$%&*";
    var slot = Math.floor(Math.max(0, s.local) * s.rate);
    for (var i = 0; i < ctx.ch.length; i++) {
      var settle = s.duration * (i + 1) / ctx.ch.length;
      var real = ctx.orig[i];
      ctx.ch[i].textContent = !s.active || s.local >= settle || real === " " ? real : glyphs.charAt(Math.floor(ctx.rand(slot * 97 + i) * glyphs.length));
    }
  },
});
