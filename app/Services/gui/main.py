# main.py
import sys
from PyQt5.QtWidgets import QApplication
from FolderSelector import FolderSelector
from LayoutDesigner import LayoutDesigner
from ComponentEditor import ComponentEditor
from TimelineEditor import TimelineConfigEditor

def main():
    app = QApplication(sys.argv)
    
    # Paso 1: Seleccionar carpetas de background
    folder_selector = FolderSelector()
    folder_selector.show()
    app.exec_()  # Espera a que se cierre
    if not hasattr(folder_selector, "config"):
        print("No se completó la selección de carpetas.")
        sys.exit(1)
    config_folders = folder_selector.config
    print("Carpetas seleccionadas:", config_folders)
    
    # Paso 2: Diseñar el layout
    layout_designer = LayoutDesigner()
    layout_designer.show()
    app.exec_()
    if not hasattr(layout_designer, "config"):
        print("No se completó el diseño del layout.")
        sys.exit(1)
    config_layout = layout_designer.config
    print("Layout configurado:", config_layout)
    
    # Paso 3: Editor de Componentes
    sections = config_layout.get("layout_sections", [])
    component_editor = ComponentEditor(sections)
    component_editor.show()
    app.exec_()
    if not hasattr(component_editor, "config"):
        print("No se completó la edición de componentes.")
        sys.exit(1)
    config_components = component_editor.config
    print("Componentes configurados:", config_components)
    
    # Paso 4: Editor de Línea de Tiempo
    # Construir timeline_items a partir de los componentes. Como el output de ComponentEditor no incluye tiempos,
    # asignamos valores por defecto:
    # - Para elementos dinámicos y para static (texto/imagen): start=0, end=5.
    # - Para static video: start=0, y se usará la ruta (video_path) para extraer la duración en el TimelineConfigEditor.
    timeline_items = []
    for sec_id, comp in config_components.items():
        print("Componente:", sec_id, comp)
        item = {"id": sec_id, "component": comp["type"]}
        if comp["static"] and comp["type"].lower() == "video":
            item["type"] = "static"
            item["subtype"] = "video"
            item["video_path"] = comp["value"]
            item["start"] = 0.0
            # No se define "end": el TimelineConfigEditor lo determinará a partir de la duración del video.
        else:
            # Para los demás, asignamos start=0 y end=5 (duración por defecto de 5 segundos).
            item["start"] = 0.0
            item["end"] = 5.0
            if comp["static"]:
                item["subtype"] = "imagen"  # Asumimos que static no video es imagen.
            else:
                item["type"] = "dynamic"
        timeline_items.append(item)
    
    # Asumamos una duración total inicial del video (por ejemplo, 30 segundos). Esto se podrá modificar en el TimelineConfigEditor.
    total_duration = 30.0
    
    timeline_editor = TimelineConfigEditor(timeline_items, total_duration)
    timeline_editor.show()
    app.exec_()
    if not hasattr(timeline_editor, "config"):
        print("No se completó la configuración del timeline.")
        sys.exit(1)
    config_timeline = timeline_editor.config
    print("Timeline configurado:", config_timeline)
    
    # Combinar toda la configuración en un solo diccionario final.
    final_config = {}
    final_config.update(config_folders)
    final_config.update(config_layout)
    final_config["components"] = config_components
    final_config["timeline"] = config_timeline
    
    print("Configuración final:")
    print(final_config)
    
    # Aquí podrías, por ejemplo, generar el script final o llamar a la función que renderice el video usando final_config.
    
    sys.exit(0)

if __name__ == '__main__':
    main()
