/* typewriter: characters revealed by count from elapsed time. MIT, video-editor profile. */
HFX.define("typewriter", {
  setup: function (ctx, params) {
    ctx.ch = ctx.qa("ch");
  },
  update: function (s, ctx) {
    var shown = (s.local >= 0) ? Math.floor(Math.max(0, s.local) * s.speed) : 0;
    for (var i = 0; i < ctx.ch.length; i++) ctx.ch[i].style.opacity = i < shown ? "1" : "0";
    ctx.el.style.borderRight = (s.local >= 0) && shown < ctx.ch.length ? "0.08em solid currentColor" : "0 solid transparent";
  },
});
