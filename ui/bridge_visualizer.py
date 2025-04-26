import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from model.bridge import BridgeModel

class BridgeVisualizerWidget(QWidget):
    """使用VTK实现的桥梁可视化控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建垂直布局容器
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建VTK的渲染组件
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.layout.addWidget(self.vtk_widget)
        
        # 创建渲染器和渲染窗口
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.2, 0.2, 0.2)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        
        # 桥梁组件的引用
        self.bridge_components = {}
        
        # 默认桥梁参数
        self.default_params = {
            "span_length": 40.0,
            "pier_height": 15.0,
            "material_props": {
                "E": 3000.0,
                "fc": 30.0,
                "pier_width": 1.2,
                "deck_area": 3.0,
                "deck_inertia": 1.0
            }
        }
        
        # 初始化可视化
        self.initialize()
        
    def initialize(self):
        """初始化VTK视图"""
        # 设置相机位置
        self.renderer.GetActiveCamera().SetPosition(80, 80, 80)
        self.renderer.GetActiveCamera().SetFocalPoint(0, 0, 0)
        self.renderer.GetActiveCamera().SetViewUp(0, 0, 1)
        
        # 创建斜拉桥模型
        self.create_cable_stayed_bridge(
            self.default_params["span_length"],
            self.default_params["pier_height"],
            self.default_params["material_props"]
        )
        
        # 启动交互器
        self.interactor.Initialize()
        self.vtk_widget.GetRenderWindow().Render()
    
    def create_bridge_model(self, span_length, pier_height, material_props):
        """创建斜拉桥模型 - 保留此方法以兼容现有代码"""
        self.create_cable_stayed_bridge(span_length, pier_height, material_props)

    def create_cable_stayed_bridge(self, span_length, pier_height, material_props):
        """创建斜拉桥模型"""
        # 移除现有组件
        for component in self.bridge_components.values():
            self.renderer.RemoveActor(component)
        self.bridge_components = {}
        
        # 基本参数
        tower_height = pier_height * 2  # 桥塔高度
        deck_width = 8.0  # 桥面宽度
        deck_thickness = 1.0  # 桥面厚度
        
        # 桥塔位置
        tower_spacing = span_length * 0.6  # 桥塔间距
        
        # 创建桥面板
        deck_length = span_length * 1.2  # 桥面长度稍大于主跨
        deck = self._create_deck(-deck_length/2, -deck_width/2, 0, deck_length, deck_width, deck_thickness)
        self.renderer.AddActor(deck)
        self.bridge_components['deck'] = deck
        
        # 桥塔宽度
        tower_width = material_props.get('pier_width', 1.2) * 2
        tower_depth = tower_width
        
        # 左塔
        left_tower_pos = -tower_spacing/2
        left_tower = self._create_tower(
            pos=(left_tower_pos, 0, 0),
            width=tower_width,
            depth=tower_depth,
            height=tower_height
        )
        self.renderer.AddActor(left_tower)
        self.bridge_components['left_tower'] = left_tower
        
        # 右塔
        right_tower_pos = tower_spacing/2
        right_tower = self._create_tower(
            pos=(right_tower_pos, 0, 0),
            width=tower_width,
            depth=tower_depth,
            height=tower_height
        )
        self.renderer.AddActor(right_tower)
        self.bridge_components['right_tower'] = right_tower
        
        # 创建斜拉索
        # 在桥面上创建连接点
        deck_attachments = []
        num_cables = 12  # 每侧的拉索数量
        
        # 左侧连接点
        for i in range(num_cables):
            pos = -tower_spacing/2 + (i - num_cables/2) * (tower_spacing/2) / num_cables
            if pos < left_tower_pos:  # 只处理左侧点
                deck_attachments.append((pos, -deck_width/2 + 0.5, 0))
                deck_attachments.append((pos, deck_width/2 - 0.5, 0))
        
        # 右侧连接点
        for i in range(num_cables):
            pos = tower_spacing/2 + (i - num_cables/2) * (tower_spacing/2) / num_cables
            if pos > right_tower_pos:  # 只处理右侧点
                deck_attachments.append((pos, -deck_width/2 + 0.5, 0))
                deck_attachments.append((pos, deck_width/2 - 0.5, 0))
        
        # 创建左塔上的拉索
        for i, attach_point in enumerate(deck_attachments):
            if attach_point[0] < left_tower_pos:  # 只连接左侧的点
                # 计算拉索在塔上的连接高度 - 交替排列
                height_factor = 0.6 + (i % 3) * 0.1
                cable = self._create_cable(
                    start=(left_tower_pos, attach_point[1], tower_height * height_factor),
                    end=attach_point
                )
                self.renderer.AddActor(cable)
                self.bridge_components[f'left_cable_{i}'] = cable
        
        # 创建右塔上的拉索
        for i, attach_point in enumerate(deck_attachments):
            if attach_point[0] > right_tower_pos:  # 只连接右侧的点
                # 计算拉索在塔上的连接高度 - 交替排列
                height_factor = 0.6 + (i % 3) * 0.1
                cable = self._create_cable(
                    start=(right_tower_pos, attach_point[1], tower_height * height_factor),
                    end=attach_point
                )
                self.renderer.AddActor(cable)
                self.bridge_components[f'right_cable_{i}'] = cable
        
        # 添加桥面中点标记和桥塔顶点标记
        self._add_markers(
            [(0, 0, deck_thickness)],  # 桥面中点
            [[1, 0, 0]],  # 红色
            'deck_middle'
        )
        
        self._add_markers(
            [(left_tower_pos, 0, tower_height), (right_tower_pos, 0, tower_height)],  # 塔顶点
            [[0, 1, 0], [0, 1, 0]],  # 绿色
            ['left_tower_top', 'right_tower_top']
        )
        
        # 重置视图
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def _add_markers(self, positions, colors, names):
        """添加标记点"""
        if not isinstance(names, list):
            names = [names]
        
        for i, (pos, color) in enumerate(zip(positions, colors)):
            # 创建球体
            sphere = vtk.vtkSphereSource()
            sphere.SetCenter(pos)
            sphere.SetRadius(0.5)
            sphere.SetPhiResolution(16)
            sphere.SetThetaResolution(16)
            
            # 创建映射器和演员
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(sphere.GetOutputPort())
            
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(color)
            
            self.renderer.AddActor(actor)
            self.bridge_components[names[i]] = actor
    
    def _create_tower(self, pos, width, depth, height):
        """创建桥塔"""
        x, y, z = pos
        
        # 桥塔顶部略窄
        top_width = width * 0.8
        top_depth = depth * 0.8
        
        # 创建一个具有8个顶点的立方体
        points = vtk.vtkPoints()
        # 底部四个点
        points.InsertNextPoint(x-width/2, y-depth/2, z)
        points.InsertNextPoint(x+width/2, y-depth/2, z)
        points.InsertNextPoint(x+width/2, y+depth/2, z)
        points.InsertNextPoint(x-width/2, y+depth/2, z)
        # 顶部四个点
        points.InsertNextPoint(x-top_width/2, y-top_depth/2, z+height)
        points.InsertNextPoint(x+top_width/2, y-top_depth/2, z+height)
        points.InsertNextPoint(x+top_width/2, y+top_depth/2, z+height)
        points.InsertNextPoint(x-top_width/2, y+top_depth/2, z+height)
        
        # 定义立方体的六个面
        faces = vtk.vtkCellArray()
        
        # 添加六个面（每个面是一个四边形）
        quad = vtk.vtkQuad()
        # 底面
        quad.GetPointIds().SetId(0, 0)
        quad.GetPointIds().SetId(1, 1)
        quad.GetPointIds().SetId(2, 2)
        quad.GetPointIds().SetId(3, 3)
        faces.InsertNextCell(quad)
        
        # 顶面
        quad = vtk.vtkQuad()
        quad.GetPointIds().SetId(0, 4)
        quad.GetPointIds().SetId(1, 5)
        quad.GetPointIds().SetId(2, 6)
        quad.GetPointIds().SetId(3, 7)
        faces.InsertNextCell(quad)
        
        # 前面
        quad = vtk.vtkQuad()
        quad.GetPointIds().SetId(0, 0)
        quad.GetPointIds().SetId(1, 1)
        quad.GetPointIds().SetId(2, 5)
        quad.GetPointIds().SetId(3, 4)
        faces.InsertNextCell(quad)
        
        # 右面
        quad = vtk.vtkQuad()
        quad.GetPointIds().SetId(0, 1)
        quad.GetPointIds().SetId(1, 2)
        quad.GetPointIds().SetId(2, 6)
        quad.GetPointIds().SetId(3, 5)
        faces.InsertNextCell(quad)
        
        # 后面
        quad = vtk.vtkQuad()
        quad.GetPointIds().SetId(0, 2)
        quad.GetPointIds().SetId(1, 3)
        quad.GetPointIds().SetId(2, 7)
        quad.GetPointIds().SetId(3, 6)
        faces.InsertNextCell(quad)
        
        # 左面
        quad = vtk.vtkQuad()
        quad.GetPointIds().SetId(0, 3)
        quad.GetPointIds().SetId(1, 0)
        quad.GetPointIds().SetId(2, 4)
        quad.GetPointIds().SetId(3, 7)
        faces.InsertNextCell(quad)
        
        # 创建多边形数据
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetPolys(faces)
        
        # 创建映射器
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polyData)
        
        # 创建演员
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.5, 0.5, 0.5)
        
        return actor
    
    def _create_cable(self, start, end):
        """创建拉索"""
        # 为了视觉效果，给拉索添加一点弯曲
        x1, y1, z1 = start
        x2, y2, z2 = end
        
        # 计算中点并稍微下移
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        mid_z = (z1 + z2) / 2 - 0.03 * np.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        
        # 创建三次样条曲线
        points = vtk.vtkPoints()
        points.InsertNextPoint(x1, y1, z1)
        points.InsertNextPoint(mid_x, mid_y, mid_z)
        points.InsertNextPoint(x2, y2, z2)
        
        # 创建样条
        spline = vtk.vtkParametricSpline()
        spline.SetPoints(points)
        
        # 创建样条函数源
        functionSource = vtk.vtkParametricFunctionSource()
        functionSource.SetParametricFunction(spline)
        functionSource.SetUResolution(20)
        
        # 创建管道表示拉索
        tubeFilter = vtk.vtkTubeFilter()
        tubeFilter.SetInputConnection(functionSource.GetOutputPort())
        tubeFilter.SetRadius(0.1)
        tubeFilter.SetNumberOfSides(8)
        
        # 创建映射器
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tubeFilter.GetOutputPort())
        
        # 创建演员
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.9, 0.9, 0.9)
        
        return actor
    
    def _create_deck(self, x, y, z, length, width, height):
        """创建桥面板3D模型"""
        # 创建立方体
        cubeSource = vtk.vtkCubeSource()
        cubeSource.SetCenter(x + length/2, y + width/2, z + height/2)
        cubeSource.SetXLength(length)
        cubeSource.SetYLength(width)
        cubeSource.SetZLength(height)
        
        # 创建映射器
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cubeSource.GetOutputPort())
        
        # 创建演员
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.5, 0.5, 0.5)
        
        return actor
    
    def update_model(self, params):
        """更新模型参数"""
        span_length = params.get("span_length", self.default_params["span_length"])
        pier_height = params.get("pier_height", self.default_params["pier_height"])
        material_props = params.get("material_props", self.default_params["material_props"])
        
        self.create_cable_stayed_bridge(span_length, pier_height, material_props)
    
    def highlight_component(self, component_name, color=(1.0, 0.5, 0.0)):
        """高亮显示某个构件，用于损伤标识"""
        if component_name in self.bridge_components:
            self.bridge_components[component_name].GetProperty().SetColor(color)
            self.vtk_widget.GetRenderWindow().Render()
    
    def reset_highlights(self):
        """重置所有高亮显示"""
        for name, component in self.bridge_components.items():
            if 'tower' in name or name in ['left_tower', 'right_tower']:
                component.GetProperty().SetColor(0.5, 0.5, 0.5)
            elif 'deck' in name:
                component.GetProperty().SetColor(0.5, 0.5, 0.5)
            elif 'cable' in name:
                component.GetProperty().SetColor(0.9, 0.9, 0.9)
        self.vtk_widget.GetRenderWindow().Render()
    
    def set_damage_visualization(self, damage_data):
        """根据损伤状态设置可视化效果"""
        # 定义损伤状态的颜色映射
        damage_colors = {
            'NO_DAMAGE': (0, 1, 0),     # 绿色
            'SLIGHT': (1, 1, 0),        # 黄色
            'MODERATE': (1, 0.5, 0),    # 橙色
            'EXTENSIVE': (1, 0, 0),     # 红色
            'COMPLETE': (0.5, 0, 0)     # 深红色
        }
        
        # 重置所有高亮
        self.reset_highlights()
        
        # 如果有损伤数据，应用到模型中
        if damage_data and 'time_history' in damage_data:
            # 墩柱损伤
            pier_damage = damage_data['time_history'].get('pier_damage_state')
            if pier_damage and pier_damage.name in damage_colors:
                color = damage_colors[pier_damage.name]
                if 'left_tower' in self.bridge_components:
                    self.bridge_components['left_tower'].GetProperty().SetColor(color)
                if 'right_tower' in self.bridge_components:
                    self.bridge_components['right_tower'].GetProperty().SetColor(color)
            
            # 桥面板损伤
            deck_damage = damage_data['time_history'].get('deck_damage_state')
            if deck_damage and deck_damage.name in damage_colors:
                color = damage_colors[deck_damage.name]
                if 'deck' in self.bridge_components:
                    self.bridge_components['deck'].GetProperty().SetColor(color)
        
        # 更新渲染
        self.vtk_widget.GetRenderWindow().Render() 