/* callout-box: an outlined box revealed left to right, then a tag below it. Edit the tag text in the overlay block. MIT, video-editor profile. */
HFX.define("callout-box", {
  update: function (s, ctx) {
    function reset(el) { el.style.transform = ""; el.style.clipPath = ""; el.style.filter = ""; el.style.borderRadius = ""; el.style.boxShadow = ""; el.style.zIndex = ""; }

    var box = ctx.q("box"), tag = ctx.q("tag");
    if (!s.active) { box.style.opacity = tag.style.opacity = "0"; return; }
    var k = Math.min(1, Math.max(0, s.local / 0.5)), c = "hsl(" + s.hue + ",95%,55%)";
    box.style.opacity = "1";
    box.style.left = (s.x * 100) + "%"; box.style.top = (s.y * 100) + "%";
    box.style.width = (s.w * 100) + "%"; box.style.height = (s.h * 100) + "%";
    box.style.borderColor = c;
    box.style.clipPath = "inset(0 " + ((1 - k) * 100).toFixed(2) + "% 0 0)";
    var t = Math.min(1, Math.max(0, (s.local - 0.4) / 0.25));
    tag.style.opacity = String(t);
    tag.style.background = c;
    tag.style.left = (s.x * 100) + "%"; tag.style.top = "calc(" + ((s.y + s.h) * 100) + "% + 4px)";
    tag.style.transform = "translateY(" + ((1 - t) * 6).toFixed(2) + "px)";
  },
});
