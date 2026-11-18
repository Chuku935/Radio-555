"""blender -b --factory-startup -P blender_render.py -- <dir_ensamblaje> <dir_blender> <dir_docs>  (rutas absolutas)"""
import bpy, sys, pathlib
from mathutils import Vector
ASM, BL, DOCS = (pathlib.Path(a) for a in sys.argv[sys.argv.index('--') + 1:])
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
COL = {'Radio_caja': (0.16, 0.09, 0.06), 'Radio_tapa': (0.24, 0.15, 0.10), 'Potenciometros_ref': (0.1, 0.3, 0.75),
       'Perillas_ref': (0.75, 0.75, 0.78), 'Protoboard_ref': (0.95, 0.88, 0.5)}
O = {}
for n, rgb in COL.items():
    bpy.ops.wm.stl_import(filepath=str(ASM / f'{n}.stl'))
    o = bpy.context.selected_objects[0]; o.name = n
    m = bpy.data.materials.new('M_' + n); m.diffuse_color = (*rgb, 1); o.data.materials.append(m); O[n] = o
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_cavity = True; sh.cavity_type = 'BOTH'; sh.show_shadows = True; sh.show_object_outline = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 50; cam.data.clip_end = 5000
def ver(loc, tgt, fn, ocultar=(), desp=None):
    for n in ocultar: O[n].hide_render = True
    for n, d in (desp or {}).items(): O[n].location = Vector(d)
    cam.location = Vector(loc); cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = str(DOCS / fn); bpy.ops.render.render(write_still=True)
    for n in ocultar: O[n].hide_render = False
    for n in (desp or {}): O[n].location = Vector((0, 0, 0))
C = (90, 36, 55)
ver((90, -420, 60), C, 'render_frente.png')
ver((-150, -360, 190), C, 'render_tres_cuartos.png')
ver((330, 400, 190), C, 'render_trasera.png')
ver((230, 380, 200), (95, 20, 50), 'render_interior.png', ocultar=['Radio_tapa'])
ver((215, 150, 95), (140, 15, 52), 'render_potenciometros.png', ocultar=['Radio_tapa', 'Protoboard_ref'])
ver((0, -170, 190), (90, 66, 45), 'render_tapa_interior.png', ocultar=['Radio_caja', 'Potenciometros_ref', 'Perillas_ref'])
ver((-260, -430, 260), (90, 60, 50), 'render_explosionado.png',
    desp={'Radio_tapa': (0, 110, 0), 'Perillas_ref': (0, -45, 0), 'Potenciometros_ref': (0, 45, 0), 'Protoboard_ref': (0, 60, 0)})
bpy.ops.wm.save_as_mainfile(filepath=str(BL / 'Radio_electroestimulador.blend'))
