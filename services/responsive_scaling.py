from PyQt6.QtWidgets import ( QApplication )

class ResponsiveScaling:
    """Resolution based responsive scaling"""
   
    def __init__(self):
        # Risoluzione di riferimento (quella su cui hai progettato l'interfaccia)
        self.BASE_WIDTH = 1920
        self.BASE_HEIGHT = 1080
       
        # Ottieni la risoluzione corrente
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
       
        # Calcola il fattore di scala
        width_scale = self.screen_width / self.BASE_WIDTH
        height_scale = self.screen_height / self.BASE_HEIGHT
       
        # Usa il minore dei due per mantenere l'aspect ratio
        self.scale_factor = min(width_scale, height_scale)
       
        print(f"📐 Screen: {self.screen_width}x{self.screen_height}")
        print(f"📐 Scale factor: {self.scale_factor:.2f}")
   
    def scale(self, value):
        """Scala un valore in base alla risoluzione"""
        return int(value * self.scale_factor)
   
    def scale_font(self, base_size):
        """Scala la dimensione del font"""
        return int(base_size * self.scale_factor)