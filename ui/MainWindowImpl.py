from ui import pretreatment
import sys
import numpy as np
import os
import json
from PySide6.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QVector3D

from ui.bridge_visualizer import BridgeVisualizerWidget
from model.bridge import BridgeModel
import pyqtgraph.opengl as gl

class CoordinateSystemWidget(gl.GLViewWidget):
    """专门用于显示坐标系的小部件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置黑色背景
        self.setBackgroundColor('k')  # 'k'表示黑色
        
        # 设置视角
        self.setCameraPosition(distance=8, elevation=30, azimuth=45)
        
        # 创建并添加坐标轴
        self._create_coordinate_system()
        
    def _create_coordinate_system(self):
        # 创建坐标轴线条 - 减小尺寸
        self._create_axis_with_arrow('x', [0, 0, 0], [3, 0, 0], (1, 0, 0, 1))  # X轴 - 红色
        self._create_axis_with_arrow('y', [0, 0, 0], [0, 3, 0], (0, 1, 0, 1))  # Y轴 - 绿色
        self._create_axis_with_arrow('z', [0, 0, 0], [0, 0, 3], (0, 0, 1, 1))  # Z轴 - 蓝色
        
        # 原点 - 白色球
        origin = gl.GLScatterPlotItem(
            pos=np.array([[0, 0, 0]]),
            color=np.array([(1, 1, 1, 1)]),  # 白色，在黑色背景上更明显
            size=0.8
        )
        self.addItem(origin)
    
    def _create_axis_with_arrow(self, axis_name, start, end, color):
        """创建带箭头的坐标轴"""
        # 线条
        axis_line = gl.GLLinePlotItem(
            pos=np.array([start, end]), 
            color=color, 
            width=1.5,
            mode='lines'
        )
        self.addItem(axis_line)
        
        # 计算箭头顶点
        x, y, z = end
        arrow_size = 0.5  # 缩小箭头大小
        
        # 根据轴方向创建箭头
        if axis_name == 'x':
            # 创建简单的箭头 - 使用两个三角形形成锥体
            arrow_verts = np.array([
                [x, y, z],                      # 箭头尖端
                [x - arrow_size, y + arrow_size/2, z],  # 左后
                [x - arrow_size, y - arrow_size/2, z],  # 右后
                [x - arrow_size, y, z + arrow_size/2],  # 上后
                [x - arrow_size, y, z - arrow_size/2]   # 下后
            ])
            
        elif axis_name == 'y':
            arrow_verts = np.array([
                [x, y, z],                      # 箭头尖端
                [x + arrow_size/2, y - arrow_size, z],  # 右后
                [x - arrow_size/2, y - arrow_size, z],  # 左后
                [x, y - arrow_size, z + arrow_size/2],  # 上后
                [x, y - arrow_size, z - arrow_size/2]   # 下后
            ])
            
        else:  # z轴
            arrow_verts = np.array([
                [x, y, z],                      # 箭头尖端
                [x + arrow_size/2, y, z - arrow_size],  # 右后
                [x - arrow_size/2, y, z - arrow_size],  # 左后
                [x, y + arrow_size/2, z - arrow_size],  # 前后
                [x, y - arrow_size/2, z - arrow_size]   # 后后
            ])
        
        # 创建面 - 使用三角形
        arrow_faces = np.array([
            [0, 1, 2],  # 底部
            [0, 1, 3],  # 侧面
            [0, 2, 3],  # 侧面
            [0, 2, 4],  # 侧面
            [0, 3, 4],  # 侧面
            [0, 1, 4]   # 侧面
        ])
        
        # 创建网格数据
        md = gl.MeshData(vertexes=arrow_verts, faces=arrow_faces)
        arrow_head = gl.GLMeshItem(
            meshdata=md,
            color=color,
            smooth=False
        )
        self.addItem(arrow_head)
        
        # 添加文字标签 - 使用更大的点来表示轴标签
        label_pos = np.array([[end[0] * 1.2, end[1] * 1.2, end[2] * 1.2]])
        label = gl.GLScatterPlotItem(
            pos=label_pos,
            color=np.array([color]),
            size=4.0  # 增大标记点尺寸
        )
        self.addItem(label)
        
        # 尝试添加文本标签 (使用大点作为标记)
        if axis_name == 'x':
            self.addItem(gl.GLTextItem(pos=(end[0] * 1.2, end[1] * 1.2, end[2] * 1.2), text='X', color=color))
        elif axis_name == 'y':
            self.addItem(gl.GLTextItem(pos=(end[0] * 1.2, end[1] * 1.2, end[2] * 1.2), text='Y', color=color))
        elif axis_name == 'z':
            self.addItem(gl.GLTextItem(pos=(end[0] * 1.2, end[1] * 1.2, end[2] * 1.2), text='Z', color=color))
    
class MainWindowImpl(pretreatment.Ui_MainWindow):
    def __init__(self, window):
        super().__init__()
        self.setupUi(window)
        self.window = window
        self.window.setWindowTitle("桥梁地震评估系统 - 前处理")

        self.replace_opengl_widget()
        
        # 初始化桥梁信息
        self.init_bridge_info()
        
        # 连接按钮信号
        self.pushButton_4.clicked.connect(self.load_model)  # 模型读取
        self.pushButton_2.clicked.connect(self.load_earthquake)  # 地震输入
        self.pushButton_3.clicked.connect(self.set_limits)  # 限值设置
        self.pushButton.clicked.connect(self.back_to_main)  # 返回
        
        # 斜拉桥
        self.current_model_params = {
            "span_length": 40.0,  # 更大的跨度
            "pier_height": 15.0,  # 更高的墩高，实际塔高为此值的2倍
            "material_props": {
                "E": 3000.0,
                "fc": 30.0,
                "pier_width": 1.2,  # 塔柱宽度，实际宽度为此值的2倍
                "deck_area": 3.0,
                "deck_inertia": 1.0
            }
        }
        
        # 设置定时器以更新坐标系视图
        self.setup_rotation_sync()
        
    def setup_rotation_sync(self):
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_coordinate_system)
        self.sync_timer.start(100)  # 每100毫秒更新一次
        
    def sync_coordinate_system(self):
        if hasattr(self, 'bridge_visualizer') and hasattr(self, 'coord_system') and hasattr(self.bridge_visualizer, 'gl_view'):
            main_view = self.bridge_visualizer.gl_view

            if main_view.opts['azimuth'] != getattr(self, '_last_azimuth', None) or \
               main_view.opts['elevation'] != getattr(self, '_last_elevation', None):
                
                # 记录新的视角
                self._last_azimuth = main_view.opts['azimuth']
                self._last_elevation = main_view.opts['elevation']
                
                # 设置坐标系视角
                self.coord_system.setCameraPosition(
                    distance=8,
                    elevation=main_view.opts['elevation'],
                    azimuth=main_view.opts['azimuth']
                )
    
    def replace_opengl_widget(self):
        """替换默认的OpenGL控件为自定义的桥梁可视化控件和坐标系控件"""
        # 获取原始控件的几何信息
        original_geometry = self.openGLWidget.geometry()
        
        # 创建布局容器，将原始控件替换为自定义控件
        container = self.centralwidget
        
        # 移除原始OpenGL控件
        self.openGLWidget.setParent(None)

        self.bridge_visualizer = BridgeVisualizerWidget(container)
        self.bridge_visualizer.setGeometry(original_geometry)
        self.bridge_visualizer.show()
        
        # 设置坐标系小部件
        self.setup_coordinate_system()
        
    def setup_coordinate_system(self):
        """设置坐标系小部件"""
        coords_geometry = self.openGLWidget_2.geometry()

        self.openGLWidget_2.setParent(None)

        if coords_geometry.width() < 100 or coords_geometry.height() < 100:
            # 如果原始控件太小，适当调整大小
            coords_geometry.setWidth(max(100, coords_geometry.width()))
            coords_geometry.setHeight(max(100, coords_geometry.height()))

        self.coord_system = CoordinateSystemWidget(self.centralwidget)
        self.coord_system.setGeometry(coords_geometry)

        self.coord_system.show()
        self.coord_system.raise_()

        print(f"坐标系窗口位置: {coords_geometry.x()}, {coords_geometry.y()}, 大小: {coords_geometry.width()}x{coords_geometry.height()}")
        
    def init_bridge_info(self):
        """初始化桥梁信息"""
        # 这里可以设置默认信息到textBrowser中
        self.textBrowser.setHtml("""
        <!DOCTYPE HTML>
        <html>
        <head>
            <style>
                body { font-family: Arial; font-size: 12pt; }
                h3 { color: #336699; }
                table { border-collapse: collapse; width: 100%; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            </style>
        </head>
        <body>
            <h3>桥梁基本信息</h3>
            <table>
                <tr><td>桥梁类型</td><td>斜拉桥</td></tr>
                <tr><td>主跨</td><td>40.0 m</td></tr>
                <tr><td>塔高</td><td>30.0 m</td></tr>
                <tr><td>设计标准</td><td>公路-I级</td></tr>
            </table>
            <h3>材料参数</h3>
            <table>
                <tr><td>混凝土强度</td><td>30.0 MPa</td></tr>
                <tr><td>弹性模量</td><td>3000.0 MPa</td></tr>
            </table>
        </body>
        </html>
        """)
        
        self.textBrowser_2.setHtml("""
        <!DOCTYPE HTML>
        <html>
        <head>
            <style>
                body { font-family: Arial; font-size: 12pt; }
                h3 { color: #336699; }
                table { border-collapse: collapse; width: 100%; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            </style>
        </head>
        <body>
            <h3>结构特性</h3>
            <table>
                <tr><td>重量</td><td>2500 kN</td></tr>
                <tr><td>桥面宽度</td><td>12.0 m</td></tr>
                <tr><td>抗震设防</td><td>8度</td></tr>
                <tr><td>塔柱截面</td><td>2.4×2.4 m</td></tr>
                <tr><td>拉索数量</td><td>48 根</td></tr>
            </table>
        </body>
        </html>
        """)
        
    def update_bridge_info(self, params):
        span_length = params.get("span_length", 40.0)
        pier_height = params.get("pier_height", 15.0)
        tower_height = pier_height * 2
        material_props = params.get("material_props", {})
        pier_width = material_props.get("pier_width", 1.2) * 2
        e_modulus = material_props.get("E", 3000.0)
        fc = material_props.get("fc", 30.0)
        
        # 更新第一个文本框
        self.textBrowser.setHtml(f"""
        <!DOCTYPE HTML>
        <html>
        <head>
            <style>
                body {{ font-family: Arial; font-size: 12pt; }}
                h3 {{ color: #336699; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h3>桥梁基本信息</h3>
            <table>
                <tr><td>桥梁类型</td><td>斜拉桥</td></tr>
                <tr><td>主跨</td><td>{span_length} m</td></tr>
                <tr><td>塔高</td><td>{tower_height} m</td></tr>
                <tr><td>设计标准</td><td>公路-I级</td></tr>
            </table>
            <h3>材料参数</h3>
            <table>
                <tr><td>混凝土强度</td><td>{fc} MPa</td></tr>
                <tr><td>弹性模量</td><td>{e_modulus} MPa</td></tr>
            </table>
        </body>
        </html>
        """)
        
        # 更新第二个文本框
        # 假设桥面宽度和重量根据参数计算
        deck_width = 12.0  # 假设值
        weight = span_length * 60  # 假设值，可以根据参数计算
        
        self.textBrowser_2.setHtml(f"""
        <!DOCTYPE HTML>
        <html>
        <head>
            <style>
                body {{ font-family: Arial; font-size: 12pt; }}
                h3 {{ color: #336699; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h3>结构特性</h3>
            <table>
                <tr><td>重量</td><td>{weight} kN</td></tr>
                <tr><td>桥面宽度</td><td>{deck_width} m</td></tr>
                <tr><td>抗震设防</td><td>8度</td></tr>
                <tr><td>塔柱截面</td><td>{pier_width}×{pier_width} m</td></tr>
                <tr><td>拉索数量</td><td>48 根</td></tr>
            </table>
        </body>
        </html>
        """)
    
    def load_model(self):
        """加载桥梁模型"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, 
            "选择模型文件", 
            "data", 
            "JSON文件 (*.json);;所有文件 (*.*)", 
            options=options
        )
        
        if file_path:
            try:
                # 加载JSON文件
                with open(file_path, 'r') as f:
                    config = json.load(f)
                
                # 更新模型参数
                self.current_model_params = {
                    "span_length": config.get("span", 20.0),
                    "pier_height": config.get("height", 10.0),
                    "material_props": config.get("material", {
                        "E": 3000.0,
                        "fc": 30.0,
                        "pier_width": 1.2,
                        "deck_area": 3.0,
                        "deck_inertia": 1.0
                    })
                }
                
                # 更新可视化
                self.bridge_visualizer.update_model(self.current_model_params)
                
                # 更新信息显示
                self.update_bridge_info(self.current_model_params)
                
                QMessageBox.information(self.window, "模型加载", f"已成功加载模型: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self.window, "错误", f"加载模型时出错: {str(e)}")
    
    def load_earthquake(self):
        """加载地震波数据"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, 
            "选择地震波文件", 
            "data", 
            "文本文件 (*.txt);;所有文件 (*.*)", 
            options=options
        )
        
        if file_path:
            try:
                QMessageBox.information(self.window, "地震波加载", f"已选择地震波文件: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self.window, "错误", f"加载地震波时出错: {str(e)}")
    
    def set_limits(self):
        """设置损伤限值"""
        QMessageBox.information(self.window, "限值设置", "此功能正在开发中...")
    
    def back_to_main(self):
        """返回主界面"""
        QMessageBox.information(self.window, "返回", "返回主界面功能正在开发中...")
