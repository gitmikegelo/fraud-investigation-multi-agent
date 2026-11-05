"""Render synthetic shipping documents for the MC-3107 demo claim into images/.

  images/mc3107.png    Commercial invoice & packing list (Orchid Trade Links) — looks genuine and
                       agrees with the B/L; the fraud only shows against the weighed VGM
  images/mc3107_1.png  Bill of lading (Meridian Container Line) — genuine, shipper's figures

Survey photos are NOT generated — supply real photos of broken glass crates:
  images/mc3107_2.png  survey photo (the SAME photo, resized/re-saved, as images/mc2988.png)
  images/mc2988.png    photo filed on prior paid claim MC-2988
  images/mc3107_3.png  optional second survey photo

All names are fictional. Figures match data/generate_marine.py (seed 3107).

Usage:  python data/generate_marine_evidence.py
"""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.generate_marine import generate_marine_data  # noqa: E402

IMAGES = Path(__file__).resolve().parent.parent.parent / "images"
FONTS = Path("C:/Windows/Fonts")

W, H = 1654, 2339          # A4 at 200 dpi
INK = (28, 28, 34)
GREY = (110, 110, 118)
LINE = (70, 70, 80)


def _font(name: str, size: int):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default()


SANS = lambda s: _font("arial.ttf", s)            # noqa: E731
SANS_B = lambda s: _font("arialbd.ttf", s)        # noqa: E731
MONO = lambda s: _font("cour.ttf", s)             # noqa: E731
MONO_B = lambda s: _font("courbd.ttf", s)         # noqa: E731


def _hero():
    d = generate_marine_data()
    claim = next(c for c in d["claims"] if c.claim_id == "MC-3107")
    shp = next(s for s in d["shipments"] if s.shipment_id == claim.shipment_id)
    cne = next(p for p in d["consignees"] if p.party_id == claim.consignee_id)
    shr = next(s for s in d["shippers"] if s.shipper_id == shp.shipper_id)
    return claim, shp, cne, shr


def _box(draw, xy, label=None, font=None):
    draw.rectangle(xy, outline=LINE, width=2)
    if label:
        draw.text((xy[0] + 10, xy[1] + 6), label, fill=GREY, font=font or SANS(20))


def _chop(img, center, text_top, text_mid):
    """Red company chop, pasted slightly rotated (as a scanned stamp would be)."""
    size = 300
    stamp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    red = (196, 38, 46, 205)
    sd.ellipse((10, 10, size - 10, size - 10), outline=red, width=8)
    sd.ellipse((34, 34, size - 34, size - 34), outline=red, width=3)
    for txt, y, f in ((text_top, 95, SANS_B(26)), (text_mid, 140, SANS_B(34)), ("SINGAPORE", 190, SANS_B(24))):
        w = sd.textlength(txt, font=f)
        sd.text(((size - w) / 2, y), txt, fill=red, font=f)
    stamp = stamp.rotate(-11, resample=Image.BICUBIC)
    img.paste(stamp, (center[0] - size // 2, center[1] - size // 2), stamp)


def _signature(d, origin, color=(30, 40, 110)):
    """Hand-drawn style signature scribble."""
    x, y = origin
    pts = [(x, y + 20), (x + 30, y - 10), (x + 55, y + 25), (x + 80, y - 5), (x + 110, y + 18),
           (x + 150, y - 12), (x + 175, y + 22), (x + 230, y + 2), (x + 290, y + 10)]
    d.line(pts, fill=color, width=4, joint="curve")
    d.line((x + 20, y + 34, x + 260, y + 28), fill=color, width=3)


def _scanify(img: Image.Image) -> Image.Image:
    """Make a clean render look like a desk scan: warm grey paper, grain, slight softness."""
    from PIL import ImageFilter
    paper = (236, 232, 222)
    noise = Image.merge("RGB", [Image.effect_noise(img.size, 40)] * 3)
    scanned = Image.blend(img, Image.new("RGB", img.size, paper), 0.16)
    scanned = Image.blend(scanned, noise, 0.07).filter(ImageFilter.GaussianBlur(0.8))
    return scanned.rotate(-0.3, resample=Image.BICUBIC, fillcolor=paper)


def render_invoice(claim, shp, cne, shr) -> Image.Image:
    img = Image.new("RGB", (W, H), (252, 252, 249))
    d = ImageDraw.Draw(img)

    d.text((110, 110), shr.name.upper(), fill=INK, font=SANS_B(46))
    d.text((110, 170), "10 Anson Road #18-07, International Plaza, Singapore 079903", fill=GREY, font=SANS(24))
    d.text((110, 204), "UEN 202534871K  ·  Tel +65 6221 4087  ·  accounts@orchidtradelinks.sg", fill=GREY, font=SANS(24))
    d.line((110, 260, W - 110, 260), fill=LINE, width=3)
    d.text((110, 290), "COMMERCIAL INVOICE & PACKING LIST", fill=INK, font=SANS_B(40))

    rows = [
        ("Invoice No.", shp.invoice_no), ("Invoice Date", "20 AUG 2026"),
        ("Terms", "FOB SINGAPORE (INCOTERMS 2020)"), ("Payment", "T/T 30 DAYS FROM B/L DATE"),
        ("Vessel / Voyage", f"{shp.vessel} {shp.voyage}"), ("B/L No.", shp.bl_number),
        ("Port of Loading", "SINGAPORE"), ("Port of Discharge", "MANILA (MICT), PHILIPPINES"),
    ]
    y = 370
    for i, (k, v) in enumerate(rows):
        x = 110 if i % 2 == 0 else 850
        d.text((x, y), k, fill=GREY, font=SANS(22))
        d.text((x, y + 28), v, fill=INK, font=SANS_B(26))
        if i % 2 == 1:
            y += 80

    _box(d, (110, y + 10, W - 110, y + 190), "BUYER / CONSIGNEE")
    d.text((130, y + 50), cne.name.upper(), fill=INK, font=SANS_B(28))
    d.text((130, y + 90), cne.registered_address, fill=INK, font=SANS(24))
    d.text((130, y + 124), "PHILIPPINES  ·  TIN 009-487-221-000", fill=INK, font=SANS(24))

    # Line-item table
    ty = y + 240
    cols = [110, 250, 900, 1110, 1290, W - 110]
    heads = ["Marks", "Description of Goods", "Quantity", "Unit Price", "Amount (USD)"]
    d.rectangle((110, ty, W - 110, ty + 56), fill=(234, 234, 238), outline=LINE, width=2)
    for i, h in enumerate(heads):
        d.text((cols[i] + 12, ty + 14), h, fill=INK, font=SANS_B(22))
    ry = ty + 56
    d.rectangle((110, ry, W - 110, ry + 260), outline=LINE, width=2)
    for x in cols[1:-1]:
        d.line((x, ty, x, ry + 260), fill=LINE, width=2)
    d.text((cols[0] + 12, ry + 20), "LPG/MNL\n1-108", fill=INK, font=SANS(22), spacing=8)
    desc = ("INSULATED GLASS UNITS, LOW-E\n6MM + 12A + 6MM, CLEAR/LOW-E\n"
            "ON 108 STEEL A-FRAME RACKS\nHS CODE 7008.00")
    d.text((cols[1] + 12, ry + 20), desc, fill=INK, font=SANS(22), spacing=10)

    # The invoice is internally consistent — the fraud only shows against the weighed VGM.
    d.text((cols[2] + 12, ry + 20), f"{int(shp.quantity):,} M2", fill=INK, font=SANS(24))
    d.text((cols[3] + 12, ry + 20), f"{shp.unit_price:,.2f}", fill=INK, font=SANS(24))
    d.text((cols[4] + 12, ry + 20), f"{shp.invoice_value:,.2f}", fill=INK, font=SANS(24))

    fy = ry + 280
    d.text((cols[3] - 60, fy), "TOTAL FOB SINGAPORE  USD", fill=INK, font=SANS_B(24))
    d.text((cols[4] + 12, fy + 36), f"{shp.invoice_value:,.2f}", fill=INK, font=SANS_B(28))
    d.text((110, fy + 40), "SAY US DOLLARS TWO HUNDRED FIFTY THOUSAND FIVE HUNDRED SIXTY ONLY", fill=INK, font=SANS(22))

    # Packing list block
    py = fy + 130
    d.text((110, py), "PACKING DETAILS", fill=INK, font=SANS_B(28))
    net = int(shp.quantity * 30)
    gross = shp.gross_weight_bl_kg
    d.text((110, py + 50), "Packages:  108 steel A-frame racks (18 per container)", fill=INK, font=SANS(24))
    d.text((110, py + 90), "Net weight:", fill=INK, font=SANS(24))
    d.text((110, py + 130), "Gross weight:", fill=INK, font=SANS(24))
    d.text((300, py + 90), f"{net:,} KGS", fill=INK, font=SANS(24))
    d.text((300, py + 130), f"{gross:,} KGS", fill=INK, font=SANS(24))
    d.text((110, py + 170), "Measurement:  6 x 20' GP", fill=INK, font=SANS(24))

    cy = py + 230
    d.rectangle((110, cy, W - 110, cy + 56), fill=(234, 234, 238), outline=LINE, width=2)
    for i, h in enumerate(["Container No.", "Seal No.", "Size", "Racks"]):
        d.text((130 + i * 360, cy + 14), h, fill=INK, font=SANS_B(22))
    for i, c in enumerate(shp.containers):
        yy = cy + 70 + i * 40
        for j, v in enumerate([c.container_no, c.seal_no_loading, c.size_type, "18"]):
            d.text((130 + j * 360, yy), v, fill=INK, font=SANS(22))

    sy = cy + 70 + len(shp.containers) * 40 + 60
    d.text((110, sy), "We certify this invoice is true and correct and the goods are of Singapore/ASEAN origin.",
           fill=INK, font=SANS(22))
    d.text((W - 620, sy + 90), f"For and on behalf of\n{shr.name}", fill=INK, font=SANS(24), spacing=8)
    d.line((W - 620, sy + 260, W - 200, sy + 260), fill=LINE, width=2)
    d.text((W - 620, sy + 270), "Authorised Signatory", fill=GREY, font=SANS(22))
    _signature(d, (W - 600, sy + 200))
    _chop(img, (W - 420, sy + 190), "ORCHID TRADE", "LINKS")
    return _scanify(img)


def render_bl(claim, shp, cne, shr) -> Image.Image:
    img = Image.new("RGB", (W, H), (250, 250, 246))
    d = ImageDraw.Draw(img)
    d.text((110, 100), "MERIDIAN CONTAINER LINE", fill=(16, 44, 92), font=SANS_B(52))
    d.text((110, 165), "BILL OF LADING FOR COMBINED TRANSPORT OR PORT TO PORT SHIPMENT", fill=INK, font=SANS_B(24))
    d.text((W - 470, 96), "B/L No.", fill=GREY, font=SANS(22))
    d.text((W - 470, 124), shp.bl_number, fill=INK, font=MONO_B(36))

    mid = W // 2
    boxes = [
        ((110, 230, mid, 420), "Shipper", f"{shr.name.upper()}\n10 ANSON ROAD #18-07\nSINGAPORE 079903"),
        ((110, 420, mid, 610), "Consignee",
         f"{cne.name.upper()}\n" + cne.registered_address.upper().replace(", 88 ", ",\n88 ")),
        ((110, 610, mid, 760), "Notify Party", "SAME AS CONSIGNEE"),
        ((mid, 230, W - 110, 420), "Forwarding Agent", "SWIFTLINK FREIGHT FORWARDING INC.\nMAKATI CITY, PHILIPPINES"),
        ((mid, 420, W - 110, 610), "Place of Receipt / Port of Loading", "SINGAPORE CY / SINGAPORE (PSA)"),
        ((mid, 610, W - 110, 760), "Port of Discharge / Place of Delivery", "MANILA (MICT) / MANILA CY"),
        ((110, 760, mid, 860), "Vessel / Voyage", f"{shp.vessel}  {shp.voyage}"),
        ((mid, 760, W - 110, 860), "Freight", "FREIGHT COLLECT"),
    ]
    for xy, label, text in boxes:
        _box(d, xy, label)
        d.multiline_text((xy[0] + 14, xy[1] + 40), text, fill=INK, font=MONO(24), spacing=8)

    ty = 890
    d.rectangle((110, ty, W - 110, ty + 50), fill=(232, 234, 240), outline=LINE, width=2)
    for x, h in ((130, "Container / Seal No."), (560, "No. & Kind of Packages — Description of Goods"),
                 (1300, "Gross Weight")):
        d.text((x, ty + 12), h, fill=INK, font=SANS_B(22))
    d.rectangle((110, ty + 50, W - 110, ty + 820), outline=LINE, width=2)
    for i, c in enumerate(shp.containers):
        d.text((130, ty + 80 + i * 44), f"{c.container_no} / {c.seal_no_loading}", fill=INK, font=MONO(24))
    desc = ("6 X 20' GP CONTAINERS\nSHIPPER'S LOAD, STOW AND COUNT\nSAID TO CONTAIN:\n"
            "108 STEEL A-FRAME RACKS\nINSULATED GLASS UNITS LOW-E\n6MM+12A+6MM\n"
            "FRAGILE - HANDLE WITH CARE\n\nSHIPPED ON BOARD\n24 AUG 2026\nSINGAPORE")
    d.multiline_text((560, ty + 80), desc, fill=INK, font=MONO(24), spacing=10)
    d.text((1300, ty + 80), f"{shp.gross_weight_bl_kg:,}.000 KGS", fill=INK, font=MONO(24))
    d.text((1300, ty + 124), "(SHIPPER'S WEIGHT)", fill=INK, font=MONO(20))

    fy = ty + 860
    d.multiline_text((110, fy), ("RECEIVED by the Carrier the Goods as specified above in apparent good order and condition\n"
                                 "unless otherwise stated, weight, measure, marks, numbers, quality, contents and value unknown."),
                     fill=GREY, font=SANS(20), spacing=6)
    _box(d, (110, fy + 90, mid, fy + 200), "Number of Original B/Ls")
    d.text((130, fy + 135), "THREE (3)", fill=INK, font=MONO(26))
    _box(d, (mid, fy + 90, W - 110, fy + 200), "Place and Date of Issue")
    d.text((mid + 20, fy + 135), "SINGAPORE  24 AUG 2026", fill=INK, font=MONO(26))
    d.text((mid + 20, fy + 260), "Signed for MERIDIAN CONTAINER LINE\nas Carrier", fill=INK, font=SANS(24), spacing=8)
    _signature(d, (mid + 60, fy + 350))
    d.line((mid + 20, fy + 400, W - 160, fy + 400), fill=LINE, width=2)
    d.text((mid + 20, fy + 410), "As Agent for the Carrier, Meridian Container Line", fill=GREY, font=SANS(20))
    return _scanify(img)


def main():
    IMAGES.mkdir(exist_ok=True)
    claim, shp, cne, shr = _hero()
    render_invoice(claim, shp, cne, shr).save(IMAGES / "mc3107.png", optimize=True)
    render_bl(claim, shp, cne, shr).save(IMAGES / "mc3107_1.png", optimize=True)
    print(f"Wrote {IMAGES / 'mc3107.png'} and {IMAGES / 'mc3107_1.png'}")
    missing = [n for n in ("mc3107_2.png", "mc2988.png") if not (IMAGES / n).exists()]
    if missing:
        print(f"Still needed (real survey photos): {', '.join(missing)}")


if __name__ == "__main__":
    main()
