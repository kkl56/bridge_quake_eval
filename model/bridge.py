import openseespy.opensees as ops
import numpy as np

class BridgeModel:
    def __init__(self, span_length, pier_height, material_props):
        self.span_length = span_length
        self.pier_height = pier_height
        self.material_props = material_props
        self.nodes = {}
        self.elements = {}
        
    def build_in_opensees(self):
        """构建完整的桥梁模型"""
        ops.wipe()
        ops.model('basic', '-ndm', 3, '-ndf', 3)  # 2D模型，每个节点3个自由度
        
        # 创建节点
        # 基础节点
        ops.node(1, 0.0, 0.0)
        ops.node(2, self.span_length, 0.0)
        ops.fix(1, 1, 1, 1)  # 固定支座
        ops.fix(2, 1, 1, 1)  # 固定支座
        
        # 桥墩顶部节点
        ops.node(3, 0.0, self.pier_height)
        ops.node(4, self.span_length, self.pier_height)
        
        # 桥面板中间节点
        ops.node(5, self.span_length/2, self.pier_height+1.0)
        
        # 记录节点信息供后续使用
        self.nodes = {
            "left_base": 1,
            "right_base": 2,
            "left_pier_top": 3,
            "right_pier_top": 4,
            "deck_middle": 5
        }
        
        # 定义材料
        # 墩柱材料
        ops.uniaxialMaterial('Concrete01', 1, 
                             self.material_props['fc'], 
                             self.material_props['fc']/self.material_props['E'], 
                             0.2*self.material_props['fc'], 
                             0.05)
        
        # 桥面板材料
        ops.uniaxialMaterial('Elastic', 2, self.material_props['E'], 0.3)

        # 墩柱截面 - 修复参数列表
        pier_width = self.material_props.get('pier_width', 1.5)
        pier_area = pier_width**2
        pier_iz = pier_width**4/12

        ops.section('Elastic', 1, self.material_props['E'], pier_area, pier_iz, 
                  self.material_props['E']/2.4, pier_iz*2)
        
        # 为每个墩柱创建集成点
        ops.beamIntegration('Legendre', 1, 1, 5)
        
        # 创建坐标变换
        # LinearTransformation是线性的几何关系（小变形假设）
        ops.geomTransf('Linear', 1, 0.0, -1.0, 0.0)  # 竖直柱
        ops.geomTransf('Linear', 2, 0.0, 0.0, 1.0)   # 水平梁

        # 创建构件

        # 改用弹性梁柱单元替代非线性梁柱（简化模型）
        # 左侧墩柱
        ops.element('elasticBeamColumn', 1, 1, 3, 
                   pier_area, self.material_props['E'], pier_iz, 1)
        
        # 右侧墩柱
        ops.element('elasticBeamColumn', 2, 2, 4, 
                   pier_area, self.material_props['E'], pier_iz, 1)
        
        # 桥面板 (简化为弹性梁)
        ops.element('elasticBeamColumn', 3, 3, 5, 
                   self.material_props.get('deck_area', 1.0), 
                   self.material_props['E'], 
                   self.material_props.get('deck_inertia', 0.1), 
                   2)
        
        ops.element('elasticBeamColumn', 4, 5, 4, 
                   self.material_props.get('deck_area', 1.0), 
                   self.material_props['E'], 
                   self.material_props.get('deck_inertia', 0.1), 
                   2)
        
        # 记录单元信息供后续使用
        self.elements = {
            "left_pier": 1,
            "right_pier": 2,
            "left_deck": 3,
            "right_deck": 4
        }
        
    def get_node_ids(self):
        """返回节点ID字典"""
        return self.nodes
        
    def get_element_ids(self):
        """返回单元ID字典"""
        return self.elements
