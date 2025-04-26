import openseespy.opensees as ops
import vtk
import numpy as np

# Clear the model
ops.wipe()
ops.model('basic', '-ndm', 3)  # 3D model

# =============================================
# 1. Define Nodes
# =============================================
# Base nodes (for beam elements)
ops.node(1, 0, 0, 0)
ops.node(2, 5, 0, 0)
ops.node(3, 5, 5, 0)
ops.node(4, 0, 5, 0)
ops.node(5, 2.5, 2.5, 3)  # Top center node

# Shell element nodes (4-node quadrilateral)
ops.node(11, 1, 1, 0)
ops.node(12, 4, 1, 0)
ops.node(13, 4, 4, 0)
ops.node(14, 1, 4, 0)

# Solid element nodes (8-node hexahedron)
ops.node(21, 1, 1, -2)
ops.node(22, 4, 1, -2)
ops.node(23, 4, 4, -2)
ops.node(24, 1, 4, -2)
ops.node(25, 1, 1, -5)
ops.node(26, 4, 1, -5)
ops.node(27, 4, 4, -5)
ops.node(28, 1, 4, -5)

# =============================================
# 2. Define Materials
# =============================================
E = 200e9  # Elastic modulus (Pa)
nu = 0.3   # Poisson's ratio
G = E / (2 * (1 + nu))  # Shear modulus

# Beam material properties
A_beam = 0.01   # Cross-sectional area
Iy_beam = Iz_beam = 1e-5  # Moment of inertia
J_beam = 2e-6   # Torsional constant

# Shell material properties
thickness_shell = 0.1  # Thickness

# Solid material
ops.nDMaterial('ElasticIsotropic', 1, E, nu)

# =============================================
# 3. Define Elements
# =============================================
# (1) Beam elements (elasticBeamColumn)
ops.geomTransf('Linear', 1, 1, 1, 0)
ops.element('elasticBeamColumn', 1, 1, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)
ops.element('elasticBeamColumn', 2, 2, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)
ops.element('elasticBeamColumn', 3, 3, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)
ops.element('elasticBeamColumn', 4, 4, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)

# (2) Shell element (ShellMITC4)
ops.section('ElasticMembranePlateSection', 1, E, nu, thickness_shell, 0.0)
ops.element('ShellMITC4', 11, 11, 12, 13, 14, 1)

# (3) Solid element (stdBrick)
ops.element('stdBrick', 21, 21, 22, 23, 24, 25, 26, 27, 28, 1)

# =============================================
# 4. Extract model data for VTK visualization
# =============================================
node_tags = ops.getNodeTags()
node_coords = np.array([ops.nodeCoord(n) for n in node_tags])

# Get element connectivity
beam_conn = [ops.eleNodes(ele) for ele in [1,2,3,4]]  # Beams
shell_conn = [ops.eleNodes(11)]                       # Shell
solid_conn = [ops.eleNodes(21)]                       # Solid

# Create VTK rendering pipeline
renderer = vtk.vtkRenderer()
render_window = vtk.vtkRenderWindow()
render_window.AddRenderer(renderer)
render_window.SetSize(800, 600)

interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(render_window)

# Create points (all nodes)
points = vtk.vtkPoints()
for coord in node_coords:
    points.InsertNextPoint(coord)

# Create a mapping from node tag to VTK point ID
node_id_map = {tag: i for i, tag in enumerate(node_tags)}

# =============================================
# (1) Display beam elements (blue lines)
# =============================================
lines = vtk.vtkCellArray()
for conn in beam_conn:
    line = vtk.vtkLine()
    line.GetPointIds().SetId(0, node_id_map[conn[0]])
    line.GetPointIds().SetId(1, node_id_map[conn[1]])
    lines.InsertNextCell(line)

line_data = vtk.vtkPolyData()
line_data.SetPoints(points)
line_data.SetLines(lines)

line_mapper = vtk.vtkPolyDataMapper()
line_mapper.SetInputData(line_data)

line_actor = vtk.vtkActor()
line_actor.SetMapper(line_mapper)
line_actor.GetProperty().SetColor(0, 0, 1)  # Blue
line_actor.GetProperty().SetLineWidth(3)
renderer.AddActor(line_actor)

# =============================================
# (2) Display shell element (green surface)
# =============================================
quads = vtk.vtkCellArray()
for conn in shell_conn:
    quad = vtk.vtkQuad()
    for i in range(4):
        quad.GetPointIds().SetId(i, node_id_map[conn[i]])
    quads.InsertNextCell(quad)

shell_data = vtk.vtkPolyData()
shell_data.SetPoints(points)
shell_data.SetPolys(quads)

shell_mapper = vtk.vtkPolyDataMapper()
shell_mapper.SetInputData(shell_data)

shell_actor = vtk.vtkActor()
shell_actor.SetMapper(shell_mapper)
shell_actor.GetProperty().SetColor(0, 1, 0)  # Green
shell_actor.GetProperty().SetOpacity(0.5)
renderer.AddActor(shell_actor)

# =============================================
# (3) Display solid element (yellow volume)
# =============================================
hexahedrons = vtk.vtkCellArray()
for conn in solid_conn:
    hex = vtk.vtkHexahedron()
    for i in range(8):
        hex.GetPointIds().SetId(i, node_id_map[conn[i]])
    hexahedrons.InsertNextCell(hex)

solid_data = vtk.vtkUnstructuredGrid()
solid_data.SetPoints(points)
solid_data.SetCells(vtk.VTK_HEXAHEDRON, hexahedrons)

solid_mapper = vtk.vtkDataSetMapper()
solid_mapper.SetInputData(solid_data)

solid_actor = vtk.vtkActor()
solid_actor.SetMapper(solid_mapper)
solid_actor.GetProperty().SetColor(1, 1, 0)  # Yellow
solid_actor.GetProperty().SetOpacity(0.8)
renderer.AddActor(solid_actor)

# =============================================
# (4) Display nodes (red points)
# =============================================
vertices = vtk.vtkCellArray()
for i in range(len(node_coords)):
    vertex = vtk.vtkVertex()
    vertex.GetPointIds().SetId(0, i)
    vertices.InsertNextCell(vertex)

point_cloud = vtk.vtkPolyData()
point_cloud.SetPoints(points)
point_cloud.SetVerts(vertices)

point_mapper = vtk.vtkPolyDataMapper()
point_mapper.SetInputData(point_cloud)

point_actor = vtk.vtkActor()
point_actor.SetMapper(point_mapper)
point_actor.GetProperty().SetPointSize(10)
point_actor.GetProperty().SetColor(1, 0, 0)  # Red
renderer.AddActor(point_actor)

# =============================================
# Start visualization
# =============================================
renderer.SetBackground(0.1, 0.2, 0.3)  # Dark blue background
renderer.ResetCamera()

# Initialize the interactor before starting it
interactor.Initialize()

# Add some output to know the script is running
print("Starting VTK visualization...")
print("Close the VTK window to exit the program.")

render_window.Render()
interactor.Start()