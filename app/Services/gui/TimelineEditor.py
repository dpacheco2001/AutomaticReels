import sys, math
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QLabel, QPushButton, QFormLayout, QMessageBox, QSizePolicy, QScrollArea)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QRectF
from moviepy import VideoFileClip  # Para extraer la duración del video

class TimelinePreview(QWidget):
    PIXELS_PER_SECOND = 100

    def __init__(self, timeline_config, total_duration, parent=None):
        """
        timeline_config: diccionario con claves = id de elemento, y valores = {"start": ..., "end": ...}
        total_duration: duración total del video en segundos.
        """
        super().__init__(parent)
        self.timeline_config = timeline_config
        self.total_duration = total_duration
        self.setMinimumSize(int(self.total_duration * self.PIXELS_PER_SECOND), 250)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setSizePolicy(size_policy)
    
    def setDynamicHeight(self, num_elements):
        height = 20 + 10 + num_elements * (40 + 10)
        self.setMinimumHeight(height)
    
    def setDynamicWidth(self, total_duration):
        self.total_duration = total_duration
        self.setMinimumWidth(int(self.total_duration * self.PIXELS_PER_SECOND))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240,240,240))
        
        tick_spacing = self.width() / self.total_duration if self.total_duration > 0 else 100
        ruler_height = 20
        pen = QPen(QColor("black"))
        painter.setPen(pen)
        for sec in range(0, int(self.total_duration)+1):
            x = int(sec * tick_spacing)
            painter.drawLine(x, 0, x, ruler_height)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x+2, ruler_height-2, f"{sec}s")
        
        start_y = ruler_height + 10
        track_height = 40
        spacing = 10
        total_px = self.width()
        for idx, (elem_id, cfg) in enumerate(self.timeline_config.items()):
            y = start_y + idx * (track_height + spacing)
            start_sec = float(cfg.get("start", 0))
            end_sec = float(cfg.get("end", 0))
            duration_sec = end_sec - start_sec
            x = (start_sec / self.total_duration) * total_px
            width_px = (duration_sec / self.total_duration) * total_px
            rect = QRectF(int(x), int(y), int(width_px), int(track_height))
            painter.setBrush(QColor(100,150,200))
            painter.drawRect(rect)
            painter.setFont(QFont("Arial", 10))
            painter.drawText(int(x)+5, int(y)+20, f"{elem_id}: {start_sec}s - {end_sec}s")

class TimelineConfigEditor(QWidget):
    def __init__(self, timeline_items, total_duration, parent=None):
        """
        timeline_items: lista de diccionarios, cada uno con:
            "id": identificador,
            "component": descripción (ej. "Texto Principal"),
            "type": "dynamic" o "static".
            Si es static y subtype es "video", debe incluir "video_path".
            Para los demás, si no se definen, se usan valores por defecto: start=0, end=5.
        total_duration: duración total del video en segundos (valor inicial).
        """
        super().__init__(parent)
        self.setWindowTitle("Editor de Línea de Tiempo")
        self.timeline_items = timeline_items
        self.total_duration = total_duration
        self.initUI()
    
    def initUI(self):
        self.layout = QVBoxLayout()
        
        # Campo para definir la duración total del video
        self.total_duration_edit = QLineEdit(str(self.total_duration))
        self.total_duration_edit.setMaximumWidth(100)
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duración total del video (s):"))
        duration_layout.addWidget(self.total_duration_edit)
        self.layout.addLayout(duration_layout)
        
        # Formulario para cada elemento
        self.form = QFormLayout()
        self.fields = []
        for item in self.timeline_items:
            h_layout = QHBoxLayout()
            label = QLabel(f"{item['id']} ({item['component']})")
            # Para elementos que no definan start/end, usamos por defecto start=0, end=5
            default_start = item.get("start", 0)
            default_end = item.get("end", 5)
            start_edit = QLineEdit(str(default_start))
            start_edit.setMaximumWidth(60)
            # Para static video, usamos "Duración (s)" en vez de "Final (s)"
            if item["type"].lower() == "static" and item.get("subtype", "").lower() == "video":
                end_label = "Duración (s):"
                video_path = item.get("video_path", "")
                default_duration = 0.0
                if video_path:
                    try:
                        clip = VideoFileClip(video_path)
                        default_duration = clip.duration
                        clip.close()
                    except Exception as e:
                        print(f"Error al obtener duración de {video_path}: {e}")
                        default_duration = 5.0
                item["default_duration"] = default_duration
                # Para video, el valor por defecto de duración se extrae, y si no se especifica, se usa default_duration.
                end_val = str(default_duration)
            else:
                end_label = "Final (s):"
                end_val = str(default_end)
            end_edit = QLineEdit(end_val)
            end_edit.setMaximumWidth(60)
            
            h_layout.addWidget(label)
            h_layout.addWidget(QLabel("Inicio (s):"))
            h_layout.addWidget(start_edit)
            h_layout.addWidget(QLabel(end_label))
            h_layout.addWidget(end_edit)
            
            self.fields.append((item["id"], item["type"], item.get("subtype", ""), start_edit, end_edit, item.get("default_duration", None)))
            self.form.addRow(h_layout)
        self.layout.addLayout(self.form)
        
        self.update_btn = QPushButton("Actualizar Preview")
        self.update_btn.clicked.connect(self.update_preview)
        self.layout.addWidget(self.update_btn)
        
        # Colocar la preview dentro de un QScrollArea para permitir scroll horizontal y vertical
        self.preview = TimelinePreview({}, self.total_duration)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.preview)
        self.layout.addWidget(self.scroll_area)
        
        self.save_btn = QPushButton("Guardar Configuración")
        self.save_btn.clicked.connect(self.save_config)
        self.layout.addWidget(self.save_btn)
        
        self.setLayout(self.layout)
        self.update_preview()
    
    def update_preview(self):
        try:
            self.total_duration = float(self.total_duration_edit.text())
        except ValueError:
            self.total_duration = 30.0
        self.timeline_config = {}
        max_end = 0.0
        for (id_, typ, subtype, start_edit, end_edit, default_duration) in self.fields:
            try:
                start = float(start_edit.text())
                val = float(end_edit.text())
            except ValueError:
                start = 0.0
                val = 0.0
            if typ.lower() == "dynamic" or (typ.lower() == "static" and subtype.lower() != "video"):
                end = val
                cfg = {"start": start, "end": end}
            else:
                # Para static video, el valor ingresado es la duración, que no puede exceder default_duration.
                if default_duration is not None and val > default_duration:
                    val = default_duration
                    end_edit.setText(str(default_duration))
                end = start + val
                cfg = {"start": start, "end": end}
                cfg["recortado"] = (val < default_duration) if default_duration is not None else False
            self.timeline_config[id_] = cfg
            if end > max_end:
                max_end = end
        # Si el máximo final supera la duración total, se actualiza la duración total.
        if max_end > self.total_duration:
            self.total_duration = max_end
            self.total_duration_edit.setText(str(max_end))
        self.preview.total_duration = self.total_duration
        self.preview.timeline_config = self.timeline_config
        self.preview.setDynamicHeight(len(self.timeline_config))
        self.preview.setDynamicWidth(self.total_duration)
        self.preview.update()
    
    def save_config(self):
        self.update_preview()
        print("Configuración del timeline:", self.timeline_config)
        self.config = {"total_duration": self.total_duration, "elements": self.timeline_config}
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Ejemplo de elementos:
    # Para elementos dinámicos y static (texto/imagen) se usan por defecto start=0 y end=5.
    # Para static video se usa la ruta, y se extrae la duración.
    timeline_items = [
        {"id": "elemento1", "component": "Texto Principal", "type": "dynamic"},
        {"id": "elemento2", "component": "Imagen Estática", "type": "static", "subtype": "imagen"},
        {"id": "elemento3", "component": "Video Estático", "type": "static", "subtype": "video",
         "video_path": r"app\Resources\AlternativeQuiz\Videos\Vertical _ Minecraft Parkour _ 5 Minutes No Copyright Gameplay _ 8 720.mp4"},
        {"id": "elemento4", "component": "Imagen Estática", "type": "static", "subtype": "imagen"},
        {"id": "elemento5", "component": "Texto Principal", "type": "dynamic"},
        {"id": "elemento6", "component": "Imagen Estática", "type": "static", "subtype": "imagen"}
    ]
    editor = TimelineConfigEditor(timeline_items, total_duration=30)
    editor.show()
    sys.exit(app.exec_())
