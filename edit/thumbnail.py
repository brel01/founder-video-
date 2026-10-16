"""Urbn founder film — thumbnails.

    python3 edit/thumbnail.py      # writes output/thumbnail_9x16.png and output/thumbnail_16x9.png
"""
import os

from PIL import Image, ImageDraw, ImageFilter

import render as R

OUT = os.path.join(R.ROOT, "output")


def cutout(name, h):
    return R.fit_h(Image.open(os.path.join(R.ROOT, "edit", "assets", f"{name}_cutout.png")).convert("RGBA"), h)


def soft_shadow(im, blur, alpha=170, color=(0, 0, 0)):
    a = im.getchannel("A").point(lambda v: int(v * alpha / 255)).filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new("RGBA", im.size, color + (0,))
    sh.putalpha(a)
    return sh


def fade_bottom(im, start):
    """Fade the cutout's lower edge so the figure melts into the frame bottom."""
    a = im.getchannel("A")
    g = Image.linear_gradient("L").resize(im.size)  # 0 top -> 255 bottom
    k = g.point(lambda v: 255 if v / 255 < start else int(255 * max(0, 1 - (v / 255 - start) / (1 - start)) ** 1.4))
    im = im.copy()
    im.putalpha(Image.composite(a, Image.new("L", im.size, 0), k))
    return im


def vertical():
    W, H = 1080, 1920
    c = R.solid(R.BLACK, (W, H))
    # Founder standing inside the brand U.
    u = R.fit_h(R.tint(R.ICON, R.BLUE), 1080)
    ux, uy = (W - u.width) // 2, 700
    glow = R.glow(420, R.BLUE, 0.55)
    c.alpha_composite(glow, (W // 2 - glow.width // 2, 1180 - glow.height // 2))
    c.alpha_composite(u, (ux, uy))
    f = fade_bottom(cutout("DSC00718", 1350), 0.9)
    fx, fy = (W - f.width) // 2 + 30, 620
    c.alpha_composite(soft_shadow(f, 30, 200), (fx - 10, fy + 20))
    c.alpha_composite(f, (fx, fy))
    # The U's bowl passes in front of him: he stands inside the mark.
    cut = int(u.height * 0.64)
    bowl = u.crop((0, cut, u.width, u.height))
    c.alpha_composite(bowl, (ux, uy + cut))
    c.alpha_composite(R.grad_top(0.40, 0.9, (0, 0, 0)))
    # Header + headline
    R.top_bar(c, 9, 0, dark=True)
    d = ImageDraw.Draw(c)
    d.rectangle((R.M, 268, R.M + 26, 294), fill=R.BLUE + (255,))
    R.put_text(c, "INTRODUCING URBN", R.M + 46, 261, 34, color=R.WHITE, fontname=R.BODY, track=0.12)
    R.put_text(c, "Why is housing", R.M, 330, 132, color=R.WHITE)
    R.put_text(c, "still disconnected?", R.M, 480, 132 * 0 + 112, color=R.WHITE, hl="disconnected?",
               hl_color=R.WHITE, hl_bg=R.BLUE)
    # Footer line
    R.put_text(c, "The digital infrastructure for housing", W / 2, H - 104, 34, color=(205, 205, 212),
               fontname=R.BODY, track=0.0, align="center")
    return c.convert("RGB")


def landscape():
    W, H = 1280, 720
    c = R.solid(R.BLACK, (W, H))
    wm = R.fit_h(R.tint(R.ICON, (24, 24, 24)), 820)
    c.alpha_composite(wm, (330, -150))
    # Right: founder stepping out of a brand-blue card
    panel = Image.new("RGBA", (420, 600), R.BLUE + (255,))
    panel.putalpha(R.rounded_mask(panel.size, 28))
    pu = R.fit_h(R.tint(R.ICON, R.WHITE, 0.10), 700)
    panel.alpha_composite(pu, (150, -40))
    c.alpha_composite(panel, (800, 90))
    f = fade_bottom(cutout("DSC00562", 860), 0.72)
    fx, fy = 1010 - f.width // 2, 40
    c.alpha_composite(soft_shadow(f, 18, 200), (fx - 6, fy + 12))
    c.alpha_composite(f, (fx, fy))
    # Left: wordmark, headline, line
    logo = R.fit_h(R.tint(R.LOGO_W, R.WHITE), 40)
    c.alpha_composite(logo, (64, 60))
    d = ImageDraw.Draw(c)
    d.rectangle((64, 168, 84, 188), fill=R.BLUE + (255,))
    R.put_text(c, "INTRODUCING URBN", 100, 162, 24, color=R.WHITE, fontname=R.BODY, track=0.12)
    R.put_text(c, "Why is housing", 64, 214, 92, color=R.WHITE)
    R.put_text(c, "still", 64, 320, 92, color=R.WHITE)
    R.put_text(c, "disconnected?", 64, 428, 92, color=R.WHITE, hl="disconnected?", hl_color=R.WHITE, hl_bg=R.BLUE)
    d.rectangle((64, 620, 84, 640), fill=R.BLUE + (255,))
    d.line((104, 630, 640, 630), fill=(255, 255, 255, 140), width=2)
    return c.convert("RGB")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    vertical().save(os.path.join(OUT, "thumbnail_9x16.png"), optimize=True)
    landscape().save(os.path.join(OUT, "thumbnail_16x9.png"), optimize=True)
    print("ok")
