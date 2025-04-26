# 导入必要的库
import openseespy.opensees as ops  # OpenSees有限元分析库
import vtk  # 可视化工具包
import numpy as np  # 数值计算库

# =============================================
# 第一部分：模型初始化
# =============================================

# 清空现有模型
ops.wipe()

# 创建3维基础模型 ('-ndm'表示空间维度)
ops.model('basic', '-ndm', 3)  

# =============================================
# 第二部分：定义节点
# =============================================

# 梁单元节点 (金字塔结构)
ops.node(1, 0, 0, 0)    # 基础节点1
ops.node(2, 5, 0, 0)    # 基础节点2
ops.node(3, 5, 5, 0)    # 基础节点3
ops.node(4, 0, 5, 0)    # 基础节点4
ops.node(5, 2.5, 2.5, 3) # 顶部中心节点

# 壳单元节点 (4节点四边形平板)
ops.node(11, 1, 1, 0)   # 壳节点1
ops.node(12, 4, 1, 0)   # 壳节点2  
ops.node(13, 4, 4, 0)   # 壳节点3
ops.node(14, 1, 4, 0)   # 壳节点4

# 实体单元节点 (8节点六面体)
ops.node(21, 1, 1, -2)  # 实体顶部节点1
ops.node(22, 4, 1, -2)  # 实体顶部节点2
ops.node(23, 4, 4, -2)  # 实体顶部节点3
ops.node(24, 1, 4, -2)  # 实体顶部节点4
ops.node(25, 1, 1, -5)  # 实体底部节点1
ops.node(26, 4, 1, -5)  # 实体底部节点2
ops.node(27, 4, 4, -5)  # 实体底部节点3
ops.node(28, 1, 4, -5)  # 实体底部节点4

# =============================================
# 第三部分：定义材料属性
# =============================================

# 基本材料参数
E = 200e9    # 弹性模量 (单位: Pa)
nu = 0.3     # 泊松比
G = E / (2 * (1 + nu))  # 剪切模量 (计算得出)

# 梁单元截面属性
A_beam = 0.01      # 截面面积 (m²)
Iy_beam = Iz_beam = 1e-5  # 惯性矩 (m⁴)
J_beam = 2e-6      # 扭转常数 (m⁴)

# 壳单元属性
thickness_shell = 0.1  # 壳厚度 (m)

# 定义3D各向同性弹性材料 (用于实体单元)
ops.nDMaterial('ElasticIsotropic', 1, E, nu)

# =============================================
# 第四部分：定义单元类型
# =============================================

# (1) 定义梁单元 (elasticBeamColumn)
ops.geomTransf('Linear', 1, 1, 1, 0)  # 几何变换
ops.element('elasticBeamColumn', 1, 1, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)
ops.element('elasticBeamColumn', 2, 2, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)
ops.element('elasticBeamColumn', 3, 3, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)
ops.element('elasticBeamColumn', 4, 4, 5, A_beam, E, G, J_beam, Iy_beam, Iz_beam, 1)

# (2) 定义壳单元 (ShellMITC4)
ops.section('ElasticMembranePlateSection', 1, E, nu, thickness_shell, 0.0)
ops.element('ShellMITC4', 11, 11, 12, 13, 14, 1)

# (3) 定义实体单元 (stdBrick)
ops.element('stdBrick', 21, 21, 22, 23, 24, 25, 26, 27, 28, 1)

# =============================================
# 第五部分：准备可视化数据
# =============================================

# 获取所有节点标签和坐标
node_tags = ops.getNodeTags()  # 获取所有节点编号
node_coords = np.array([ops.nodeCoord(n) for n in node_tags])  # 获取所有节点坐标

# 获取各类单元连接关系
beam_conn = [ops.eleNodes(ele) for ele in [1,2,3,4]]  # 梁单元连接关系
shell_conn = [ops.eleNodes(11)]                       # 壳单元连接关系
solid_conn = [ops.eleNodes(21)]                       # 实体单元连接关系

# =============================================
# 第六部分：VTK可视化设置
# =============================================

# 创建VTK渲染管线基本组件
renderer = vtk.vtkRenderer()  # 创建渲染器
render_window = vtk.vtkRenderWindow()  # 创建渲染窗口
render_window.AddRenderer(renderer)    # 将渲染器添加到窗口
render_window.SetSize(800, 600)       # 设置窗口大小

# 创建交互器 (用于用户交互)
interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(render_window)

# 创建点集 (存储所有节点坐标)
points = vtk.vtkPoints()
for coord in node_coords:
    points.InsertNextPoint(coord)  # 添加节点坐标

# 创建节点标签到VTK点ID的映射
node_id_map = {tag: i for i, tag in enumerate(node_tags)}

# =============================================
# 6.1 可视化梁单元 (蓝色线)
# =============================================

# 创建线单元容器
lines = vtk.vtkCellArray()
for conn in beam_conn:
    line = vtk.vtkLine()
    # 设置线单元的两个端点 (注意使用映射后的ID)
    line.GetPointIds().SetId(0, node_id_map[conn[0]])
    line.GetPointIds().SetId(1, node_id_map[conn[1]])
    lines.InsertNextCell(line)

# 创建线单元数据集
line_data = vtk.vtkPolyData()
line_data.SetPoints(points)  # 设置点坐标
line_data.SetLines(lines)    # 设置线单元

# 设置线单元映射器和演员
line_mapper = vtk.vtkPolyDataMapper()
line_mapper.SetInputData(line_data)

line_actor = vtk.vtkActor()
line_actor.SetMapper(line_mapper)
line_actor.GetProperty().SetColor(0, 0, 1)  # 设置颜色为蓝色
line_actor.GetProperty().SetLineWidth(3)     # 设置线宽
renderer.AddActor(line_actor)                # 添加到渲染器

# =============================================
# 6.2 可视化壳单元 (绿色面)
# =============================================

# 创建四边形单元容器
quads = vtk.vtkCellArray()
for conn in shell_conn:
    quad = vtk.vtkQuad()
    for i in range(4):  # 四边形有4个节点
        quad.GetPointIds().SetId(i, node_id_map[conn[i]])
    quads.InsertNextCell(quad)

# 创建壳单元数据集
shell_data = vtk.vtkPolyData()
shell_data.SetPoints(points)
shell_data.SetPolys(quads)  # 设置多边形单元

# 设置壳单元映射器和演员
shell_mapper = vtk.vtkPolyDataMapper()
shell_mapper.SetInputData(shell_data)

shell_actor = vtk.vtkActor()
shell_actor.SetMapper(shell_mapper)
shell_actor.GetProperty().SetColor(0, 1, 0)  # 设置颜色为绿色
shell_actor.GetProperty().SetOpacity(0.5)     # 设置透明度
renderer.AddActor(shell_actor)

# =============================================
# 6.3 可视化实体单元 (黄色体)
# =============================================

# 创建六面体单元容器
hexahedrons = vtk.vtkCellArray()
for conn in solid_conn:
    hex = vtk.vtkHexahedron()
    for i in range(8):  # 六面体有8个节点
        hex.GetPointIds().SetId(i, node_id_map[conn[i]])
    hexahedrons.InsertNextCell(hex)

# 创建实体单元数据集
solid_data = vtk.vtkUnstructuredGrid()
solid_data.SetPoints(points)
solid_data.SetCells(vtk.VTK_HEXAHEDRON, hexahedrons)  # 设置六面体单元

# 设置实体单元映射器和演员
solid_mapper = vtk.vtkDataSetMapper()
solid_mapper.SetInputData(solid_data)

solid_actor = vtk.vtkActor()
solid_actor.SetMapper(solid_mapper)
solid_actor.GetProperty().SetColor(1, 1, 0)  # 设置颜色为黄色
solid_actor.GetProperty().SetOpacity(0.8)     # 设置透明度
renderer.AddActor(solid_actor)

# =============================================
# 6.4 可视化节点 (红点)
# =============================================

# 创建顶点容器
vertices = vtk.vtkCellArray()
for i in range(len(node_coords)):
    vertex = vtk.vtkVertex()
    vertex.GetPointIds().SetId(0, i)  # 每个节点作为一个顶点
    vertices.InsertNextCell(vertex)

# 创建点云数据集
point_cloud = vtk.vtkPolyData()
point_cloud.SetPoints(points)
point_cloud.SetVerts(vertices)  # 设置顶点

# 设置点云映射器和演员
point_mapper = vtk.vtkPolyDataMapper()
point_mapper.SetInputData(point_cloud)

point_actor = vtk.vtkActor()
point_actor.SetMapper(point_mapper)
point_actor.GetProperty().SetPointSize(10)  # 设置点大小
point_actor.GetProperty().SetColor(1, 0, 0)  # 设置颜色为红色
renderer.AddActor(point_actor)

# =============================================
# 第七部分：启动可视化
# =============================================

# 设置渲染器背景色 (深蓝色)
renderer.SetBackground(0.1, 0.2, 0.3)  

# 重置相机位置以显示整个场景
renderer.ResetCamera()

# 初始化交互器 (必须步骤)
interactor.Initialize()

# 控制台输出提示信息
print("VTK可视化窗口已启动...")
print("请关闭窗口退出程序")

# 开始渲染和交互
render_window.Render()
interactor.Start()