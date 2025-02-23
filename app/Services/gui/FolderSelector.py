# FolderSelector.py
import sys, os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout

class FolderSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Selecciona Carpetas de Background")
        
        # Etiquetas y campos de texto para video y audio
        video_label = QLabel("Carpeta de Video de Fondo:")
        self.video_edit = QLineEdit()
        video_btn = QPushButton("Examinar...")
        video_btn.clicked.connect(self.select_video_folder)
        
        audio_label = QLabel("Carpeta de Audio de Fondo:")
        self.audio_edit = QLineEdit()
        audio_btn = QPushButton("Examinar...")
        audio_btn.clicked.connect(self.select_audio_folder)
        
        # Botón para continuar
        next_btn = QPushButton("Siguiente")
        next_btn.clicked.connect(self.proceed)
        
        # Layouts horizontales
        video_layout = QHBoxLayout()
        video_layout.addWidget(video_label)
        video_layout.addWidget(self.video_edit)
        video_layout.addWidget(video_btn)
        
        audio_layout = QHBoxLayout()
        audio_layout.addWidget(audio_label)
        audio_layout.addWidget(self.audio_edit)
        audio_layout.addWidget(audio_btn)
        
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.addLayout(video_layout)
        main_layout.addLayout(audio_layout)
        main_layout.addWidget(next_btn)
        
        self.setLayout(main_layout)
    
    def select_video_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecciona Carpeta de Video")
        if folder:
            self.video_edit.setText(folder)
    
    def select_audio_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecciona Carpeta de Audio")
        if folder:
            self.audio_edit.setText(folder)
    
    def proceed(self):
        video_folder = self.video_edit.text()
        audio_folder = self.audio_edit.text()
        if not os.path.isdir(video_folder) or not os.path.isdir(audio_folder):
            print("Por favor, selecciona carpetas válidas.")
            return
        # Guardar la configuración
        self.config = {"bg_video_dir": video_folder, "bg_audio_dir": audio_folder}
        print("Configuración seleccionada:", self.config)
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    selector = FolderSelector()
    selector.show()
    sys.exit(app.exec_())
