import asyncio
import time

from PyQt5.QtCore import QRunnable, pyqtSlot

from engine.active_learning import ActiveLearning
from view.engine_callback import EngineSignals


class Engine(QRunnable):
    def __init__(self, img_path, label_path, *args, **kwargs):
        super(Engine, self).__init__()
        self.img_path = img_path
        self.label_path = label_path
        self.signals = EngineSignals()
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        try:
            al = ActiveLearning()
            al.run(self.img_path, self.label_path, self.signals)
            self.signals.success.emit(100, 'SUCCESS')
        except:
            self.signals.error(0, '')