"""Electroestimulador con forma de radio antigua: parámetros (mm). TODO A PRESIÓN, sin tornillos.
Ejes: X = ancho (izquierda -> derecha mirando el frente), Y = fondo (0 = cara delantera), Z = alto (0 = base de la caja).
Lo marcado  # A VERIFICAR  es un valor típico que conviene medir en la pieza real.
"""
# ---------------------------------------------------------------- holguras
h_bolsillo, h_pasante, h_encaje = 0.4, 0.2, 0.3

# ---------------------------------------------------------------- caja
W, D, H = 180.0, 72.0, 105.0     # ancho x fondo x alto (exterior, sin asa ni patas)
pared = 2.6                      # todas las paredes, también el frente
r_esquinas = 10.0
tapa_e = 2.4                     # placa de la tapa trasera
# asa de radio (en el plano del frente, para imprimir sin soportes)
asa_x = (42.0, 138.0); asa_alto = 17.0; asa_barra = 6.0; asa_fondo = 10.0
# patas
pata_x = (24.0, 156.0); pata_ancho = 14.0; pata_alto = 2.0

# ---------------------------------------------------------------- decoración del frente (grabada 1.0 mm, para pintar)
grabado = 1.0
rejilla = (12.0, 110.0, 12.0, 66.0)     # x0, x1, z0, z1  (ranuras ciegas: la caja queda cerrada)
rejilla_columnas, rejilla_ranura, rejilla_paso = 3, 2.4, 5.0
dial = (12.0, 110.0, 74.0, 95.0)

# ---------------------------------------------------------------- potenciómetros WH148 B50K (genéricos de 16 mm)
pot_x = 148.0
pot_z = (22.0, 52.0, 82.0)       # 3 mandos en columna
pot_eje_d = 5.9                  # medido (perilla.py)
pot_eje_L = 15.0                 # de la cara de apoyo (metal) a la punta del eje: confirmado, 15 mm
pot_rosca_d, pot_rosca_l = 7.0, 7.0   # casquillo M7x0.75                                  # A VERIFICAR
pot_cuerpo_d, pot_cuerpo_l = 17.0, 9.5                                                    # A VERIFICAR
pot_teton_r, pot_teton = 7.8, (2.8, 1.2, 3.0)   # tetón antigiro: radio, (ancho, grueso, alto)   # A VERIFICAR
pot_terminales = (12.0, 9.0)     # lengüeta de los 3 terminales: ancho, cuánto baja del cuerpo
# sujeción a presión: torreta + 3 patillas elásticas
torreta_r = 8.3
patilla_ang = (90.0, 205.0, 335.0)   # los terminales quedan hacia abajo (270°), libres
patilla_ancho, patilla_e, patilla_gancho = 6.0, 1.8, 0.9
ranura_teton_ang = (0.0, 180.0)      # ranuras para el tetón, a los dos lados

# ---------------------------------------------------------------- cubre eje (perilla_extensor/perilla.py)
perilla_agujero_d = 7.9          # agujero de la pared para el casquillo de la perilla
perilla_casq_d, perilla_casq_l = 7.4, 4.0
perilla_falda_d, perilla_cuerpo_d, perilla_alto, perilla_sep = 15.7, 10.6, 12.0, 0.8

# ---------------------------------------------------------------- protoboard pequeña
proto = (83.0, 56.4, 31.0)
proto_x0, proto_y0 = 10.0, 6.4

# ---------------------------------------------------------------- tapa trasera a presión y paso de cables
faldon_l, faldon_e = 6.0, 1.6    # faldón de la tapa que entra en la caja
cordon_h = 0.7                   # cordón de enganche (0.4 mm de agarre real)
cordones_x = (45.0, 135.0); cordon_largo = 30.0
# VCC, GND y muestra de señal: 3 ranuras abiertas en el borde inferior de la tapa
puerto_x = (100.0, 104.5, 109.0)
puerto_ancho = 1.7               # cable Dupont de ~1.4 mm                                 # A VERIFICAR
puerto_alto = 1.3                # la tapa pellizca el cable contra el suelo (0.1 mm)

# guía de los cables de los potenciómetros (horquilla)
horquilla_x, horquilla_z, horquilla_hueco, horquilla_l = 124.0, (30.0, 76.0), 3.0, 22.0

cama = (220.0, 220.0, 240.0)
