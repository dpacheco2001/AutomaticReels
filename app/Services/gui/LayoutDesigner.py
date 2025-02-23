# LayoutDesigner.py
import sys, math
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QSpinBox, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QLineEdit

from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt

class LayoutPreview(QWidget):
    def __init__(self, sections, video_width=720, video_height=1280, parent=None):
        super().__init__(parent)
        self.sections = sections  # Lista de dicts: {"x", "y", "w", "h", "id"}
        self.video_width = video_width
        self.video_height = video_height
        self.setFixedSize(360, 640)  # Previsualización escalada
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(220,220,220))
        scale_x = self.width() / self.video_width
        scale_y = self.height() / self.video_height
        pen = QPen(QColor(0,0,0))
        pen.setWidth(2)
        painter.setPen(pen)
        for section in self.sections:
            x = section["x"] * scale_x
            y = section["y"] * scale_y
            w = section["w"] * scale_x
            h = section["h"] * scale_y
            painter.drawRect(int(x), int(y), int(w), int(h))
            if "id" in section and section["id"]:
                painter.drawText(int(x)+5, int(y)+20, section["id"])

class LayoutDesigner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diseñador de Layout")
        self.sections = []
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # Selección de número de secciones
        num_layout = QHBoxLayout()
        num_label = QLabel("Número de secciones:")
        self.num_spin = QSpinBox()
        self.num_spin.setMinimum(1)
        self.num_spin.setMaximum(20)
        self.num_spin.setValue(6)
        generate_btn = QPushButton("Generar Vista")
        generate_btn.clicked.connect(self.generate_layout)
        num_layout.addWidget(num_label)
        num_layout.addWidget(self.num_spin)
        num_layout.addWidget(generate_btn)
        main_layout.addLayout(num_layout)
        
        # Área de previsualización
        self.preview = None
        self.preview_container = QVBoxLayout()
        main_layout.addLayout(self.preview_container)
        
        # Formulario para asignar IDs
        self.form = QFormLayout()
        main_layout.addLayout(self.form)
        
        # Botón para continuar
        next_btn = QPushButton("Siguiente")
        next_btn.clicked.connect(self.proceed)
        main_layout.addWidget(next_btn)
        
        self.setLayout(main_layout)
    
    def generate_layout(self):
        n = self.num_spin.value()
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        video_width = 720
        video_height = 1280
        cell_w = video_width / cols
        cell_h = video_height / rows
        self.sections = []
        for i in range(n):
            row = i // cols
            col = i % cols
            section = {"x": col * cell_w, "y": row * cell_h, "w": cell_w, "h": cell_h, "id": f"div_{i+1}"}
            self.sections.append(section)
        
        if self.preview:
            self.preview.setParent(None)
        self.preview = LayoutPreview(self.sections, video_width, video_height)
        self.preview_container.addWidget(self.preview)
        
        for i in reversed(range(self.form.count())):
            self.form.removeRow(i)
        self.id_edits = []
        for i, section in enumerate(self.sections):
            edit = QLineEdit(section["id"])
            self.form.addRow(f"ID para sección {i+1}:", edit)
            self.id_edits.append(edit)
    
    def proceed(self):
        for i, edit in enumerate(self.id_edits):
            self.sections[i]["id"] = edit.text()
        config = {"layout_sections": self.sections}
        QMessageBox.information(self, "Layout", f"Configuración guardada:\n{config}")
        self.config = config  # Guardamos la configuración para usarla en el main
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    designer = LayoutDesigner()
    designer.show()
    sys.exit(app.exec_())
