# === FUNZIONE UTILITY PER ARROTONDARE PIXMAP SENZA BORDO NERO ===
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor


def rounded_pixmap(original_path, width, height, radius):
    """Restituisce un QPixmap arrotondato con sfondo trasparente e senza bordi neri"""
    pixmap = QPixmap(original_path)
    if pixmap.isNull():
        return None
    scaled = pixmap.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )
    result = QPixmap(scaled.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("white"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, scaled.width(), scaled.height(), radius, radius)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return result
