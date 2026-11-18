"""Electroestimulador-radio: caja y tapa trasera a presión (sin tornillos) + comprobaciones.
Uso: python -P modelo.py <dir_stl> <dir_ensamblaje> <informe.json>"""
import sys, math, json, struct, pathlib
import numpy as np
import manifold3d as m3
from manifold3d import Manifold as M, CrossSection as CS
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from params import *

m3.set_circular_segments(72)
OUT, ASM, REP = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True); ASM.mkdir(parents=True, exist_ok=True)
U = m3.OpType.Add

# ---------------------------------------------------------------- utilidades
def box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
def rrect(x0, x1, y0, y1, r):
    r = max(r, 0.01)
    return CS.square([x1 - x0 - 2 * r, y1 - y0 - 2 * r]).translate([x0 + r, y0 + r]).offset(r, m3.JoinType.Round)
def rect(x0, x1, y0, y1): return CS.square([x1 - x0, y1 - y0]).translate([x0, y0])
def union(lst): return M.batch_boolean(lst, U)
def cunion(lst): return CS.batch_boolean(lst, U)
def prismY(cs_xz, y0, y1):
    """Sección dibujada en (x, z) extruida a lo largo de Y."""
    return cs_xz.extrude(y1 - y0).rotate([90, 0, 0]).translate([0, y1, 0])
def prismX(cs_yz, x0, x1):
    """Sección dibujada en (y, z) extruida a lo largo de X."""
    return cs_yz.extrude(x1 - x0).transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))
def cylY(r0, y0, y1, x, z, r1=None):
    """Cilindro/cono con eje Y: radio r0 en y0 y r1 en y1."""
    r1 = r0 if r1 is None else r1
    return M.cylinder(y1 - y0, r1, r0).rotate([90, 0, 0]).translate([x, y1, z])
def sector(r_in, r_out, ang, ancho):
    """Trozo de anillo de 'ancho' mm centrado en el ángulo 'ang' (grados, 0 = +X, 90 = arriba)."""
    return ((CS.circle(r_out) - CS.circle(r_in)) ^ rect(0, r_out + 1, -ancho / 2, ancho / 2).rotate(ang))
def save_stl(man, fn):
    mesh = man.to_mesh(); V = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64); F = np.asarray(mesh.tri_verts)
    tri = V[F]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30
    rec = np.zeros(len(F), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]); rec['n'] = n; rec['v'] = tri
    with open(fn, 'wb') as f:
        f.write(b'Radio electroestimulador'.ljust(80, b' ')); f.write(struct.pack('<I', len(F))); f.write(rec.tobytes())
def a_cama(man):
    b = man.bounding_box(); return man.translate([-(b[0] + b[3]) / 2, -(b[1] + b[4]) / 2, -b[2]])

y_tapa = D - tapa_e                      # cara interior de la placa de la tapa = borde trasero de la caja
L = pot_eje_L                            # la punta del eje queda al ras de la cara delantera (y = 0)
contorno = rrect(0, W, 0, H, r_esquinas)
patas_cs = cunion([rect(x - pata_ancho / 2, x + pata_ancho / 2, -pata_alto, 1.0) for x in pata_x])

# ---------------------------------------------------------------- CAJA
cuerpo = prismY(contorno, 0, y_tapa) - prismY(contorno.offset(-pared, m3.JoinType.Round), pared, D)
asa_cs = (rrect(asa_x[0], asa_x[1], H - 12, H + asa_alto, 9.0)
          - rrect(asa_x[0] + asa_barra, asa_x[1] - asa_barra, H - 12, H + asa_alto - asa_barra, 4.0)) ^ rect(0, W, H - 0.5, H + 50)
partes = [cuerpo, prismY(asa_cs, 0, asa_fondo), prismY(patas_cs, 0, y_tapa)]
r_pat = pot_cuerpo_d / 2 + 0.4
y_g0 = L + pot_cuerpo_l + 0.3            # donde empieza el gancho (0.3 de juego tras el cuerpo)
y_g1 = y_g0 + patilla_gancho; y_g2 = y_g1 + 1.6
cortes = []
for pz in pot_z:
    c = lambda cs: cs.translate([pot_x, pz])
    partes.append(prismY(c(CS.circle(torreta_r)), pared - 0.01, L))                        # torreta: apoyo de la cara del potenciómetro
    for a in patilla_ang:                                                                 # 3 patillas elásticas desde la pared delantera
        pat = prismY(c(sector(r_pat, r_pat + patilla_e, a, patilla_ancho)), pared - 0.01, y_g2)
        gan = prismY(c(sector(r_pat - patilla_gancho, r_pat + 0.01, a, patilla_ancho)), y_g0, y_g2)
        gan = gan - cylY(r_pat, y_g0 - 0.01, y_g1, pot_x, pz, r_pat - patilla_gancho) \
                  - cylY(r_pat - patilla_gancho, y_g1 - 0.001, y_g2 + 0.01, pot_x, pz, r_pat + 0.25)
        partes += [pat, gan]
    # agujero: Ø7.9 para el casquillo de la perilla y Ø7.4 para la rosca del potenciómetro
    cortes += [cylY(perilla_agujero_d / 2, -1, perilla_casq_l + 2, pot_x, pz),
               cylY(perilla_agujero_d / 2, perilla_casq_l + 2 - 0.01, perilla_casq_l + 2.25, pot_x, pz, pot_rosca_d / 2 + h_pasante),
               cylY(pot_rosca_d / 2 + h_pasante, perilla_casq_l + 2, L + 1, pot_x, pz)]
    for a in ranura_teton_ang:                                                            # ranuras del tetón antigiro
        cortes.append(prismY(c(rect(pot_teton_r - 1.2, torreta_r + 1, -pot_teton[0] / 2 - 0.3, pot_teton[0] / 2 + 0.3).rotate(a)),
                             L - pot_teton[2] - 0.5, L + 0.1))
# horquilla para los cables de los potenciómetros (2 aletas con labio a 45°)
hx, hh = horquilla_x, horquilla_hueco / 2
for s in (-1, 1):
    x_in = hx + s * hh
    partes.append(box(x_in, x_in + s * 1.6, pared - 0.01, pared + horquilla_l, horquilla_z[0], horquilla_z[1]))
    labio = CS([[(0, 0), (0.6, 0.6), (0.6, 1.4), (0, 2.6)]] if s < 0 else [[(0, 0), (0, 2.6), (-0.6, 1.4), (-0.6, 0.6)]])
    # sección en (x, y) del labio, extruida en Z
    partes.append(labio.extrude(horquilla_z[1] - horquilla_z[0]).translate([x_in, pared + horquilla_l - 2.6, horquilla_z[0]]))
# protoboard: 2 guías laterales + tope delantero (el tope trasero y el de arriba van en la tapa)
px0, px1 = proto_x0 - h_bolsillo, proto_x0 + proto[0] + h_bolsillo
partes += [box(px0 - 1.6, px0, pared - 0.01, 42, pared - 0.01, pared + 6), box(px1, px1 + 1.6, pared - 0.01, 42, pared - 0.01, pared + 6),
           box(proto_x0 + 12, proto_x0 + proto[0] - 12, pared - 0.01, proto_y0 - h_bolsillo, pared - 0.01, pared + 5)]
caja = union(partes) - union(cortes)
# ranuras en V para los cordones de la tapa
y_c = y_tapa - 3.5
def v_yz(z_pared, sentido, base, alto):       # triángulo en (y, z): base sobre la pared, vértice hacia 'sentido'
    return CS([[(y_c - base / 2, z_pared), (y_c + base / 2, z_pared), (y_c, z_pared + sentido * alto)]][::1], m3.FillRule.NonZero)
def v_xy(x_pared, sentido, base, alto):       # triángulo en (x, y)
    return CS([[(x_pared, y_c - base / 2), (x_pared, y_c + base / 2), (x_pared + sentido * alto, y_c)]], m3.FillRule.NonZero)
gr = []
for x in cordones_x:
    gr += [prismX(v_yz(H - pared, +1, 1.0, 0.5), x - cordon_largo / 2 - 1, x + cordon_largo / 2 + 1),
           prismX(v_yz(pared, -1, 1.0, 0.5), x - cordon_largo / 2 - 1, x + cordon_largo / 2 + 1)]
zc0, zc1 = H / 2 - cordon_largo / 2, H / 2 + cordon_largo / 2
gr += [v_xy(pared, -1, 1.0, 0.5).extrude(cordon_largo + 2).translate([0, 0, zc0 - 1]),
       v_xy(W - pared, +1, 1.0, 0.5).extrude(cordon_largo + 2).translate([0, 0, zc0 - 1])]
caja = caja - union(gr)
# decoración grabada en el frente
dec = []
x0, x1, z0, z1 = rejilla
wc = (x1 - x0 - (rejilla_columnas - 1) * 4.0) / rejilla_columnas
for i in range(rejilla_columnas):
    cx0 = x0 + i * (wc + 4.0); z = z0 + 1.0
    while z + rejilla_ranura <= z1 - 1.0:
        dec.append(rrect(cx0, cx0 + wc, z, z + rejilla_ranura, 1.0)); z += rejilla_paso
dx0, dx1, dz0, dz1 = dial
dec.append(rrect(dx0, dx1, dz0, dz1, 3.0) - rrect(dx0 + 1.2, dx1 - 1.2, dz0 + 1.2, dz1 - 1.2, 1.8))      # marco del dial
for i in range(25):
    x = dx0 + 7 + i * (dx1 - dx0 - 14) / 24
    dec.append(rect(x - 0.5, x + 0.5, dz0 + 4, dz0 + (11 if i % 4 == 0 else 8)))
dec.append(rect(dx0 + 5, dx1 - 5, dz1 - 6.5, dz1 - 5.5))
for pz in pot_z:                                                                                          # escala de cada mando
    for k in range(11):
        a = 225 - k * 27
        dec.append(rect(perilla_falda_d / 2 + 2.2, perilla_falda_d / 2 + (5.4 if k % 5 == 0 else 4.2), -0.5, 0.5).rotate(a).translate([pot_x, pz]))
caja = caja - prismY(cunion(dec), -1, grabado)

# ---------------------------------------------------------------- TAPA TRASERA
of = pared + h_encaje
faldon_cs = contorno.offset(-of, m3.JoinType.Round) - contorno.offset(-of - faldon_e, m3.JoinType.Round)
tp = [prismY(cunion([contorno, patas_cs]), y_tapa, D), prismY(faldon_cs, y_tapa - faldon_l, y_tapa + 0.01)]
for x in cordones_x:                                                    # cordones de enganche (arriba, abajo y laterales)
    tp += [prismX(v_yz(H - of - 0.01, +1, 1.4, cordon_h), x - cordon_largo / 2, x + cordon_largo / 2),
           prismX(v_yz(of + 0.01, -1, 1.4, cordon_h), x - cordon_largo / 2, x + cordon_largo / 2)]
tp += [v_xy(of + 0.01, -1, 1.4, cordon_h).extrude(cordon_largo).translate([0, 0, zc0]),
       v_xy(W - of - 0.01, +1, 1.4, cordon_h).extrude(cordon_largo).translate([0, 0, zc0])]
y_pr = proto_y0 + proto[1]                                              # borde trasero de la protoboard
for x in (proto_x0 + 18, proto_x0 + proto[0] - 18):                     # topes traseros de la protoboard
    tp.append(box(x - 3, x + 3, y_pr + h_encaje, y_tapa + 0.01, of + faldon_e - 0.01, pared + 16))
tp.append(box(proto_x0 + proto[0] / 2 - 4, proto_x0 + proto[0] / 2 + 4, y_pr - 12, y_tapa + 0.01,
              pared + proto[2] + 0.5, pared + proto[2] + 3.5))        # dedo que impide que la protoboard se levante
tapa = union(tp)
ct = []
for x in puerto_x:                                                      # 3 ranuras: VCC, GND y señal
    ct += [box(x - puerto_ancho / 2, x + puerto_ancho / 2, y_tapa - 0.01, D + 1, -pata_alto - 1, pared + puerto_alto),
           box(x - puerto_ancho / 2, x + puerto_ancho / 2, y_tapa - faldon_l - 1, y_tapa + 0.01, -1, of + faldon_e + 0.5)]
ct.append(box(W / 2 - 10, W / 2 + 10, y_tapa - 0.1, D - 1.2, H - 3.0, H + 1))      # uña para abrir la tapa
sim = [rect(puerto_x[0] - 1.6, puerto_x[0] + 1.6, 10.6, 11.4), rect(puerto_x[0] - 0.4, puerto_x[0] + 0.4, 9.4, 12.6),          # +
       rect(puerto_x[1] - 1.6, puerto_x[1] + 1.6, 10.6, 11.4),                                                                # -
       rect(puerto_x[2] - 1.8, puerto_x[2] - 0.6, 9.6, 10.4), rect(puerto_x[2] - 1.0, puerto_x[2] - 0.2, 9.6, 12.6),          # pulso
       rect(puerto_x[2] - 1.0, puerto_x[2] + 1.0, 11.8, 12.6), rect(puerto_x[2] + 0.2, puerto_x[2] + 1.0, 9.6, 12.6),
       rect(puerto_x[2] + 0.6, puerto_x[2] + 1.8, 9.6, 10.4)]
ct.append(prismY(cunion(sim), D - 0.6, D + 1))
tapa = tapa - union(ct)

# ---------------------------------------------------------------- REFERENCIAS
pots, perillas = [], []
for pz in pot_z:
    p = [cylY(pot_eje_d / 2, 0, L - pot_rosca_l, pot_x, pz), cylY(pot_rosca_d / 2, L - pot_rosca_l - 0.01, L, pot_x, pz),
         cylY(pot_cuerpo_d / 2, L, L + pot_cuerpo_l, pot_x, pz),
         box(pot_x - pot_teton_r - pot_teton[1] / 2, pot_x - pot_teton_r + pot_teton[1] / 2, L - pot_teton[2], L + 0.01,
             pz - pot_teton[0] / 2, pz + pot_teton[0] / 2),
         box(pot_x - pot_terminales[0] / 2, pot_x + pot_terminales[0] / 2, L + 0.5, L + 2.5,
             pz - pot_cuerpo_d / 2 - pot_terminales[1], pz - pot_cuerpo_d / 2 + 2)]
    pots.append(union(p))
    k = [cylY(perilla_casq_d / 2, 0, perilla_casq_l, pot_x, pz) - cylY(pot_eje_d / 2 + 0.15, -1, perilla_casq_l + 1, pot_x, pz),
         cylY(perilla_falda_d / 2, -perilla_sep - 1.5, -perilla_sep, pot_x, pz),
         cylY(perilla_cuerpo_d / 2, -perilla_sep - perilla_alto, -perilla_sep, pot_x, pz)]
    perillas.append(union(k))
pots, perillas = union(pots), union(perillas)
protob = box(proto_x0, proto_x0 + proto[0], proto_y0, y_pr, pared, pared + proto[2])

PIEZAS = dict(Radio_caja=caja, Radio_tapa=tapa)
REFS = dict(Potenciometros_ref=pots, Perillas_ref=perillas, Protoboard_ref=protob)

# ---------------------------------------------------------------- COMPROBACIONES
res = {}
todos = {**PIEZAS, **REFS}; nombres = list(todos)
previstos = {('Radio_caja', 'Radio_tapa')}                    # cordones de enganche dentro de sus ranuras
choques, contactos = {}, {}
for i, a_ in enumerate(nombres):
    for b_ in nombres[i + 1:]:
        v = (todos[a_] ^ todos[b_]).volume()
        if v > 1e-3 and (a_, b_) != ('Potenciometros_ref', 'Perillas_ref'):
            (contactos if (a_, b_) in previstos else choques)[f'{a_} x {b_}'] = round(v, 3)
res['interferencias_mm3'] = choques or 'ninguna'
res['contactos_previstos_mm3'] = contactos
res['agarre_cordon_mm'] = round(cordon_h - h_encaje, 2)
res['perilla_vs_caja_mm'] = round(perillas.min_gap(caja, 5.0), 2)
res['proto_vs_potenciometros_mm'] = round(protob.min_gap(pots, 80.0), 1)
res['proto_vs_tapa_mm'] = round(protob.min_gap(tapa, 10.0), 2)
tens = 1.5 * patilla_e * patilla_gancho / (y_g0 - pared) ** 2
res['patilla'] = dict(largo=round(y_g0 - pared, 1), flecha=patilla_gancho, deformacion_pct=round(100 * tens, 2))
def voladizos(man):
    mesh = man.to_mesh(); V = np.asarray(mesh.vert_properties)[:, :3]; F = np.asarray(mesh.tri_verts); T = V[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); A = np.linalg.norm(n, axis=1) / 2; n /= (2 * A[:, None] + 1e-30)
    zmin = T[:, :, 2].min(axis=1)
    m = (n[:, 2] < -math.cos(math.radians(45)) - 2e-3) & (zmin > 0.05)
    plano = m & (n[:, 2] < -0.999)
    zs = {}
    for z, ar in zip(np.round(zmin[plano], 1), A[plano]): zs[float(z)] = zs.get(float(z), 0) + float(ar)
    return dict(area_voladizo_mm2=round(float(A[m].sum()), 1), puentes_mm2_por_altura={k: round(v, 1) for k, v in sorted(zs.items())})
ORIENT = dict(Radio_caja=[90, 0, 0], Radio_tapa=[-90, 0, 0])      # caja: frente sobre la cama; tapa: cara exterior sobre la cama
fab = {}
for n, p in PIEZAS.items():
    q = a_cama(p.rotate(ORIENT[n]))
    b = q.bounding_box(); dims = [round(b[3] - b[0], 1), round(b[4] - b[1], 1), round(b[5] - b[2], 1)]
    fab[n] = dict(medidas=dims, cabe_en_cama=dims[0] <= cama[0] and dims[1] <= cama[1] and dims[2] <= cama[2],
                  volumen_cm3=round(q.volume() / 1000, 1), manifold=q.status() == m3.Error.NoError, cuerpos=len(q.decompose()),
                  **voladizos(q))
    save_stl(q, OUT / f'{n}.stl')
res['fabricacion'] = fab
for n, p in todos.items(): save_stl(p, ASM / f'{n}.stl')
json.dump(res, open(REP, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
