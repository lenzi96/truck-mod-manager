"""
ElidedLabel widget for clean responsive text truncation with ellipsis.
Prevents horizontal overflow and squished layouts while preserving full text on hover.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy


class ElidedLabel(QLabel):
    """A QLabel that automatically elides its text with '...' when space is constrained."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(60)
        self._update_elided_text()

    @property
    def full_text(self) -> str:
        return self._full_text

    def setText(self, text: str):
        self._full_text = text
        self.setToolTip(text)
        self._update_elided_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(60)
        return hint

    def sizeHint(self):
        hint = super().sizeHint()
        if self._full_text:
            metrics = self.fontMetrics()
            hint.setWidth(min(metrics.horizontalAdvance(self._full_text), 450))
        return hint

    def _update_elided_text(self):
        if not self._full_text:
            super().setText("")
            return
        metrics = self.fontMetrics()
        avail_width = max(10, self.width() - 2)
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, avail_width)
        super().setText(elided)
