import subprocess
import sys
import os

def upload_video(title: str):
    """
    Llama al script cli.py del proyecto TiktokAutoUploader usando el venv de ese proyecto.
    Parámetros fijos:
      - Usuario: "my_saved_username"
      - Ruta del video: "app\Resources\RatherThan\VideosTests\final_with_animated_clock.mp4"
    Se asume que cli.py y config.txt se encuentran en D:\PythonProjects\TiktokAutoUploader
    """
    # Parámetros fijos
    user = "my_saved_username"
    video_path = r"final_with_animated_clock.mp4"

    # Ruta del intérprete de Python del venv de TiktokAutoUploader
    venv_python = r"D:\PythonProjects\TiktokAutoUploader\.venv\Scripts\python.exe"

    # Ruta al script cli.py en el proyecto TiktokAutoUploader
    cli_script = os.path.join(r"D:\PythonProjects\TiktokAutoUploader", "cli.py")
    if not os.path.exists(cli_script):
        raise FileNotFoundError(f"No se encontró 'cli.py' en {cli_script}")

    # Construir el comando
    cmd = [
        venv_python,
        cli_script,
        "upload",
        "--user", user,
        "-v", video_path,
        "-t", title
    ]
    
    print("Ejecutando comando:")
    print(" ".join(cmd))
    
    # Directorio de trabajo donde se encuentra config.txt
    cwd = r"D:\PythonProjects\TiktokAutoUploader"
    subprocess.run(cmd, check=True, cwd=cwd)

# Ejemplo de uso:
if __name__ == "__main__":
    # Llama a la función pasando el título del video
    upload_video("test #ratherthan #monetizar #parati #automatico #wouldyourather")
