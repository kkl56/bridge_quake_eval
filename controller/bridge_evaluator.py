import json
import os
import time
import numpy as np
import logging
from model.bridge import BridgeModel
from model.analysis_runner import AnalysisRunner
from model.damage_evaluator import DamageEvaluator, DamageState

logger = logging.getLogger("bridge_eval.evaluator")

class BridgeEvaluator:
    """
    桥梁评估器类，封装整个桥梁结构分析和损伤评估流程
    """
    
    def __init__(self, config_file=None, config_dict=None):
        """
        初始化桥梁评估器
        
        参数:
            config_file: 配置文件路径
            config_dict: 配置字典，与config_file二选一
        """
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
                logger.info(f"从文件加载配置: {config_file}")
        elif config_dict:
            self.config = config_dict
            logger.info("使用传入的配置字典")
        else:
            raise ValueError("必须提供配置文件路径或配置字典")
            
        self.results = {}
        self._initialize_components()
        
    def _initialize_components(self):
        """初始化各组件"""
        # 创建桥梁模型
        self.bridge_model = BridgeModel(
            span_length=self.config['span'],
            pier_height=self.config['height'],
            material_props=self.config['material']
        )
        logger.debug(f"初始化桥梁模型: 跨度={self.config['span']}, 高度={self.config['height']}")
        
        # 创建分析运行器
        self.analysis_runner = AnalysisRunner()
        
        # 创建损伤评估器
        fragility_params = self._convert_fragility_config()
        self.damage_evaluator = DamageEvaluator(fragility_params)
        
    def _convert_fragility_config(self):
        """转换配置中的易损性参数格式"""
        if 'fragility' not in self.config:
            logger.info("配置中未找到易损性参数，使用默认值")
            return None
            
        # 转换为损伤评估器需要的格式
        fragility_config = {}
        
        for component_type, damage_levels in self.config['fragility'].items():
            fragility_config[component_type] = {}
            
            for damage_name, params in damage_levels.items():
                # 将字符串损伤状态名转换为枚举
                damage_state = getattr(DamageState, damage_name.upper())
                fragility_config[component_type][damage_state] = params
                
        logger.debug(f"转换易损性参数完成: {fragility_config.keys()}")
        return fragility_config
        
    def run_analysis(self, analysis_types=None):
        """
        运行分析
        
        参数:
            analysis_types: 要运行的分析类型列表，可选值: 'static', 'modal', 'time_history'
                           如果为None，则根据配置决定
        
        返回:
            包含分析结果的字典
        """
        print("开始桥梁分析...")
        start_time = time.time()
        
        # 确定要运行的分析类型
        if analysis_types is None:
            analysis_types = []
            if 'analysis' in self.config:
                if 'static_load' in self.config['analysis']:
                    analysis_types.append('static')
                if 'ground_motion' in self.config['analysis']:
                    analysis_types.append('time_history')
                    
                # 默认总是运行模态分析
                analysis_types.append('modal')
                
        logger.info(f"将要运行的分析类型: {analysis_types}")
        analysis_results = {}
        
        # 按顺序运行各类型分析，避免相互干扰
        # 1. 静态分析
        if 'static' in analysis_types:
            try:
                print("运行static分析...")
                # 构建模型
                self.bridge_model.build_in_opensees()
                
                static_load = self.config['analysis'].get('static_load', 100.0)
                disp = self.analysis_runner.run_static_analysis(static_load)
                analysis_results['static_displacement'] = disp
                logger.info(f"静态分析完成，最大位移: {disp}")
            except Exception as e:
                logger.error(f"静态分析失败: {e}", exc_info=True)
        
        # 2. 模态分析
        if 'modal' in analysis_types:
            try:
                print("运行modal分析...")
                # 构建模型（重新构建以确保干净的状态）
                self.bridge_model.build_in_opensees()
                
                num_modes = self.config.get('num_modes', 3)
                periods = self.analysis_runner.run_modal_analysis(num_modes)
                analysis_results['modal_periods'] = periods
                logger.info(f"模态分析完成，模态周期: {periods}")
            except Exception as e:
                logger.error(f"模态分析失败: {e}", exc_info=True)
        
        # 3. 时程分析            
        if 'time_history' in analysis_types:
            try:
                print("运行time_history分析...")
                # 构建模型（重新构建以确保干净的状态）
                self.bridge_model.build_in_opensees()
                
                gm_config = self.config['analysis']['ground_motion']
                gm_file = gm_config['file']
                dt = gm_config['dt']
                duration = gm_config.get('duration', None)
                
                th_results = self.analysis_runner.run_time_history_analysis(
                    gm_file, dt, analysis_dt=dt/2, total_time=duration
                )
                
                # 提取关键响应指标
                if len(th_results['displacements']) > 1:
                    max_disp = np.max(np.abs(th_results['displacements'][:, 1:]), axis=0)
                    analysis_results['max_displacement'] = max_disp.tolist()
                    logger.info(f"时程分析完成，最大位移向量: {max_disp}")
                else:
                    logger.warning("时程分析完成，但位移结果为空")
            except Exception as e:
                logger.error(f"时程分析失败: {e}", exc_info=True)
        
        # 保存分析运行器的完整结果
        self.results['analysis'] = self.analysis_runner.get_results()
        
        # 3. 评估损伤
        print("评估结构损伤...")
        try:
            damage_results = self.damage_evaluator.evaluate_damage_from_results(
                self.results['analysis'], 
                self.config['height']
            )
            self.results['damage'] = damage_results
            logger.info(f"损伤评估完成")
        except Exception as e:
            logger.error(f"损伤评估失败: {e}", exc_info=True)
            self.results['damage'] = {"error": str(e)}
        
        # 4. 汇总结果
        end_time = time.time()
        analysis_time = end_time - start_time
        self.results['summary'] = {
            'total_analysis_time': analysis_time,
            'config': self.config
        }
        logger.info(f"分析完成，总耗时: {analysis_time:.2f} 秒")
        
        # 如果配置要求保存结果
        if self.config.get('output', {}).get('save_results', False):
            result_file = self.config['output'].get('result_file', 'results.json')
            self._save_results(result_file)
        
        return self.results
    
    def _save_results(self, filename):
        """保存结果到文件"""
        # 转换不可JSON序列化的对象
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, DamageState):
                return obj.name
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return str(obj)
        
        # 递归处理结果字典
        def process_dict(d):
            result = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    result[k] = process_dict(v)
                elif isinstance(v, list):
                    result[k] = [convert_to_serializable(item) for item in v]
                else:
                    result[k] = convert_to_serializable(v)
            return result
            
        serializable_results = process_dict(self.results)
        
        try:
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=2)
                
            logger.info(f"结果已保存到 {filename}")
            print(f"结果已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存结果时出错: {e}")
    
    def get_damage_summary(self):
        """获取损伤评估摘要"""
        if 'damage' not in self.results:
            return "尚未进行损伤评估"
            
        damage_results = self.results['damage']
        summary = []
        
        if 'time_history' in damage_results:
            th_damage = damage_results['time_history']
            
            if 'error' in th_damage:
                summary.append(f"损伤评估出错: {th_damage['error']}")
                return "\n".join(summary)
                
            overall_state = th_damage['overall_damage_state']
            description = self.damage_evaluator.get_damage_description(overall_state)
            
            summary.append(f"整体损伤状态: {overall_state.name}")
            summary.append(f"损伤描述: {description}")
            summary.append(f"墩柱最大层间位移角: {th_damage['max_pier_drift']:.6f}")
            
            # 添加墩柱损伤概率
            summary.append("墩柱各损伤状态概率:")
            for state, prob in th_damage['pier_damage_probabilities'].items():
                summary.append(f"  - {state}: {prob:.2%}")
                
            # 添加桥面板损伤概率
            summary.append("桥面板各损伤状态概率:")
            for state, prob in th_damage['deck_damage_probabilities'].items():
                summary.append(f"  - {state}: {prob:.2%}")
        elif 'static' in damage_results:
            static_damage = damage_results['static']
            if 'error' in static_damage:
                summary.append(f"静力分析损伤评估出错: {static_damage['error']}")
            else:
                state = static_damage['damage_state']
                description = self.damage_evaluator.get_damage_description(state)
                summary.append(f"静力分析损伤状态: {state.name}")
                summary.append(f"损伤描述: {description}")
                summary.append(f"桥面板最大位移: {static_damage['deck_displacement']:.6f}")
        else:
            summary.append("未进行损伤评估或损伤评估结果为空")
                
        return "\n".join(summary)


def run_from_config(config_file):
    """从配置文件运行桥梁评估"""
    evaluator = BridgeEvaluator(config_file=config_file)
    results = evaluator.run_analysis()
    
    print("\n==== 评估结果摘要 ====")
    print(evaluator.get_damage_summary())
    
    return evaluator, results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "data/sample_input.json"
        
    run_from_config(config_file) 