# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_connect_loop

import bmesh
import bpy
from mathutils import kdtree
from bpy.props import BoolProperty
from bpy.types import Operator, Panel, Scene
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "Connect Loop",
    "description": "Connects selected vertices by shortest loop",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 1),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > Connect Loop",
    "doc_url": "https://github.com/Korchy/1d_connect_loop",
    "tracker_url": "https://github.com/Korchy/1d_connect_loop",
    "category": "All"
}


# MAIN CLASS

class ConnectLoop:

    # deep parameter for finding vertices linked by edges with current vertex
    #   bigger value allows more raw selecting, but can use more memory and be more slow
    _linked_verts_recursive_deep = 10

    @classmethod
    def connect_loop(cls, context, ob, boundary_priority=True):
        # connect selected vertices by shortest loop
        #   if boundary_priority == True - boundary vertex on the isoline is priority for connecting
        ob = ob if ob else context.active_object
        if ob:
            # edit/object mode
            mode = ob.mode
            if ob.mode == 'EDIT':
                bpy.ops.object.mode_set(mode='OBJECT')
            # get data loop from source mesh
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bm.verts.ensure_lookup_table()
            # selected vertices
            if boundary_priority:
                # modify selection - try to find boundary vertices (have only one linked edge) and if vertices
                #   connected by the edge vertices are selected too - remove this selection. Leave only boundary
                #   vertex selected
                bm.select_mode = {'VERT'}   # to enable full deselect (edges and faces) just by deselecting vertices
                # for each boundary vertex
                for vertex in (_vertex for _vertex in bm.verts
                               if _vertex.select and len(_vertex.link_edges) == 1):
                    linked_to_boundary_verts = cls._linked_verts(bm_vert=vertex, deep=cls._linked_verts_recursive_deep)
                    linked_to_boundary_verts -= {vertex}  # starting (boundary in our case) vertex is also in the list
                    for linked_vertex in linked_to_boundary_verts:
                        linked_vertex.select = False
                bm.select_flush_mode()  # recalculate selection to apply deselecting vertices to edges and faces
            # selected vertices list
            selected_vertices = [vertex for vertex in bm.verts if vertex.select]
            # create KDTree for selected vertices
            kd = kdtree.KDTree(len(selected_vertices))
            for vertex in selected_vertices:
                kd.insert(vertex.co, vertex.index)
            kd.balance()
            # create loop from selected vertices starting from active vertex
            if bm.select_history.active:
                loop = [bm.select_history.active, ]
                selected_vertices.remove(bm.select_history.active)

                def flt(_index):
                    # filter vertices finding by KDTree to exclude already found and linked by edges
                    # already found vertices are in the "loop" list
                    # vertices connected by edges we dynamically remove from "selected_vertices"
                    return _index not in (vertex.index for vertex in loop) \
                        and _index in (vertex.index for vertex in selected_vertices)

                # find next vertex - mostly close to the first vertex
                current_vertex = bm.select_history.active
                _l = len(selected_vertices)
                _i = 0
                while current_vertex:
                    # check if current vertex has linked selected vertices by edges, to exclude them from next search
                    linked_verts = cls._linked_verts(bm_vert=current_vertex, deep=cls._linked_verts_recursive_deep)
                    selected_vertices = list(set(selected_vertices) - linked_verts)
                    # find next vertex closest to the current_vertex, this vertex will be current on the next step
                    co, index, distance = kd.find(co=current_vertex.co, filter=flt)
                    current_vertex = bm.verts[index] if index else None
                    if current_vertex:
                        loop.append(current_vertex)
                        selected_vertices.remove(current_vertex)
                    # alarm break
                    _i += 1
                    if _i > _l:
                        print('overflow err exit')
                        break
                # now we have loop of vertices - build edges by it
                # print('loop', loop)
                # split loop for chunks each of two vertices
                for chunk in (_chunk for _chunk in cls._chunks(lst=loop, n=2, offset=1) if len(_chunk) == 2):
                    # create edge for each vertex's pair
                    # first try to create with splitting faces
                    connected_dict = bmesh.ops.connect_vert_pair(bm, verts=chunk)
                    # if no edges were created - try to connect vertices without faces between them
                    #   by just creating new edge
                    if not connected_dict['edges']:
                        bm.edges.new(chunk)
            # save changed data to mesh
            bm.to_mesh(ob.data)
            bm.free()
            # return mode back
            bpy.ops.object.mode_set(mode=mode)

    @classmethod
    def _linked_verts(cls, bm_vert, deep=3, verts=None):
        # get all vertices linked to bm_vert by edges recursively on specified deep
        #   bm_vert - starting vertex
        #   deep - recursion deep
        verts = {bm_vert} if verts is None else verts
        if deep > 0:
            selected_linked_verts = {_edge.other_vert(bm_vert) for _edge in bm_vert.link_edges
                                     if _edge.other_vert(bm_vert).select
                                     and _edge.other_vert(bm_vert) not in verts}
            verts |= selected_linked_verts
            for vert in selected_linked_verts:
                verts |= cls._linked_verts(bm_vert=vert, deep=deep - 1, verts=verts)
        return verts

    @staticmethod
    def _chunks(lst, n, offset=0):
        # create list of chunks with n elements in each (sub-lists) from raw list
        for i in range(0, len(lst), n - offset):
            yield lst[i:i + n]

    @staticmethod
    def ui(layout, context):
        # ui panel
        op = layout.operator(
            operator='connect_loop.connect_loop',
            icon='PARTICLE_POINT'
        )
        op.boundary_priority = context.scene.connect_loop_prop_boundary_priority
        layout.prop(
            data=context.scene,
            property='connect_loop_prop_boundary_priority'
        )

# OPERATORS

class ConnectLoop_OT_connect_loop(Operator):
    bl_idname = 'connect_loop.connect_loop'
    bl_label = 'Connect Loop'
    bl_description = 'Connects selected vertices by shortest loop'
    bl_options = {'REGISTER', 'UNDO'}

    boundary_priority = BoolProperty(
        name='Boundary Priority',
        default=True
    )

    def execute(self, context):
        ConnectLoop.connect_loop(
            context=context,
            ob=context.active_object,
            boundary_priority = self.boundary_priority
        )
        return {'FINISHED'}


# PANELS

class ConnectLoop_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'Connect Loop'
    bl_category = '1D'

    def draw(self, context):
        ConnectLoop.ui(
            layout=self.layout,
            context=context
        )


# REGISTER

def register(ui=True):
    Scene.connect_loop_prop_boundary_priority = BoolProperty(
        name='Boundary Priority',
        default=True
    )
    register_class(ConnectLoop_OT_connect_loop)
    if ui:
        register_class(ConnectLoop_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(ConnectLoop_PT_panel)
    unregister_class(ConnectLoop_OT_connect_loop)
    del Scene.connect_loop_prop_boundary_priority


if __name__ == '__main__':
    register()
