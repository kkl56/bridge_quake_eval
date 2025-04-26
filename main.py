import sys

from controller.bridge_evaluator import BridgeEvaluator
import json
import argparse
import logging
from PySide6.QtWidgets import QApplication, QMainWindow
import ui.MainWindowImpl


# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bridge_eval")

def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='桥梁地震损伤评估程序')
    parser.add_argument('--config', '-c', default='data/sample_input.json',
                      help='配置文件路径')
    parser.add_argument('--analysis', '-a', choices=['static', 'modal', 'time_history', 'all'],
                      default='all', help='要运行的分析类型')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='启用调试模式')
    parser.add_argument('--ui', action='store_true', default=True,
                      help='启动图形界面')
    
    args = parser.parse_args()
    
    # 设置调试级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("调试模式已启用")
    
    # 如果启用UI，则启动图形界面
    if args.ui:
        app = QApplication(sys.argv)
        
        # 创建主窗口
        mw = QMainWindow()
        impl = ui.MainWindowImpl.MainWindowImpl(mw)
        mw.show()
        
        # 运行应用程序事件循环
        return app.exec()
    
    # 否则，运行命令行模式
    # 确定要运行的分析类型
    analysis_types = None
    if args.analysis != 'all':
        analysis_types = [args.analysis]
    
    logger.info(f"使用配置文件: {args.config}")
    logger.info(f"分析类型: {analysis_types if analysis_types else 'all'}")
    
    try:
        # 创建桥梁评估器并运行分析
        evaluator = BridgeEvaluator(config_file=args.config)
        results = evaluator.run_analysis(analysis_types)
        
        # 打印损伤评估摘要
        print("\n==== 桥梁损伤评估摘要 ====")
        summary = evaluator.get_damage_summary()
        print(summary)
        
        # 打印分析结果
        logger.info("分析结果概览:")
        if 'analysis' in results:
            for analysis_type, result in results['analysis'].items():
                logger.info(f"- {analysis_type} 分析完成")
                if analysis_type == 'static':
                    try:
                        disp = result['displacements']['node5'][1]
                        logger.info(f"  桥面板最大位移: {disp:.6f} m")
                    except (KeyError, IndexError) as e:
                        logger.error(f"  获取静力分析结果时出错: {e}")
                
                elif analysis_type == 'time_history':
                    try:
                        max_disp = results['summary'].get('max_displacement', [0, 0, 0])
                        logger.info(f"  最大位移响应: {max_disp}")
                    except Exception as e:
                        logger.error(f"  获取时程分析结果时出错: {e}")
        
        # 保存结果
        if 'output' in evaluator.config and evaluator.config['output'].get('save_results'):
            result_file = evaluator.config['output'].get('result_file', 'results.json')
            logger.info(f"结果已保存到: {result_file}")
            
        return evaluator, results
        
    except Exception as e:
        logger.error(f"程序执行过程中出错: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    sys.exit(main())  # 进入QT事件循环或命令行模式

