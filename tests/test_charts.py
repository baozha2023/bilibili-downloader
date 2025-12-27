import sys
import os
import unittest
import types
import importlib.util
from unittest.mock import MagicMock
import matplotlib
matplotlib.use('Agg')

# Mock modules using MagicMock
sys.modules["PyQt5"] = MagicMock()
sys.modules["PyQt5"].__path__ = [] 

sys.modules["PyQt5.QtWidgets"] = MagicMock()
sys.modules["PyQt5.QtGui"] = MagicMock()
sys.modules["PyQt5.QtCore"] = MagicMock()
sys.modules["PyQt5.QtNetwork"] = MagicMock()

# Configure specific return values
qt_gui = sys.modules["PyQt5.QtGui"]
qt_gui.QImage.fromData.return_value = "mock_image_data"
qt_gui.QPixmap.fromImage.return_value = "mock_pixmap"

# Load charts.py directly bypassing package init
charts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ui/tabs/analysis/charts.py'))
spec = importlib.util.spec_from_file_location("charts", charts_path)
charts_module = importlib.util.module_from_spec(spec)
sys.modules["charts"] = charts_module
spec.loader.exec_module(charts_module)

ChartGenerator = charts_module.ChartGenerator

class TestCharts(unittest.TestCase):
    def setUp(self):
        self.label = MagicMock()
        self.label.setPixmap = MagicMock()
        self.label.setText = MagicMock()

    def test_generate_stats_chart(self):
        print("Testing generate_stats_chart...")
        stat = {'view': 100, 'like': 10, 'coin': 5, 'favorite': 2, 'share': 1}
        ChartGenerator.generate_stats_chart(self.label, stat)
        self.label.setPixmap.assert_called()

    def test_generate_ratio_chart(self):
        print("Testing generate_ratio_chart...")
        stat = {'view': 100, 'like': 10, 'coin': 5, 'favorite': 2}
        ChartGenerator.generate_ratio_chart(self.label, stat)
        self.label.setPixmap.assert_called()

    def test_generate_danmaku_chart(self):
        print("Testing generate_danmaku_chart...")
        danmaku = [{'time': 10}, {'time': 20}, {'time': 50}]
        ChartGenerator.generate_danmaku_chart(self.label, danmaku, duration=100)
        self.label.setPixmap.assert_called()

    def test_generate_level_chart(self):
        print("Testing generate_level_chart...")
        levels = [1, 2, 3, 3, 4, 5, 6, 6, 6]
        ChartGenerator.generate_level_chart(self.label, levels)
        self.label.setPixmap.assert_called()

    def test_generate_sentiment_chart(self):
        print("Testing generate_sentiment_chart...")
        score = 0.75
        ChartGenerator.generate_sentiment_chart(self.label, score)
        self.label.setPixmap.assert_called()

    def test_generate_location_chart(self):
        print("Testing generate_location_chart...")
        locations = ['北京', '上海', '北京', '广州']
        ChartGenerator.generate_location_chart(self.label, locations)
        self.label.setPixmap.assert_called()

    def test_generate_danmaku_color_chart(self):
        print("Testing generate_danmaku_color_chart...")
        danmaku = [{'color': 16777215}, {'color': 0}, {'color': 16777215}]
        ChartGenerator.generate_danmaku_color_chart(self.label, danmaku)
        self.label.setPixmap.assert_called()

    def test_generate_emoji_chart(self):
        print("Testing generate_emoji_chart...")
        emojis = ['[doge]', '[OK]', '[doge]']
        ChartGenerator.generate_emoji_chart(self.label, emojis)
        self.label.setPixmap.assert_called()

    def test_generate_word_cloud(self):
        print("Testing generate_word_cloud...")
        comments = ["测试", "评论", "内容", "哈哈", "不错"]
        ChartGenerator.generate_word_cloud(self.label, comments)
        if self.label.setPixmap.called:
            pass
        elif self.label.setText.called:
            print(f"WordCloud failed but handled: {self.label.setText.call_args}")
        else:
            self.fail("Neither setPixmap nor setText called for word cloud")

if __name__ == '__main__':
    unittest.main()
