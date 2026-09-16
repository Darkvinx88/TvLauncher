"""
Responsive Scaling Module
Gestisce il ridimensionamento responsive basato sulla risoluzione dello schermo
"""
import platform
from PyQt6.QtWidgets import QApplication


class ResponsiveScaling:
    """Resolution based responsive scaling"""
   
    def __init__(self):
        # Risoluzione di riferimento 
        self.BASE_WIDTH = 1920
        self.BASE_HEIGHT = 1080
       
        screen = QApplication.primaryScreen()
        geometry = screen.geometry()
        self.screen_width = geometry.width()
        self.screen_height = geometry.height()
        dpr = screen.devicePixelRatio()

        
        if platform.system() == "Windows":
            physical_width = self.screen_width
            physical_height = self.screen_height
        else:
            physical_width = self.screen_width * dpr
            physical_height = self.screen_height * dpr

        width_scale = physical_width / self.BASE_WIDTH
        height_scale = physical_height / self.BASE_HEIGHT
       
        
        self.scale_factor = min(width_scale, height_scale)
       
        print(f"📐 Screen: {self.screen_width}x{self.screen_height} (logical)")
        print(f"📐 Physical: {int(physical_width)}x{int(physical_height)} (DPR: {dpr})")
        print(f"📐 Scale factor: {self.scale_factor:.2f}")
   
    def scale(self, value):
        """Scala un valore in base alla risoluzione"""
        return int(value * self.scale_factor)
   
    def scale_font(self, base_size):
        """Scala la dimensione del font"""
        return int(base_size * self.scale_factor)
