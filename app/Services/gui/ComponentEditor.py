# ComponentEditor.py
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QComboBox, QLineEdit, QPushButton,
                             QCheckBox, QFormLayout, QVBoxLayout, QMessageBox, QHBoxLayout)

class ComponentEditor(QWidget):
    def __init__(self, sections):
        """
        sections: lista de diccionarios de secciones, cada uno con al menos la clave "id".
        """
        super().__init__()
        self.sections = sections
        self.setWindowTitle("Editor de Componentes para cada Sección")
        self.initUI()
    
    def initUI(self):
        self.layout = QVBoxLayout()
        
        # Creamos un formulario para cada sección
        self.form = QFormLayout()
        self.section_fields = []  # Guardaremos para cada sección: (section_id, combo, line_edit, checkbox)
        for sec in self.sections:
            # Crear QComboBox para seleccionar tipo
            combo = QComboBox()
            combo.addItems(["-- Seleccionar --", "Texto", "Imagen", "GIF", "Video"])
            
            # Campo QLineEdit para valor, con placeholder inicial para "identificador"
            line_edit = QLineEdit()
            line_edit.setPlaceholderText("Seleccione el identificador (ej. general_text)")
            
            # Checkbox para marcar si es estático
            checkbox = QCheckBox("Estático")
            # Conectar el cambio del checkbox para actualizar el placeholder
            checkbox.toggled.connect(lambda checked, le=line_edit: le.setPlaceholderText(
                "Seleccione la ruta" if checked else "Seleccione el identificador (ej. tal)"
            ))
            
            # Layout horizontal para combinar combo, line_edit y checkbox
            h_layout = QHBoxLayout()
            h_layout.addWidget(combo)
            h_layout.addWidget(line_edit)
            h_layout.addWidget(checkbox)
            
            label = QLabel(f"Sección {sec['id']}:")
            self.form.addRow(label, h_layout)
            self.section_fields.append((sec["id"], combo, line_edit, checkbox))
        
        self.layout.addLayout(self.form)
        
        # Botón para continuar
        self.next_btn = QPushButton("Siguiente")
        self.next_btn.clicked.connect(self.proceed)
        self.layout.addWidget(self.next_btn)
        
        self.setLayout(self.layout)
    
    def proceed(self):
        # Recolectar la configuración de cada sección
        config_components = {}
        for sec_id, combo, line_edit, checkbox in self.section_fields:
            comp_type = combo.currentText()
            comp_value = line_edit.text().strip()
            is_static = checkbox.isChecked()
            # Solo guardar si se ha seleccionado un tipo válido
            if comp_type == "-- Seleccionar --":
                continue
            config_components[sec_id] = {
                "type": comp_type,
                "static": is_static,
                "value": comp_value
            }
        if not config_components:
            QMessageBox.warning(self, "Error", "Debe asignar al menos un componente.")
            return
        QMessageBox.information(self, "Componentes Configurados", f"Configuración:\n{config_components}")
        self.config = config_components
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Ejemplo de secciones simuladas
    sections = [
        {"id": "div_1", "x": 0, "y": 0, "w": 240, "h": 320},
        {"id": "div_2", "x": 240, "y": 0, "w": 240, "h": 320},
        {"id": "div_3", "x": 480, "y": 0, "w": 240, "h": 320},
        {"id": "div_4", "x": 0, "y": 320, "w": 240, "h": 320},
        {"id": "div_5", "x": 240, "y": 320, "w": 240, "h": 320},
        {"id": "div_6", "x": 480, "y": 320, "w": 240, "h": 320}
    ]
    editor = ComponentEditor(sections)
    editor.show()
    sys.exit(app.exec_())
