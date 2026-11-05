import os
import math
from PIL import Image, ImageDraw

COLOR = (255, 34, 0, 255)  # ScrapeHero standard annotation red: #FF2200

def draw_arrow(image_path, tip_x, tip_y, direction='right', length=130, start_pos=None, out_path=None):
    """
    Draws a standard ScrapeHero markup arrow with 4x Lanczos antialiasing.
    direction: 'right', 'left', 'up', 'down', 'up-right', 'down-right'
    tip_x, tip_y: target position where arrow tip lands
    length: total length of arrow from start of shaft to tip
    start_pos: optional (sx, sy) tuple to specify exact arrow origin
    """
    if out_path is None:
        out_path = image_path
        
    img = Image.open(image_path).convert("RGBA")
    
    scale = 4
    canvas = Image.new("RGBA", (img.width * scale, img.height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    if start_pos is not None:
        sx, sy = start_pos
        dx = tip_x - sx
        dy = tip_y - sy
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        ux, uy = dx / dist, dy / dist
    else:
        if direction == 'right':
            ux, uy = 1.0, 0.0
        elif direction == 'left':
            ux, uy = -1.0, 0.0
        elif direction == 'down':
            ux, uy = 0.0, 1.0
        elif direction == 'up':
            ux, uy = 0.0, -1.0
        elif direction == 'up-right':
            ux, uy = 1.0 / math.sqrt(2), -1.0 / math.sqrt(2)
        elif direction == 'down-right':
            ux, uy = 1.0 / math.sqrt(2), 1.0 / math.sqrt(2)
        else:
            ux, uy = 1.0, 0.0
        dist = length
        sx = tip_x - ux * dist
        sy = tip_y - uy * dist

    px, py = -uy, ux
    
    head_len = 32 * scale
    head_half_w = 14 * scale
    shaft_half_w = 3.5 * scale
    
    txs, tys = tip_x * scale, tip_y * scale
    sxs, sys = sx * scale, sy * scale
    
    base_x = txs - ux * head_len
    base_y = tys - uy * head_len
    
    p1 = (txs, tys)
    p2 = (base_x + px * head_half_w, base_y + py * head_half_w)
    p3 = (base_x - px * head_half_w, base_y - py * head_half_w)
    
    s1 = (sxs + px * shaft_half_w, sys + py * shaft_half_w)
    s2 = (sxs - px * shaft_half_w, sys - py * shaft_half_w)
    s3 = (base_x - px * shaft_half_w, base_y - py * shaft_half_w)
    s4 = (base_x + px * shaft_half_w, base_y + py * shaft_half_w)
    
    draw.polygon([s1, s2, s3, s4], fill=COLOR)
    draw.polygon([p1, p2, p3], fill=COLOR)
    
    overlay = canvas.resize((img.width, img.height), Image.Resampling.LANCZOS)
    img.alpha_composite(overlay)
    
    if out_path.lower().endswith(('.jpg', '.jpeg')):
        img.convert("RGB").save(out_path, quality=95)
    else:
        img.save(out_path)
    print(f"Arrow applied to {out_path}")

def draw_box(image_path, x1, y1, x2, y2, stroke_width=6, out_path=None):
    """
    Draws a red bounding box with specified stroke_width (default: 6px).
    """
    if out_path is None:
        out_path = image_path
        
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    for i in range(stroke_width):
        draw.rectangle([x1 + i, y1 + i, x2 - i, y2 - i], outline=COLOR[:3])
        
    if out_path.lower().endswith(('.jpg', '.jpeg')):
        img.convert("RGB").save(out_path, quality=95)
    else:
        img.save(out_path)
    print(f"Box applied to {out_path}")

if __name__ == '__main__':
    print("markup_helper ready")
