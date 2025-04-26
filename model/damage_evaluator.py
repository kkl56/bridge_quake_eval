import numpy as np
from enum import Enum

class DamageState(Enum):
    """桥梁损伤状态枚举"""
    NO_DAMAGE = 0       # 无损伤
    SLIGHT = 1          # 轻微损伤
    MODERATE = 2        # 中等损伤
    EXTENSIVE = 3       # 严重损伤
    COMPLETE = 4        # 完全损伤/倒塌

class DamageEvaluator:
    """桥梁损伤评估器"""
    
    def __init__(self, fragility_params=None):
        """
        初始化损伤评估器
        
        参数:
            fragility_params: 易损性曲线参数字典，包含各损伤状态的中值和对数标准差
                             如果为None则使用默认参数
        """
        # 默认的易损性曲线参数 (单位: 米，基于位移)
        self.default_fragility = {
            "pier_drift": {  # 墩柱层间位移角
                DamageState.SLIGHT: {"median": 0.005, "beta": 0.6},
                DamageState.MODERATE: {"median": 0.01, "beta": 0.6},
                DamageState.EXTENSIVE: {"median": 0.025, "beta": 0.6},
                DamageState.COMPLETE: {"median": 0.05, "beta": 0.6}
            },
            "deck_disp": {  # 桥面板位移
                DamageState.SLIGHT: {"median": 0.02, "beta": 0.6},
                DamageState.MODERATE: {"median": 0.05, "beta": 0.6},
                DamageState.EXTENSIVE: {"median": 0.1, "beta": 0.6},
                DamageState.COMPLETE: {"median": 0.3, "beta": 0.6}
            }
        }
        
        self.fragility_params = fragility_params if fragility_params else self.default_fragility
    
    def evaluate_damage_from_results(self, analysis_results, pier_height):
        """
        从分析结果评估桥梁损伤
        
        参数:
            analysis_results: 分析结果字典
            pier_height: 墩柱高度
            
        返回:
            包含损伤状态和概率的字典
        """
        damage_result = {}
        
        # 评估静力分析结果
        if "static" in analysis_results:
            try:
                static_disp = analysis_results["static"]["displacements"]["node5"][1]  # 竖向位移
                damage_result["static"] = {
                    "deck_displacement": static_disp,
                    "damage_state": self._evaluate_damage_state("deck_disp", abs(static_disp))
                }
            except (KeyError, IndexError, TypeError) as e:
                print(f"处理静力分析结果时出错: {e}")
                damage_result["static"] = {
                    "deck_displacement": 0.0,
                    "damage_state": DamageState.NO_DAMAGE,
                    "error": str(e)
                }
        
        # 评估时程分析结果
        if "time_history" in analysis_results:
            try:
                th_results = analysis_results["time_history"]
                
                if len(th_results["displacements"]) <= 1:
                    # 没有有效结果
                    damage_result["time_history"] = {
                        "max_pier_drift": 0.0,
                        "max_deck_displacement": [0.0, 0.0, 0.0],
                        "pier_damage_state": DamageState.NO_DAMAGE,
                        "deck_damage_state": DamageState.NO_DAMAGE,
                        "overall_damage_state": DamageState.NO_DAMAGE,
                        "pier_damage_probabilities": {state.name: 0.0 for state in DamageState},
                        "deck_damage_probabilities": {state.name: 0.0 for state in DamageState},
                        "error": "时程分析结果无效或为空"
                    }
                    return damage_result
                
                # 设置列索引，根据节点和自由度
                # 假设结果格式: 时间, 节点1-x, 节点1-y, 节点1-z, 节点2-x, ...
                # 检查维度是否足够
                if th_results["displacements"].shape[1] < 16:
                    print(f"警告: 位移数据列数不足, 实际: {th_results['displacements'].shape[1]}, 预期: 16")
                    # 使用零数组填充
                    disp_array = np.zeros((len(th_results["displacements"]), 16))
                    disp_array[:, :min(16, th_results["displacements"].shape[1])] = th_results["displacements"][:, :min(16, th_results["displacements"].shape[1])]
                else:
                    disp_array = th_results["displacements"]
                
                # 节点3 (左墩顶) 的x方向位移: 索引应该是1+3*3-3=7 (时间是索引0)
                node3_disp_x = disp_array[:, 4]  # 1+节点*3+自由度
                
                # 节点5 (桥面中点) 的xyz位移: 索引应该是 1+5*3-3=13, 14, 15
                deck_disp = disp_array[:, 13:16]
                
                # 计算最大值
                max_deck_disp = np.max(np.abs(deck_disp), axis=0) if deck_disp.shape[0] > 0 else np.zeros(3)
                max_drift = np.max(np.abs(node3_disp_x)) / pier_height if len(node3_disp_x) > 0 else 0.0
                
                # 评估墩柱损伤
                pier_damage_state = self._evaluate_damage_state("pier_drift", max_drift)
                
                # 评估桥面板损伤
                deck_damage_state = self._evaluate_damage_state("deck_disp", max_deck_disp[1])
                
                # 整体损伤取两者的最大值
                overall_damage = max(pier_damage_state, deck_damage_state, key=lambda x: x.value)
                
                # 计算各损伤状态的概率
                pier_damage_probs = self._calculate_damage_probabilities("pier_drift", max_drift)
                deck_damage_probs = self._calculate_damage_probabilities("deck_disp", max_deck_disp[1])
                
                damage_result["time_history"] = {
                    "max_pier_drift": max_drift,
                    "max_deck_displacement": max_deck_disp,
                    "pier_damage_state": pier_damage_state,
                    "deck_damage_state": deck_damage_state,
                    "overall_damage_state": overall_damage,
                    "pier_damage_probabilities": pier_damage_probs,
                    "deck_damage_probabilities": deck_damage_probs
                }
            except Exception as e:
                print(f"处理时程分析结果时出错: {e}")
                import traceback
                traceback.print_exc()
                
                damage_result["time_history"] = {
                    "max_pier_drift": 0.0,
                    "max_deck_displacement": [0.0, 0.0, 0.0],
                    "pier_damage_state": DamageState.NO_DAMAGE,
                    "deck_damage_state": DamageState.NO_DAMAGE,
                    "overall_damage_state": DamageState.NO_DAMAGE,
                    "pier_damage_probabilities": {state.name: 0.0 for state in DamageState},
                    "deck_damage_probabilities": {state.name: 0.0 for state in DamageState},
                    "error": str(e)
                }
        
        return damage_result
    
    def _evaluate_damage_state(self, component_type, demand):
        """
        评估给定需求下的损伤状态
        
        参数:
            component_type: 构件类型 ("pier_drift" 或 "deck_disp")
            demand: 位移需求值
            
        返回:
            DamageState 枚举值
        """
        fragility = self.fragility_params[component_type]
        
        # 从高到低检查损伤状态
        for state in reversed(list(DamageState)):
            if state == DamageState.NO_DAMAGE:
                return state
                
            if state in fragility:
                median = fragility[state]["median"]
                beta = fragility[state]["beta"]
                
                # 使用对数正态累积分布函数计算超越概率
                if demand >= median:
                    return state
        
        return DamageState.NO_DAMAGE
    
    def _calculate_damage_probabilities(self, component_type, demand):
        """
        计算各损伤状态的概率
        
        参数:
            component_type: 构件类型
            demand: 位移需求值
            
        返回:
            包含各损伤状态概率的字典
        """
        fragility = self.fragility_params[component_type]
        probabilities = {}
        
        for state in DamageState:
            if state == DamageState.NO_DAMAGE:
                continue
                
            if state in fragility:
                median = fragility[state]["median"]
                beta = fragility[state]["beta"]
                
                # 计算超越概率
                if demand > 0:
                    z = np.log(demand / median) / beta
                    prob = self._standard_normal_cdf(z)
                else:
                    prob = 0.0
                
                probabilities[state.name] = prob
        
        # 计算处于各损伤状态的条件概率
        conditional_probs = {}
        prev_prob = 0.0
        
        for state in DamageState:
            if state == DamageState.NO_DAMAGE:
                conditional_probs[state.name] = 1.0 - probabilities.get(DamageState.SLIGHT.name, 0.0)
            elif state == DamageState.COMPLETE:
                conditional_probs[state.name] = probabilities.get(state.name, 0.0)
            else:
                current_prob = probabilities.get(state.name, 0.0)
                next_state = DamageState(state.value + 1)
                next_prob = probabilities.get(next_state.name, 0.0)
                conditional_probs[state.name] = current_prob - next_prob
        
        return conditional_probs
    
    def _standard_normal_cdf(self, x):
        """
        标准正态分布累积分布函数
        """
        return 0.5 * (1 + np.math.erf(x / np.sqrt(2)))
        
    def get_damage_description(self, damage_state):
        """
        获取损伤状态的文字描述
        
        参数:
            damage_state: DamageState枚举值
            
        返回:
            损伤描述字符串
        """
        descriptions = {
            DamageState.NO_DAMAGE: "无损伤",
            DamageState.SLIGHT: "轻微损伤：出现细小裂缝，不影响结构功能",
            DamageState.MODERATE: "中等损伤：明显裂缝，混凝土保护层剥落，可能需要维修",
            DamageState.EXTENSIVE: "严重损伤：大面积混凝土剥落，钢筋裸露，需要重大维修",
            DamageState.COMPLETE: "完全损伤：结构失效或接近失效，需要重建"
        }
        
        return descriptions.get(damage_state, "未知损伤状态") 