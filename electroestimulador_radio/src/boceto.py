"""Boceto 2D de la carcasa tipo radio: frente, trasera e interior en planta. Uso: python -P boceto.py <salida.png>"""
import sys, math, pathlib
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from params import *

S = 3.2
try:
    F = ImageFont.truetype("arial.ttf", 22); Fs = ImageFont.truetype("arial.ttf", 16); Fb = ImageFont.truetype("arialbd.ttf", 24)
except OSError:
    F = Fs = Fb = ImageFont.load_default()
CUERPO, MARCO, CREMA, METAL, OSCURO = "#3a2a20", "#c9c9c9", "#efe3c2", "#9a9a9a", "#1c1c1c"
W, D, H = caja

def vista_frontal():
    im = Image.new("RGB", (int(W * S + 80), int((H + asa_alto) * S + 110)), "white"); d = ImageDraw.Draw(im)
    ox, oz = 40, int((H + asa_alto) * S + 60)
    P = lambda x, z: (ox + x * S, oz - z * S)
    def R(x0, x1, z0, z1, **k): d.rounded_rectangle([P(x0, z1), P(x1, z0)], **k)
    # asa
    d.rounded_rectangle([P(30, H + asa_alto), P(W - 30, H - 4)], radius=int(10 * S), outline=METAL, width=int(4 * S))
    # cuerpo
    R(0, W, 0, H, radius=int(r_esquinas * S), fill=CUERPO, outline="black", width=3)
    R(4, W - 4, 4, H - 4, radius=int((r_esquinas - 3) * S), outline=METAL, width=4)
    # rejilla de altavoz (ranuras horizontales)
    x0, x1, z0, z1 = rejilla
    R(x0, x1, z0, z1, radius=12, fill=MARCO, outline="black", width=2)
    z = z0 + 5
    while z < z1 - 4:
        R(x0 + 6, x1 - 6, z, z + 2.6, radius=4, fill=OSCURO); z += 5.2
    # dial
    x0, x1, z0, z1 = dial
    R(x0, x1, z0, z1, radius=8, fill=CREMA, outline="black", width=2)
    for i in range(23):
        x = x0 + 8 + i * (x1 - x0 - 16) / 22
        d.line([P(x, z0 + 4), P(x, z0 + (11 if i % 5 == 0 else 8))], fill="black", width=2)
    d.line([P(x0 + 60, z0 + 2), P(x0 + 60, z1 - 2)], fill="#c0201c", width=4)
    d.text(P(x0 + 6, z1 - 3), "  1   2   3   4   5   6   7   8   9", fill="black", font=Fs)
    # mandos
    for i, zc in enumerate(mandos_z):
        cx, cz = P(mandos_x, zc); r = perilla_d / 2 * S
        d.ellipse([cx - r - 7, cz - r - 7, cx + r + 7, cz + r + 7], outline=METAL, width=3)          # aro de escala
        for k in range(11):
            a = math.radians(225 - k * 27)
            d.line([cx + (r + 9) * math.cos(a), cz - (r + 9) * math.sin(a), cx + (r + 15) * math.cos(a), cz - (r + 15) * math.sin(a)], fill=CREMA, width=2)
        d.ellipse([cx - r, cz - r, cx + r, cz + r], fill=METAL, outline="black", width=2)
        d.ellipse([cx - r * 0.75, cz - r * 0.75, cx + r * 0.75, cz + r * 0.75], fill="#d8d8d8", outline="#666")
        d.line([cx, cz, cx, cz - r * 0.75], fill="black", width=4)
        d.text((cx + r + 20, cz - 10), f"P{i + 1}", fill="black", font=F)
    for x in (25, W - 25):
        d.rectangle([P(x - 8, 0), P(x + 8, -3)], fill="black")                                        # patas
    d.text((10, 8), "FRENTE: rejilla y dial decorativos + 3 mandos", fill="black", font=F)
    return im

def vista_trasera():
    im = Image.new("RGB", (int(W * S + 80), int(H * S + 110)), "white"); d = ImageDraw.Draw(im)
    ox, oz = 40, int(H * S + 60)
    P = lambda x, z: (ox + x * S, oz - z * S)
    d.rounded_rectangle([P(0, H), P(W, 0)], radius=int(r_esquinas * S), fill=CUERPO, outline="black", width=3)
    d.rounded_rectangle([P(6, H - 6), P(W - 6, 6)], radius=int(6 * S), fill="#4a382c", outline=METAL, width=3)   # tapa trasera
    for x, z in ((14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)):
        cx, cz = P(x, z); d.ellipse([cx - 9, cz - 9, cx + 9, cz + 9], fill=METAL, outline="black")                # tornillos
    for i in range(6):                                                                                            # ranuras de ventilación
        d.rounded_rectangle([P(60 + i * 14, 95), P(66 + i * 14, 70)], radius=8, fill=OSCURO)
    # conectores (vista trasera: el lado de los mandos queda a la izquierda)
    for (x, z, dd, txt) in ((40, 40, jack_alim_d, "ALIMENTACIÓN"), (80, 40, salida_senal_d, "SEÑAL (muestra)")):
        cx, cz = P(x, z); r = dd / 2 * S
        d.ellipse([cx - r - 8, cz - r - 8, cx + r + 8, cz + r + 8], fill=METAL, outline="black")
        d.ellipse([cx - r, cz - r, cx + r, cz + r], fill=OSCURO)
        d.text((cx - 50, cz + r + 14), txt, fill="white", font=Fs)
    d.text((10, 8), "TRASERA: tapa atornillada + conectores", fill="black", font=F)
    return im

def vista_interior():
    im = Image.new("RGB", (int(W * S + 80), int(D * S + 210)), "white"); d = ImageDraw.Draw(im)
    ox, oy = 40, 130
    P = lambda x, y: (ox + x * S, oy + y * S)                       # planta: frente arriba
    d.rounded_rectangle([P(0, 0), P(W, D)], radius=int(r_esquinas * S), fill="#f3ece6", outline=CUERPO, width=int(pared * S))
    # potenciómetros: casquillo en la pared delantera, cuerpo dentro
    for zc in mandos_z[:1]:
        pass
    for i, xo in enumerate((-22, 0, 22)):         # en planta se ven superpuestos: se dibujan separados para leerlos
        x = mandos_x + xo
        d.rectangle([P(x - perilla_d / 2, -perilla_h), P(x + perilla_d / 2, 0)], fill=METAL, outline="black")               # perilla fuera
        d.rectangle([P(x - pot_cuerpo_d / 2, pared + 2), P(x + pot_cuerpo_d / 2, pared + 2 + pot_cuerpo_l)], fill="#2f6db3", outline="black")
        d.rectangle([P(x - 6, pared + 2 + pot_cuerpo_l), P(x + 6, pared + 2 + pot_cuerpo_l + 4)], fill="#d9b13b")           # patas soldadas
        # cables con bucle de reserva hasta la protoboard
        d.line([P(x, pared + 16), P(x, 38), P(118 - i * 6, 48), P(118 - i * 6, 52)], fill=["#d22", "#2a2", "#22d"][i], width=3)
    # brida de sujeción de cables (abrazadera impresa) cerca de los potenciómetros
    d.rectangle([P(135, 34), P(185, 41)], fill="#888", outline="black"); d.text(P(136, 42), "abrazadera de cables", fill="black", font=Fs)
    # protoboard
    px0, py0 = 20, D - pared - 4 - proto[1]
    d.rectangle([P(px0, py0), P(px0 + proto[0], py0 + proto[1])], fill="#f2e3a0", outline="#8a7420", width=3)
    d.text(P(px0 + 8, py0 + 22), "mini protoboard 83x56", fill="#5a4a10", font=Fs)
    d.rectangle([P(px0 + proto[0] + 4, py0 + 10), P(px0 + proto[0] + 10, py0 + 40)], fill="#888")                # anclaje de cables
    # conectores traseros
    for x in (W - 40, W - 80):
        d.rectangle([P(x - 6, D - pared - 12), P(x + 6, D)], fill=METAL, outline="black")
    d.text((10, 8), "INTERIOR en planta (los 3 mandos van en columna; aqui se dibujan separados)", fill="black", font=F)
    return im

ims = [vista_frontal(), vista_trasera(), vista_interior()]
Wt = max(i.width for i in ims); Ht = sum(i.height for i in ims)
hoja = Image.new("RGB", (Wt, Ht), "white"); y = 0
for i in ims: hoja.paste(i, (0, y)); y += i.height
hoja.save(sys.argv[1])
