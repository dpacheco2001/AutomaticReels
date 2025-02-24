import sys, os, json, math
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QSpinBox, QDoubleSpinBox, QFormLayout, QMessageBox,
    QComboBox, QCheckBox, QScrollArea, QListWidget, QListWidgetItem,
    QSplitter, QGroupBox
)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QRectF
from moviepy import VideoFileClip


class ElementPreviewWidget(QWidget):
    def __init__(self, layout_sections, parent=None):
        super().__init__(parent)
        self.layout_sections = layout_sections 
        self.current_div_id = None
        self.offset_x = 0
        self.offset_y = 0
        self.setFixedSize(270, 480)  

    def set_data(self, div_id, offset_x, offset_y):
        self.current_div_id = div_id
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240,240,240))
        scale = min(self.width()/1080, self.height()/1920)
        pen = QPen(QColor(0,0,0))
        pen.setWidth(2)
        painter.setPen(pen)
        for div in self.layout_sections:
            x = div["x"] * scale
            y = div["y"] * scale
            w = div["w"] * scale
            h = div["h"] * scale
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.drawText(int(x)+5, int(y)+20, div["id"])
        if self.current_div_id:
            for div in self.layout_sections:
                if div["id"] == self.current_div_id:
                    pen = QPen(QColor(255,0,0))
                    pen.setWidth(3)
                    painter.setPen(pen)
                    x = div["x"] * scale
                    y = div["y"] * scale
                    w = div["w"] * scale
                    h = div["h"] * scale
                    painter.drawRect(int(x), int(y), int(w), int(h))
                    pos_x = (div["x"] + self.offset_x) * scale
                    pos_y = (div["y"] + self.offset_y) * scale
                    painter.setBrush(QColor(255,0,0))
                    painter.drawEllipse(int(pos_x)-5, int(pos_y)-5, 10, 10)
                    painter.drawText(int(pos_x)+8, int(pos_y), f"Centro elemento")
                    break


class FolderSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seleccionar Fondos")
        self.audio_label = QLabel("Carpeta de Audio:")
        self.audio_edit = QLineEdit("app/Resources/AlternativeQuiz/Sounds/backgrounds")
        self.audio_btn = QPushButton("Examinar...")
        self.audio_btn.clicked.connect(self.select_audio)
        self.visual_label = QLabel("Carpeta de Imagen/Video de Fondo:")
        self.visual_edit = QLineEdit("app/Resources/AlternativeQuiz/Videos")
        self.visual_btn = QPushButton("Examinar...")
        self.visual_btn.clicked.connect(self.select_visual)
        self.next_btn = QPushButton("Siguiente")
        self.next_btn.clicked.connect(self.proceed)
        la = QHBoxLayout()
        la.addWidget(self.audio_label)
        la.addWidget(self.audio_edit)
        la.addWidget(self.audio_btn)
        lv = QHBoxLayout()
        lv.addWidget(self.visual_label)
        lv.addWidget(self.visual_edit)
        lv.addWidget(self.visual_btn)
        main_layout = QVBoxLayout()
        main_layout.addLayout(la)
        main_layout.addLayout(lv)
        main_layout.addWidget(self.next_btn)
        self.setLayout(main_layout)
    def select_audio(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Audio")
        if folder: self.audio_edit.setText(folder)
    def select_visual(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Imagen/Video")
        if folder: self.visual_edit.setText(folder)
    def proceed(self):
        audio = self.audio_edit.text()
        visual = self.visual_edit.text()
        if not os.path.isdir(audio) or not os.path.isdir(visual):
            QMessageBox.warning(self, "Error", "Seleccione carpetas válidas.")
            return
        self.config = {"bg_audio_dir": audio, "bg_visual_dir": visual}
        self.close()


class LayoutPreview(QWidget):
    def __init__(self, sections, canvas_width=1080, canvas_height=1920, parent=None):
        super().__init__(parent)
        self.sections = sections
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.setFixedSize(int(canvas_width/2), int(canvas_height/2))
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(230,230,230))
        scale_x = self.width()/self.canvas_width
        scale_y = self.height()/self.canvas_height
        pen = QPen(QColor(0,0,0)); pen.setWidth(2); painter.setPen(pen)
        for sec in self.sections:
            x = sec["x"] * scale_x
            y = sec["y"] * scale_y
            w = sec["w"] * scale_x
            h = sec["h"] * scale_y
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.drawText(int(x)+5, int(y)+20, sec["id"])
            
class LayoutDesigner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diseñador de Layout (1080x1920)")
        self.sections = []
        self.initUI()
    def initUI(self):
        self.num_label = QLabel("Número de Divisiones:")
        self.num_spin = QSpinBox(); self.num_spin.setMinimum(1); self.num_spin.setMaximum(20); self.num_spin.setValue(4)
        self.gen_btn = QPushButton("Generar Layout"); self.gen_btn.clicked.connect(self.generate_layout)
        top_layout = QHBoxLayout(); top_layout.addWidget(self.num_label); top_layout.addWidget(self.num_spin); top_layout.addWidget(self.gen_btn)
        self.preview_container = QVBoxLayout()
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setFixedHeight(250)
        self.preview_container.addWidget(self.preview_scroll)
        self.form = QFormLayout()
        self.next_btn = QPushButton("Siguiente"); self.next_btn.clicked.connect(self.proceed)
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(self.preview_container)
        main_layout.addLayout(self.form)
        main_layout.addWidget(self.next_btn)
        self.setLayout(main_layout)
    def generate_layout(self):
        n = self.num_spin.value(); cols = math.ceil(math.sqrt(n)); rows = math.ceil(n/cols)
        canvas_w = 1080; canvas_h = 1920; cell_w = canvas_w/cols; cell_h = canvas_h/rows
        self.sections = []
        for i in range(n):
            r = i // cols; c = i % cols
            sec = {"id": f"div_{i+1}", "x": c*cell_w, "y": r*cell_h, "w": cell_w, "h": cell_h}
            self.sections.append(sec)
        if hasattr(self, "preview"): self.preview.setParent(None)
        self.preview = LayoutPreview(self.sections, canvas_w, canvas_h)
        self.preview_scroll.setWidget(self.preview)
        while self.form.count() > 0:
            self.form.removeRow(0)
        self.id_edits = []
        for i, sec in enumerate(self.sections):
            edit = QLineEdit(sec["id"])
            self.form.addRow(f"ID para div {i+1}:", edit)
            self.id_edits.append(edit)
    def proceed(self):
        for i, edit in enumerate(self.id_edits):
            self.sections[i]["id"] = edit.text()
        self.config = {"layout_sections": self.sections}
        self.close()


class TimelineGlobalWidget(QWidget):
    def __init__(self, elements_data, parent=None):
        super().__init__(parent)
        self.elements_data = elements_data
        self.setMinimumHeight(80)
    def set_data(self, data):
        self.elements_data = data; self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(245,245,245))
        overall_duration = 0
        for elem in self.elements_data:
            for seg in elem.get("segments", []):
                overall_duration = max(overall_duration, seg.get("end", 0))
        if overall_duration <= 0: overall_duration = 30
        w = self.width()
        if overall_duration <= 30: tick_interval = 1
        elif overall_duration <= 60: tick_interval = 5
        else: tick_interval = 10
        tick_spacing = w/overall_duration
        pen = QPen(QColor(0,0,0)); painter.setPen(pen)
        for sec in range(0, int(overall_duration)+1, tick_interval):
            x = sec*tick_spacing; painter.drawLine(int(x), 0, int(x), 10)
            painter.setFont(QFont("Arial", 8)); painter.drawText(int(x)+2, 20, f"{sec}s")
        row_height = 30
        for i, elem in enumerate(self.elements_data):
            y_offset = 30 + i*row_height; painter.setFont(QFont("Arial", 10))
            painter.drawText(2, y_offset+20, elem.get("id", ""))
            for seg in elem.get("segments", []):
                s = seg.get("start", 0); e = seg.get("end", 0)
                seg_w = ((e-s)/overall_duration)*w; x = (s/overall_duration)*w
                rect = QRectF(x, y_offset, seg_w, row_height-5)
                painter.fillRect(rect, QColor(100,150,200)); painter.drawRect(rect)
                painter.drawText(int(x)+2, int(y_offset)+15, seg.get("id", ""))


class ElementEditorNew(QWidget):
    def __init__(self, layout_config):
        super().__init__()
        self.setWindowTitle("Editor de Elementos")
        self.div_ids = [d["id"] for d in layout_config.get("layout_sections", [])]
        self.layout_sections = layout_config.get("layout_sections", [])
        self.elements_data = []  
        self.initUI()
    def initUI(self):
        self.main_layout = QVBoxLayout()
        self.splitter = QSplitter(Qt.Horizontal)
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.load_element)
        self.splitter.addWidget(self.list_widget)
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout()
        self.elem_group = QGroupBox("Datos del Elemento")
        elem_form = QFormLayout()
        self.elem_id_edit = QLineEdit()
        self.div_combo = QComboBox(); self.div_combo.addItems(self.div_ids)
        self.offset_x_spin = QDoubleSpinBox(); self.offset_x_spin.setRange(0,10000)
        self.offset_y_spin = QDoubleSpinBox(); self.offset_y_spin.setRange(0,10000)
        elem_form.addRow("ID Elemento:", self.elem_id_edit)
        elem_form.addRow("Div:", self.div_combo)
        elem_form.addRow("Offset X:", self.offset_x_spin)
        elem_form.addRow("Offset Y:", self.offset_y_spin)
        self.elem_group.setLayout(elem_form)
        self.detail_layout.addWidget(self.elem_group)
        self.preview_group = QGroupBox("Vista de Posición")
        self.elem_preview = ElementPreviewWidget(self.layout_sections)
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.elem_preview)
        self.preview_group.setLayout(preview_layout)
        self.detail_layout.addWidget(self.preview_group)
        self.seg_group = QGroupBox("Segmentos")
        seg_layout = QHBoxLayout()
        self.seg_list = QListWidget()
        self.seg_list.currentRowChanged.connect(self.load_segment)
        seg_layout.addWidget(self.seg_list)
        seg_form = QFormLayout()
        self.seg_id_edit = QLineEdit()
        self.seg_static_checkbox = QCheckBox("Estático"); self.seg_static_checkbox.setChecked(True)
        self.seg_static_checkbox.toggled.connect(lambda ch: self.seg_value_edit.setEnabled(ch))
        self.seg_start_spin = QDoubleSpinBox(); self.seg_start_spin.setRange(0,10000); self.seg_start_spin.setDecimals(2); self.seg_start_spin.setSingleStep(0.1)
        self.seg_end_spin = QDoubleSpinBox(); self.seg_end_spin.setRange(0,10000); self.seg_end_spin.setDecimals(2); self.seg_end_spin.setSingleStep(0.1)
        self.seg_type_combo = QComboBox(); self.seg_type_combo.addItems(["Texto", "Imagen", "GIF", "Video"])
        self.seg_value_edit = QLineEdit(); self.seg_value_edit.setPlaceholderText("Valor (texto o ruta)")
        self.seg_value_edit.editingFinished.connect(self.check_video_duration)
        seg_form.addRow("ID Segmento:", self.seg_id_edit)
        seg_form.addRow("Estático:", self.seg_static_checkbox)
        seg_form.addRow("Inicio (s):", self.seg_start_spin)
        seg_form.addRow("Fin (s):", self.seg_end_spin)
        seg_form.addRow("Tipo:", self.seg_type_combo)
        seg_form.addRow("Valor:", self.seg_value_edit)
        self.seg_detail_widget = QWidget()
        self.seg_detail_widget.setLayout(seg_form)
        seg_layout.addWidget(self.seg_detail_widget)

        seg_buttons_layout = QVBoxLayout()
        self.add_seg_btn = QPushButton("Agregar Segmento")
        self.add_seg_btn.clicked.connect(self.add_segment)
        self.del_seg_btn = QPushButton("Eliminar Segmento")
        self.del_seg_btn.clicked.connect(self.delete_segment)
        seg_buttons_layout.addWidget(self.add_seg_btn)
        seg_buttons_layout.addWidget(self.del_seg_btn)
        seg_layout.addLayout(seg_buttons_layout)
        self.seg_group.setLayout(seg_layout)
        self.detail_layout.addWidget(self.seg_group)
        self.update_elem_btn = QPushButton("Actualizar Elemento")
        self.update_elem_btn.clicked.connect(self.update_current_element)
        self.detail_layout.addWidget(self.update_elem_btn)
        self.detail_widget.setLayout(self.detail_layout)
        self.splitter.addWidget(self.detail_widget)
        self.splitter.setStretchFactor(0,1); self.splitter.setStretchFactor(1,2)
        self.main_layout.addWidget(self.splitter)
        self.add_elem_btn = QPushButton("Agregar Elemento")
        self.add_elem_btn.clicked.connect(self.add_element)
        self.main_layout.addWidget(self.add_elem_btn)
        self.global_timeline = TimelineGlobalWidget(self.elements_data)
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setWidget(self.global_timeline)
        self.main_layout.addWidget(QLabel("Línea de Tiempo Global:"))
        self.main_layout.addWidget(self.timeline_scroll)
        self.next_btn = QPushButton("Siguiente")
        self.next_btn.clicked.connect(self.finish)
        self.main_layout.addWidget(self.next_btn)
        self.setLayout(self.main_layout)
        self.div_combo.currentIndexChanged.connect(self.update_element_preview)
        self.offset_x_spin.valueChanged.connect(self.update_element_preview)
        self.offset_y_spin.valueChanged.connect(self.update_element_preview)
    def update_element_preview(self):
        div = self.div_combo.currentText()
        offset_x = self.offset_x_spin.value()
        offset_y = self.offset_y_spin.value()
        self.elem_preview.set_data(div, offset_x, offset_y)
    def add_element(self):
        new_elem = {
            "id": f"elemento_{len(self.elements_data)+1}",
            "div": self.div_ids[0] if self.div_ids else "",
            "offset": {"x": 0, "y": 0},
            "segments": [{
                "id": "seg1",
                "static": True,
                "start": 0,
                "end": 5,
                "content_type": "Texto",
                "value": ""
            }]
        }
        self.elements_data.append(new_elem)
        item = QListWidgetItem(new_elem["id"])
        self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(self.list_widget.count()-1)
        self.update_timeline()
    def load_element(self, index):
        if index < 0 or index >= len(self.elements_data): return
        elem = self.elements_data[index]
        self.elem_id_edit.setText(elem.get("id", ""))
        div = elem.get("div", self.div_ids[0] if self.div_ids else "")
        idx = self.div_ids.index(div) if div in self.div_ids else 0
        self.div_combo.setCurrentIndex(idx)
        self.offset_x_spin.setValue(elem.get("offset", {}).get("x", 0))
        self.offset_y_spin.setValue(elem.get("offset", {}).get("y", 0))
        self.update_element_preview()
        self.seg_list.clear()
        for seg in elem.get("segments", []):
            self.seg_list.addItem(seg.get("id", ""))
        if elem.get("segments", []):
            self.seg_list.setCurrentRow(0)
        else:
            self.add_segment()
    def load_segment(self, index):
        curr_elem = self.get_current_element()
        if not curr_elem or index < 0 or index >= len(curr_elem.get("segments", [])): return
        seg = curr_elem["segments"][index]
        self.seg_id_edit.setText(seg.get("id", ""))
        self.seg_static_checkbox.setChecked(seg.get("static", True))
        self.seg_start_spin.setValue(seg.get("start", 0))
        self.seg_end_spin.setValue(seg.get("end", 5))
        content_type = seg.get("content_type", "Texto")
        idx = self.seg_type_combo.findText(content_type)
        self.seg_type_combo.setCurrentIndex(idx if idx>=0 else 0)
        self.seg_value_edit.setText(seg.get("value", ""))
    def check_video_duration(self):
        if self.seg_static_checkbox.isChecked() and self.seg_type_combo.currentText() == "Video" and self.seg_value_edit.text():
            try:
                clip = VideoFileClip(self.seg_value_edit.text())
                dur = clip.duration
                clip.close()
                self.seg_end_spin.setValue(dur)
            except Exception:
                pass
        self.update_current_element()
    def update_current_element(self):
        index = self.list_widget.currentRow()
        if index < 0 or index >= len(self.elements_data): return
        elem = self.elements_data[index]
        elem["id"] = self.elem_id_edit.text()
        elem["div"] = self.div_combo.currentText()
        elem["offset"] = {"x": self.offset_x_spin.value(), "y": self.offset_y_spin.value()}
        seg_index = self.seg_list.currentRow()
        if seg_index >= 0 and seg_index < len(elem.get("segments", [])):
            seg = elem["segments"][seg_index]
            seg["id"] = self.seg_id_edit.text()
            seg["static"] = self.seg_static_checkbox.isChecked()
            seg["start"] = self.seg_start_spin.value()
            seg["end"] = self.seg_end_spin.value()
            seg["content_type"] = self.seg_type_combo.currentText()
            seg["value"] = self.seg_value_edit.text() if seg["static"] else ""
            self.seg_list.currentItem().setText(seg["id"])
        self.list_widget.currentItem().setText(elem["id"])
        self.update_timeline()
    def add_segment(self):
        index = self.list_widget.currentRow()
        if index < 0:
            if self.list_widget.count() > 0:
                index = 0
                self.list_widget.setCurrentRow(0)
            else:
                return
        elem = self.elements_data[index]
        new_seg = {
            "id": f"seg{len(elem.get('segments', []))+1}",
            "static": True,
            "start": 0,
            "end": 5,
            "content_type": "Texto",
            "value": ""
        }
        elem["segments"].append(new_seg)
        self.seg_list.addItem(new_seg["id"])
        self.seg_list.setCurrentRow(self.seg_list.count()-1)
        self.update_timeline()
    def delete_segment(self):
        index = self.list_widget.currentRow()
        seg_index = self.seg_list.currentRow()
        if index < 0 or seg_index < 0: return
        elem = self.elements_data[index]
        if len(elem["segments"]) <= 1:
            QMessageBox.warning(self, "Error", "Cada elemento debe tener al menos un segmento.")
            return
        del elem["segments"][seg_index]
        self.seg_list.takeItem(seg_index)
        if self.seg_list.count() > 0:
            self.seg_list.setCurrentRow(0)
        self.update_timeline()
    def get_current_element(self):
        index = self.list_widget.currentRow()
        if index < 0 or index >= len(self.elements_data): return None
        return self.elements_data[index]
    def update_timeline(self):
        self.global_timeline.set_data(self.elements_data)
    def finish(self):
        self.update_current_element()
        self.config = {"elements": self.elements_data}
        self.close()
    def showEvent(self, event):
        if self.list_widget.count() > 0:
            self.load_element(0)
        super().showEvent(event)

# --- Función Principal ---
def main():
    app = QApplication(sys.argv)
    fs = FolderSelector()
    fs.showMaximized()
    app.exec_()
    if not hasattr(fs, "config"): sys.exit(1)
    folders = fs.config
    ld = LayoutDesigner()
    ld.showMaximized()
    app.exec_()
    if not hasattr(ld, "config"): sys.exit(1)
    layout_conf = ld.config
    ee = ElementEditorNew(layout_conf)
    ee.showMaximized()
    app.exec_()
    if not hasattr(ee, "config"): sys.exit(1)
    elements_conf = ee.config
    final_config = {}
    final_config.update(folders)
    final_config.update(layout_conf)
    final_config.update(elements_conf)
    save_path = QFileDialog.getSaveFileName(None, "Guardar Configuración", "", "JSON Files (*.json)")[0]
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(final_config, f, indent=4)
    sys.exit(0)

if __name__ == "__main__":
    main()
