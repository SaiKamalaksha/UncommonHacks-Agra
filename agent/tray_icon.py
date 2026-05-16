from PIL import Image, ImageDraw

def create_icon(color="green"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # draw a shield shape
    draw.polygon([
        (32, 4),   # top center
        (60, 16),  # top right
        (60, 36),  # mid right
        (32, 60),  # bottom center
        (4, 36),   # mid left
        (4, 16),   # top left
    ], fill=color)
    return img