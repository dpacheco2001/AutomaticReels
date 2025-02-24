import os
import random
import cv2
import numpy as np
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip


def draw_text_centered(img, text, center_x, center_y, font=cv2.FONT_HERSHEY_DUPLEX,
                       font_scale=1.0, color=(255, 255, 255), thickness=2, outline_color=(0, 0, 0)):
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    text_x = center_x - text_size[0] // 2
    text_y = center_y + text_size[1] // 2
    cv2.putText(img, text, (text_x, text_y), font, font_scale, outline_color, thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)


def create_text_image(text, width, height, font_scale=1.2, text_color=(255, 255, 255), outline_color=(0, 0, 0)):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (0, 0, 0)
    draw_text_centered(img, text, width // 2, height // 2,
                       font_scale=font_scale, color=text_color, outline_color=outline_color)
    return img


def get_random_file(directory, extensions):
    """ Devuelve una ruta de archivo aleatoria dentro de 'directory' 
        con alguna de las extensiones indicadas en 'extensions'. """
    if not os.path.isdir(directory):
        return None
    files = [f for f in os.listdir(directory) if f.lower().endswith(extensions)]
    return os.path.join(directory, random.choice(files)) if files else None


def generar_video(**kwargs):
    """
    - Se asume que las posiciones definidas en "layout_sections" + "offset"
      son coordenadas en las que queremos que el ELEMENTO esté CENTRADO.
    - Ajustamos la posición del clip para que MoviePy lo dibuje centrado en ese punto.
    """

    # Config de ejemplo (ajústala según tus necesidades)
    config = {
        "bg_audio_dir": "app/Resources/AlternativeQuiz/Sounds/backgrounds",
        "bg_visual_dir": "app/Resources/AlternativeQuiz/Videos",
        "layout_sections": [
            {"id": "div_1", "x": 0.0, "y": 0.0, "w": 360.0, "h": 960.0},
            {"id": "div_5", "x": 360.0, "y": 960.0, "w": 360.0, "h": 960.0}
        ],
        "elements": [
            {
                "id": "header",
                "div": "div_1",
                "offset": {"x": 500.0, "y": 500.0},
                "segments": [
                    {
                        "id": "hello_world",
                        "static": True,
                        "start": 0.0,
                        "end": 5.0,
                        "content_type": "Texto",
                        "value": "Hello World",
                        "text_color": (255, 0, 255)
                    },
                    {
                        "id": "hola_mundo",
                        "static": True,
                        "start": 5.0,
                        "end": 10.0,
                        "content_type": "Texto",
                        "value": "¡Hola mundo!",
                        "text_color": (255, 0, 127)
                    }
                ]
            },
            {
                "id": "logo",
                "div": "div_5",
                "offset": {"x": 170.0, "y": 5.0},
                "segments": [
                    {
                        "id": "play_station",
                        "static": True,
                        "start": 3.0,
                        "end": 4.0,
                        "content_type": "Imagen",
                        "value": "app/Resources/AlternativeQuiz/adelante.png"
                    }
                ]
            }
        ]
    }

    # 1) Determina la duración máxima requerida (según los segmentos)
    max_end = 0
    for elem in config["elements"]:
        for seg in elem["segments"]:
            if seg["end"] > max_end:
                max_end = seg["end"]

    # 2) Obtén rutas del video y audio de fondo
    bg_video_path = get_random_file(config["bg_visual_dir"], (".mp4", ".avi", ".mov"))
    bg_audio_path = get_random_file(config["bg_audio_dir"], (".mp3", ".wav"))

    if not bg_video_path or not bg_audio_path:
        raise FileNotFoundError("No se encontró un video o audio de fondo en los directorios especificados.")

    # 3) Carga el video y audio de fondo y recórtalos para no procesar más allá de 'max_end'
    bg_video = VideoFileClip(bg_video_path).subclipped(0, max_end).resized((1080, 1920))
    bg_audio = AudioFileClip(bg_audio_path).subclipped(0, max_end)

    # Asignamos audio al clip de video de fondo
    bg_video = bg_video.with_audio(bg_audio)

    # Crearemos la lista de clips que se superpondrán
    clips = [bg_video]

    # 4) Diccionario { 'div_id': (x, y) } con las posiciones base
    div_positions = {div["id"]: (div["x"], div["y"]) for div in config["layout_sections"]}

    # 5) Iterar sobre cada elemento y sus segmentos
    for element in config["elements"]:
        div_x, div_y = div_positions[element["div"]]
        offset_x, offset_y = element["offset"]["x"], element["offset"]["y"]

        for segment in element["segments"]:
            start, end = segment["start"], segment["end"]
            content_type = segment["content_type"]
            value = segment["value"]

            # Reemplazo dinámico si no es estático
            if not segment["static"] and segment["id"] in kwargs:
                value = kwargs[segment["id"]]

            # Calculamos la posición 'center' final:
            center_final_x = div_x + offset_x
            center_final_y = div_y + offset_y
            # NOTA:  Este 'center_final_x, center_final_y' será el centro del clip.

            if content_type == "Texto":
                # Creamos la imagen con OpenCV
                text_img = create_text_image(
                    text=value,
                    width=360,
                    height=100,
                    text_color=segment["text_color"]
                )
                # ImageClip a partir de la imagen
                txt_clip = ImageClip(text_img)

                # Obtenemos dimensiones del clip
                clip_w, clip_h = txt_clip.size  # (width, height)

                # Ajustar la posición de modo que 'center_final_x, center_final_y' sea el centro
                pos_x = center_final_x - (clip_w / 2)
                pos_y = center_final_y - (clip_h / 2)

                txt_clip = (
                    txt_clip.with_position((pos_x, pos_y))
                            .with_start(start)
                            .with_end(end)
                )
                clips.append(txt_clip)

            elif content_type == "Imagen":
                # Validar ruta
                if os.path.exists(value):
                    img_clip = ImageClip(value)
                    clip_w, clip_h = img_clip.size

                    pos_x = center_final_x - (clip_w / 2)
                    pos_y = center_final_y - (clip_h / 2)

                    img_clip = (
                        img_clip.with_position((pos_x, pos_y))
                                .with_start(start)
                                .with_end(end)
                    )
                    clips.append(img_clip)

    # 6) Creamos el compuesto final
    final_video = CompositeVideoClip(clips, size=(1080, 1920))

    # 7) Guardamos el resultado
    output_path = "output_video.mp4"
    final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

    return output_path


# Ejemplo de uso:
if __name__ == "__main__":
    # Aquí se cambia "hello_world" para un segmento dinámico.
    # (En este caso, "hello_world" es estático, pero es sólo ejemplo de cómo se llamaría).
    video_generado = generar_video(hello_world="Nuevo mensaje dinámico")
    print(f"Video generado en: {video_generado}")
