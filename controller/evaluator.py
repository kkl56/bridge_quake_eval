from model.bridge import BridgeModel
from model.analysis_runner import AnalysisRunner

class Evaluator:
    def __init__(self, config):
        self.model = BridgeModel(
            span_length=config['span'],
            pier_height=config['height'],
            material_props=config['material']
        )
        self.runner = AnalysisRunner()

    def run(self):
        self.model.build_in_opensees()
        disp = self.runner.run_static_analysis()
        print(f'位移结果: {disp}')
