import cv2
import numpy as np
import os
import random
import glob
import math
import imageio
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, VideoClip

# ====================================================
# LAYOUT FIJO (posiciones y divs)
# ====================================================
# Aunque en el JSON se indican varios divs, usaremos únicamente la posición de "div_1" 
# como referencia global para calcular las coordenadas absolutas.
LAYOUT = {
    "bg_audio_dir": "app/Resources/AlternativeQuiz/Sounds/backgrounds",
    "bg_visual_dir": "app/Resources/AlternativeQuiz/Videos",
    "bg_voices_dir": r"app\Resources\AlternativeQuiz\Sounds\voices",
    "layout_sections": [
        {"id": "div_1", "x": 0,   "y": 0,   "w": 540, "h": 960},
        {"id": "div_2", "x": 540, "y": 0,   "w": 540, "h": 960},
        {"id": "div_3", "x": 0,   "y": 960, "w": 540, "h": 960},
        {"id": "div_4", "x": 540, "y": 960, "w": 540, "h": 960}
    ],
    "elements": [
        {
            "id": "header",
            "div": "div_1",  # No importa, usaremos siempre div_1
            "comments": "Título que aparece hasta el final del video",
            "segments": [
                {
                    "id": "titulo",
                    "offset": {"x": 270, "y": 50},  # Se interpretará como centro global (div_1 + offset)
                    "content_type": "Texto",
                    "effect": "Oscilación suave",
                    "text_color": "#000000",
                    "dura_hasta_el_final": True
                }
            ]
        },
        {
            "id": "lateral_column",
            "div": "div_1",
            "comments": "Columna lateral vertical (modos y viñetas)",
            "segments": [
                {
                    "id": "lateral_column",
                    "offset": {"x": 30, "y": 100},  # Usaremos div_1 como referencia
                    "content_type": "Texto",
                    "effect": "Sin efecto",
                    "dura_hasta_el_final": True
                }
            ]
        },
        {
            "id": "intro",
            "div": "div_1",
            "comments": "Texto e imagen que aparecen al inicio (duración = voice_intro)",
            "segments": [
                {
                    "id": "texto_intro",
                    "offset": {"x": 270, "y": 300},
                    "content_type": "Texto",
                    "effect": "Oscilación suave"
                },
                {
                    "id": "imagen_intro",
                    "offset": {"x": 270, "y": 500},
                    "content_type": "Imagen",
                    "effect": "Oscilación suave"
                }
            ]
        },
        {
            "id": "contenido",
            "div": "div_1",
            "comments": "Modos y viñetas (logo, text_logo, cronómetro, etc.)",
            "segments": [
                {
                    "id": "texto_modo",
                    "offset": {"x": 270, "y": 100},
                    "content_type": "Texto",
                    "effect": "Oscilación suave",
                    "text_color": "#ffffff"
                },
                {
                    "id": "imagen_modo",
                    "offset": {"x": 270, "y": 200},
                    "content_type": "Imagen",
                    "effect": "Oscilación suave"
                },
                {
                    "id": "logo",
                    "offset": {"x": 270, "y": 600},
                    "content_type": "Imagen",
                    "effect": "Oscilación suave"
                },
                {
                    "id": "text_logo",
                    "offset": {"x": 270, "y": 700},
                    "content_type": "Texto",
                    "effect": "Oscilación suave",
                    "text_color": "#ffffff"
                },
                {
                    "id": "cronometro",
                    "offset": {"x": 270, "y": 800},
                    "content_type": "GIF",
                    "effect": "Oscilación suave"
                }
            ]
        }
    ]
}

# ====================================================
# FUNCIONES AUXILIARES
# ====================================================

def superponer_imagen(base, overlay, x, y):
    h_base, w_base = base.shape[:2]
    h_over, w_over = overlay.shape[:2]
    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + w_over, w_base)
    y2 = min(y + h_over, h_base)
    if x1 >= x2 or y1 >= y2:
        return base
    dx1 = x1 - x
    dy1 = y1 - y
    dx2 = dx1 + (x2 - x1)
    dy2 = dy1 + (y2 - y1)
    overlay_cropped = overlay[dy1:dy2, dx1:dx2]
    if overlay_cropped.shape[2] == 4:
        alpha = overlay_cropped[:, :, 3] / 255.0
        overlay_cropped = overlay_cropped[:, :, :3]
    else:
        alpha = np.ones((y2 - y1, x2 - x1), dtype=np.float32)
    roi = base[y1:y2, x1:x2]
    for c in range(3):
        roi[:, :, c] = roi[:, :, c] * (1 - alpha) + overlay_cropped[:, :, c] * alpha
    return base

def resize_to_fit(img, max_width, max_height):
    h, w = img.shape[:2]
    scale = min(max_width / w, max_height / h)
    if scale < 1:
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img

def hex_to_bgr(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (b, g, r)
    except:
        pass
    return (255, 255, 255)

def draw_text_custom(frame, text, center_x, center_y, font_scale, color, thickness=2):
    # Dibuja el texto centrado en (center_x, center_y)
    font = cv2.FONT_HERSHEY_SIMPLEX
    (w, h), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = int(center_x - w/2)
    y = int(center_y + h/2)
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)

def draw_vertical_text(frame, text_lines, start_x, start_y, font_scale, color, line_spacing):
    # Dibuja cada línea centrada horizontalmente en start_x, comenzando en start_y y separadas por line_spacing
    y = start_y
    for line in text_lines:
        (w, h), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        x = int(start_x - w/2)
        cv2.putText(frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2, cv2.LINE_AA)
        y += line_spacing

def get_div_position(div_id):
    # Usamos únicamente la posición de "div_1" como referencia global
    # Si div_id es "div_1", se devuelve su posición; si es otro, igualmente se devuelve la posición de "div_1"
    for section in LAYOUT["layout_sections"]:
        if section["id"] == "div_1":
            return int(section["x"]), int(section["y"])
    return 0, 0

def get_absolute_position(element, seg_offset):
    # Ignoramos el campo "div" del elemento y siempre usamos "div_1" como base
    base_x, base_y = get_div_position("div_1")
    return base_x + int(seg_offset["x"]), base_y + int(seg_offset["y"])

# ====================================================
# FUNCIÓN make_frame: GENERA CADA FRAME (VideoClip)
# ====================================================
def make_frame(t):
    # El fondo: si es video, se obtiene y se redimensiona; si no, se usa la imagen
    if is_bg_video:
        frame = bg_video_clip.get_frame(t)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
    else:
        frame = bg_image.copy()
    if len(frame.shape) == 2 or frame.shape[2] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    active_events = [ev for ev in timeline if ev["start"] <= t < ev["end"]]
    
    # Dibujar header
    for elem in LAYOUT["elements"]:
        if elem["id"] == "header":
            for seg in elem["segments"]:
                if seg.get("dura_hasta_el_final", False):
                    offx, offy = get_absolute_position(elem, seg["offset"])
                    dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                    dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                    header_text = content_data.get("header_text", "QUIZ LOGOS")
                    draw_text_custom(frame, header_text, offx+dx, offy+dy, 1.0, hex_to_bgr(seg.get("text_color", "#FFFFFF")))
    
    # Dibujar columna lateral (después de intro)
    if t >= timeline[0]["end"]:
        for elem in LAYOUT["elements"]:
            if elem["id"] == "lateral_column":
                offx, offy = get_absolute_position(elem, elem["segments"][0]["offset"])
                draw_vertical_text(frame, lateral_lines, offx, offy, lateral_font_scale, lateral_color, lateral_line_spacing)
    
    # Dibujar intro
    if any(ev["type"] == "intro" for ev in active_events):
        for elem in LAYOUT["elements"]:
            if elem["id"] == "intro":
                for seg in elem["segments"]:
                    offx, offy = get_absolute_position(elem, seg["offset"])
                    dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                    dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                    if seg["content_type"] == "Texto":
                        draw_text_custom(frame, content_data["intro"]["texto_intro"], offx+dx, offy+dy, 1.0, (255,255,255))
                    elif seg["content_type"] == "Imagen" and os.path.isfile(content_data["intro"]["imagen_intro"]):
                        intro_img = cv2.imread(content_data["intro"]["imagen_intro"], cv2.IMREAD_UNCHANGED)
                        if intro_img is not None:
                            intro_img = resize_to_fit(intro_img, 200, 200)
                            tlx = offx - intro_img.shape[1]//2 + dx
                            tly = offy - intro_img.shape[0]//2 + dy
                            superponer_imagen(frame, intro_img, tlx, tly)
    
    # Dibujar contenido (modos y viñetas)
    for ev in active_events:
        if ev["type"] == "modo":
            modo_key = ev["modo_key"]
            modo_data = content_data["modos"][modo_key]
            for elem in LAYOUT["elements"]:
                if elem["id"] == "contenido":
                    for seg in elem["segments"]:
                        if seg["id"] == "texto_modo":
                            offx, offy = get_absolute_position(elem, seg["offset"])
                            dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                            dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                            draw_text_custom(frame, modo_data["texto_modo"], offx+dx, offy+dy, 0.8, hex_to_bgr(seg.get("text_color", "#FFFFFF")))
                        if seg["id"] == "imagen_modo" and os.path.isfile(modo_data["imagen_modo"]):
                            modo_img = cv2.imread(modo_data["imagen_modo"], cv2.IMREAD_UNCHANGED)
                            if modo_img is not None:
                                modo_img = resize_to_fit(modo_img, 200, 200)
                                offx, offy = get_absolute_position(elem, seg["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect") == "Oscilación suave" else 0
                                tlx = offx - modo_img.shape[1]//2 + dx
                                tly = offy - modo_img.shape[0]//2 + dy
                                superponer_imagen(frame, modo_img, tlx, tly)
        if ev["type"] in ["question", "cronometro", "answer"]:
            vigneta_key = ev["vigneta_key"]
            found_v = None
            for mk, md in content_data["modos"].items():
                if vigneta_key in md["viñetas"]:
                    found_v = md["viñetas"][vigneta_key]
                    break
            if not found_v:
                continue
            # Para "question", mostrar pregunta (logo y text_logo en blanco)
            if ev["type"] == "question":
                for elem in LAYOUT["elements"]:
                    if elem["id"] == "contenido":
                        seg_logo = next((s for s in elem["segments"] if s["id"] == "logo"), None)
                        if seg_logo and os.path.isfile(found_v["imagen_logo"]):
                            logo_img = cv2.imread(found_v["imagen_logo"], cv2.IMREAD_UNCHANGED)
                            if logo_img is not None:
                                logo_img = resize_to_fit(logo_img, 200, 200)
                                offx, offy = get_absolute_position(elem, seg_logo["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_logo.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_logo.get("effect")=="Oscilación suave" else 0
                                tlx = offx - logo_img.shape[1]//2 + dx
                                tly = offy - logo_img.shape[0]//2 + dy
                                superponer_imagen(frame, logo_img, tlx, tly)
                        seg_text_logo = next((s for s in elem["segments"] if s["id"] == "text_logo"), None)
                        if seg_text_logo:
                            offx, offy = get_absolute_position(elem, seg_text_logo["offset"])
                            dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                            dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                            draw_text_custom(frame, found_v["text_logo"], offx+dx, offy+dy, 0.8, (255,255,255))
            elif ev["type"] == "cronometro":
                for elem in LAYOUT["elements"]:
                    if elem["id"] == "contenido":
                        seg_crono = next((s for s in elem["segments"] if s["id"] == "cronometro"), None)
                        if seg_crono and cronometro_frames:
                            offx, offy = get_absolute_position(elem, seg_crono["offset"])
                            dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_crono.get("effect")=="Oscilación suave" else 0
                            dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_crono.get("effect")=="Oscilación suave" else 0
                            local_time = t - ev["start"]
                            gif_fps = len(cronometro_frames) / cronometro_duration
                            c_index = int(local_time * gif_fps) % len(cronometro_frames)
                            crono_img = resize_to_fit(cronometro_frames[c_index], 200, 200)
                            tlx = offx - crono_img.shape[1]//2 + dx
                            tly = offy - crono_img.shape[0]//2 + dy
                            superponer_imagen(frame, crono_img, tlx, tly)
            elif ev["type"] == "answer":
                # Durante answer, se muestra la respuesta (en verde) solo cuando está activa
                for elem in LAYOUT["elements"]:
                    if elem["id"] == "contenido":
                        seg_text_logo = next((s for s in elem["segments"] if s["id"] == "text_logo"), None)
                        if seg_text_logo:
                            offx, offy = get_absolute_position(elem, seg_text_logo["offset"])
                            dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                            dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                            draw_text_custom(frame, found_v["text_logo"], offx+dx, offy+dy, 0.8, (0,255,0))
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

# ====================================================
# FUNCIÓN PRINCIPAL: CREAR VIDEO FINAL
# ====================================================
def generate_tiktok_video(content_data, output_path="final_tiktok.mp4", fps=30):
    # Variables de referencia
    bg_voices_dir = LAYOUT["bg_voices_dir"]
    bg_audio_dir  = LAYOUT["bg_audio_dir"]
    bg_visual_dir = LAYOUT["bg_visual_dir"]

    # Ruta de voice_intro
    voice_intro_path = os.path.normpath(r"app\Resources\AlternativeQuiz\Sounds\voices\voice_intro.mp3")
    print("voice_intro_path:", voice_intro_path)
    if not os.path.isfile(voice_intro_path):
        raise FileNotFoundError(f"No se encontró la voz de intro en: {voice_intro_path}")
    intro_voice_clip = AudioFileClip(voice_intro_path)
    intro_duration = intro_voice_clip.duration
    cronometro_duration = 3.0
    cronometro_gif_path = content_data.get("cronometro_gif", r"app\Resources\AlternativeQuiz\clock_gif.gif")
    default_w, default_h = content_data.get("image_default_size", [200, 200])

    # Calcular duración total (suma de voces)
    total_duration = intro_duration
    modos = content_data["modos"]
    for modo_key, modo_data in modos.items():
        voice_modo_path = os.path.join(bg_voices_dir, f"voice_modo_{modo_key}.mp3")
        if os.path.isfile(voice_modo_path):
            modo_voice_clip = AudioFileClip(voice_modo_path)
            total_duration += modo_voice_clip.duration
            modo_voice_clip.close()
        for vigneta_key, _ in modo_data["viñetas"].items():
            q_path = os.path.join(bg_voices_dir, f"voice_question_{vigneta_key}.mp3")
            a_path = os.path.join(bg_voices_dir, f"voice_answer_{vigneta_key}.mp3")
            q_dur = AudioFileClip(q_path).duration if os.path.isfile(q_path) else 0.0
            a_dur = AudioFileClip(a_path).duration if os.path.isfile(a_path) else 0.0
            total_duration += (q_dur + cronometro_duration + a_dur)
    intro_voice_clip.close()

    total_frames = int(total_duration * fps)
    WIDTH, HEIGHT = 1080, 1920

    # Preparar background visual
    bg_visual_files = glob.glob(os.path.join(bg_visual_dir, "*"))
    if not bg_visual_files:
        raise ValueError(f"No se encontraron videos/imagenes en {bg_visual_dir}")
    bg_visual_choice = random.choice(bg_visual_files)
    is_bg_video = os.path.splitext(bg_visual_choice)[1].lower() in [".mp4", ".mov", ".avi", ".mkv"]
    if is_bg_video:
        bg_video_clip = VideoFileClip(bg_visual_choice).subclipped(0, total_duration)
    else:
        bg_image = cv2.imread(bg_visual_choice, cv2.IMREAD_COLOR)
        if bg_image is None:
            bg_image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        else:
            bg_image = cv2.resize(bg_image, (WIDTH, HEIGHT))

    # Cargar frames del GIF de cronómetro
    cronometro_frames = []
    if os.path.isfile(cronometro_gif_path):
        gif_frames = imageio.mimread(cronometro_gif_path)
        for frame in gif_frames:
            if frame.shape[2] == 4:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA)
            else:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cronometro_frames.append(frame_bgr)

    # Construir timeline de eventos
    timeline = []
    current_time = 0.0
    timeline.append({"type": "intro", "start": current_time, "end": current_time + intro_duration})
    current_time += intro_duration
    for modo_key, modo_data in modos.items():
        voice_modo_path = os.path.join(bg_voices_dir, f"voice_modo_{modo_key}.mp3")
        modo_dur = 0.0
        if os.path.isfile(voice_modo_path):
            modo_dur = AudioFileClip(voice_modo_path).duration
        timeline.append({"type": "modo", "modo_key": modo_key, "start": current_time, "end": current_time + modo_dur})
        current_time += modo_dur
        for vigneta_key, _ in modo_data["viñetas"].items():
            q_path = os.path.join(bg_voices_dir, f"voice_question_{vigneta_key}.mp3")
            a_path = os.path.join(bg_voices_dir, f"voice_answer_{vigneta_key}.mp3")
            q_dur = AudioFileClip(q_path).duration if os.path.isfile(q_path) else 0.0
            a_dur = AudioFileClip(a_path).duration if os.path.isfile(a_path) else 0.0
            timeline.append({"type": "question", "vigneta_key": vigneta_key, "start": current_time, "end": current_time + q_dur})
            current_time += q_dur
            timeline.append({"type": "cronometro", "vigneta_key": vigneta_key, "start": current_time, "end": current_time + cronometro_duration})
            current_time += cronometro_duration
            timeline.append({"type": "answer", "vigneta_key": vigneta_key, "start": current_time, "end": current_time + a_dur})
            current_time += a_dur

    # Configuración para la columna lateral
    lateral_lines = []
    for modo_key, modo_data in modos.items():
        lateral_lines.append(modo_data["texto_modo"].upper() + ":")
        for vigneta_key, vigneta_data in modo_data["viñetas"].items():
            lateral_lines.append(f"  {vigneta_key}) {vigneta_data['text_logo']}")
    lateral_font_scale = content_data.get("text_settings", {}).get("lateral_scale", 0.5)
    lateral_line_spacing = content_data.get("text_settings", {}).get("lateral_line_spacing", 40)
    lateral_color = (255, 255, 255)

    # Parámetros de oscilación
    osc_amplitude = 5
    osc_frequency = 0.5

    def get_events_at_time(t):
        active = []
        for ev in timeline:
            if ev["start"] <= t < ev["end"]:
                active.append(ev)
        return active

    # Definir la función make_frame (toda la generación se basa en el tiempo t)
    def make_frame(t):
        if is_bg_video:
            frame = bg_video_clip.get_frame(t)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
        else:
            frame = bg_image.copy()
        if len(frame.shape) == 2 or frame.shape[2] == 1:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        active_events = [ev for ev in timeline if ev["start"] <= t < ev["end"]]
        # Dibujar header
        for elem in LAYOUT["elements"]:
            if elem["id"] == "header":
                for seg in elem["segments"]:
                    if seg.get("dura_hasta_el_final", False):
                        offx, offy = get_absolute_position(elem, seg["offset"])
                        dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        header_text = content_data.get("header_text", "QUIZ LOGOS")
                        draw_text_custom(frame, header_text, offx+dx, offy+dy, 1.0, hex_to_bgr(seg.get("text_color", "#FFFFFF")))
        # Dibujar columna lateral (después de intro)
        if t >= timeline[0]["end"]:
            for elem in LAYOUT["elements"]:
                if elem["id"] == "lateral_column":
                    offx, offy = get_absolute_position(elem, elem["segments"][0]["offset"])
                    draw_vertical_text(frame, lateral_lines, offx, offy, lateral_font_scale, lateral_color, lateral_line_spacing)
        # Dibujar intro
        if any(ev["type"] == "intro" for ev in active_events):
            for elem in LAYOUT["elements"]:
                if elem["id"] == "intro":
                    for seg in elem["segments"]:
                        offx, offy = get_absolute_position(elem, seg["offset"])
                        dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        if seg["content_type"]=="Texto":
                            draw_text_custom(frame, content_data["intro"]["texto_intro"], offx+dx, offy+dy, 1.0, (255,255,255))
                        elif seg["content_type"]=="Imagen" and os.path.isfile(content_data["intro"]["imagen_intro"]):
                            intro_img = cv2.imread(content_data["intro"]["imagen_intro"], cv2.IMREAD_UNCHANGED)
                            if intro_img is not None:
                                intro_img = resize_to_fit(intro_img, 200, 200)
                                tlx = offx - intro_img.shape[1]//2 + dx
                                tly = offy - intro_img.shape[0]//2 + dy
                                superponer_imagen(frame, intro_img, tlx, tly)
        # Dibujar contenido (modos y viñetas)
        for ev in active_events:
            if ev["type"] == "modo":
                modo_key = ev["modo_key"]
                modo_data = content_data["modos"][modo_key]
                for elem in LAYOUT["elements"]:
                    if elem["id"] == "contenido":
                        for seg in elem["segments"]:
                            if seg["id"] == "texto_modo":
                                offx, offy = get_absolute_position(elem, seg["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                draw_text_custom(frame, modo_data["texto_modo"], offx+dx, offy+dy, 0.8, hex_to_bgr(seg.get("text_color", "#FFFFFF")))
                            if seg["id"] == "imagen_modo" and os.path.isfile(modo_data["imagen_modo"]):
                                modo_img = cv2.imread(modo_data["imagen_modo"], cv2.IMREAD_UNCHANGED)
                                if modo_img is not None:
                                    modo_img = resize_to_fit(modo_img, 200, 200)
                                    offx, offy = get_absolute_position(elem, seg["offset"])
                                    dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                    dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                    tlx = offx - modo_img.shape[1]//2 + dx
                                    tly = offy - modo_img.shape[0]//2 + dy
                                    superponer_imagen(frame, modo_img, tlx, tly)
            if ev["type"] in ["question", "cronometro", "answer"]:
                vigneta_key = ev["vigneta_key"]
                found_v = None
                for mk, md in content_data["modos"].items():
                    if vigneta_key in md["viñetas"]:
                        found_v = md["viñetas"][vigneta_key]
                        break
                if not found_v:
                    continue
                if ev["type"] == "question":
                    for elem in LAYOUT["elements"]:
                        if elem["id"] == "contenido":
                            seg_logo = next((s for s in elem["segments"] if s["id"] == "logo"), None)
                            if seg_logo and os.path.isfile(found_v["imagen_logo"]):
                                logo_img = cv2.imread(found_v["imagen_logo"], cv2.IMREAD_UNCHANGED)
                                if logo_img is not None:
                                    logo_img = resize_to_fit(logo_img, 200, 200)
                                    offx, offy = get_absolute_position(elem, seg_logo["offset"])
                                    dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_logo.get("effect")=="Oscilación suave" else 0
                                    dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_logo.get("effect")=="Oscilación suave" else 0
                                    tlx = offx - logo_img.shape[1]//2 + dx
                                    tly = offy - logo_img.shape[0]//2 + dy
                                    superponer_imagen(frame, logo_img, tlx, tly)
                            seg_text_logo = next((s for s in elem["segments"] if s["id"] == "text_logo"), None)
                            if seg_text_logo:
                                offx, offy = get_absolute_position(elem, seg_text_logo["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                draw_text_custom(frame, found_v["text_logo"], offx+dx, offy+dy, 0.8, (255,255,255))
                elif ev["type"] == "cronometro":
                    for elem in LAYOUT["elements"]:
                        if elem["id"] == "contenido":
                            seg_crono = next((s for s in elem["segments"] if s["id"] == "cronometro"), None)
                            if seg_crono and cronometro_frames:
                                offx, offy = get_absolute_position(elem, seg_crono["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_crono.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_crono.get("effect")=="Oscilación suave" else 0
                                local_time = t - ev["start"]
                                gif_fps = len(cronometro_frames) / cronometro_duration
                                c_index = int(local_time * gif_fps) % len(cronometro_frames)
                                crono_img = resize_to_fit(cronometro_frames[c_index], 200, 200)
                                tlx = offx - crono_img.shape[1]//2 + dx
                                tly = offy - crono_img.shape[0]//2 + dy
                                superponer_imagen(frame, crono_img, tlx, tly)
                elif ev["type"] == "answer":
                    for elem in LAYOUT["elements"]:
                        if elem["id"] == "contenido":
                            seg_text_logo = next((s for s in elem["segments"] if s["id"] == "text_logo"), None)
                            if seg_text_logo:
                                offx, offy = get_absolute_position(elem, seg_text_logo["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                draw_text_custom(frame, found_v["text_logo"], offx+dx, offy+dy, 0.8, (0,255,0))
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

# ====================================================
# FUNCIÓN PRINCIPAL: CREAR VIDEO FINAL
# ====================================================
def generate_tiktok_video(content_data, output_path="final_tiktok.mp4", fps=30):
    # Variables de referencia
    bg_voices_dir = LAYOUT["bg_voices_dir"]
    bg_audio_dir  = LAYOUT["bg_audio_dir"]
    bg_visual_dir = LAYOUT["bg_visual_dir"]

    # Ruta de voice_intro
    voice_intro_path = os.path.normpath(r"app\Resources\AlternativeQuiz\Sounds\voices\voice_intro.mp3")
    print("voice_intro_path:", voice_intro_path)
    if not os.path.isfile(voice_intro_path):
        raise FileNotFoundError(f"No se encontró la voz de intro en: {voice_intro_path}")
    intro_voice_clip = AudioFileClip(voice_intro_path)
    intro_duration = intro_voice_clip.duration
    cronometro_duration = 3.0
    cronometro_gif_path = content_data.get("cronometro_gif", r"app\Resources\AlternativeQuiz\clock_gif.gif")
    default_w, default_h = content_data.get("image_default_size", [200, 200])

    # Calcular duración total (suma de voces)
    total_duration = intro_duration
    modos = content_data["modos"]
    for modo_key, modo_data in modos.items():
        voice_modo_path = os.path.join(bg_voices_dir, f"voice_modo_{modo_key}.mp3")
        if os.path.isfile(voice_modo_path):
            modo_voice_clip = AudioFileClip(voice_modo_path)
            total_duration += modo_voice_clip.duration
            modo_voice_clip.close()
        for vigneta_key, _ in modo_data["viñetas"].items():
            q_path = os.path.join(bg_voices_dir, f"voice_question_{vigneta_key}.mp3")
            a_path = os.path.join(bg_voices_dir, f"voice_answer_{vigneta_key}.mp3")
            q_dur = AudioFileClip(q_path).duration if os.path.isfile(q_path) else 0.0
            a_dur = AudioFileClip(a_path).duration if os.path.isfile(a_path) else 0.0
            total_duration += (q_dur + cronometro_duration + a_dur)
    intro_voice_clip.close()

    total_frames = int(total_duration * fps)
    WIDTH, HEIGHT = 1080, 1920

    # Preparar background visual
    bg_visual_files = glob.glob(os.path.join(bg_visual_dir, "*"))
    if not bg_visual_files:
        raise ValueError(f"No se encontraron videos/imagenes en {bg_visual_dir}")
    bg_visual_choice = random.choice(bg_visual_files)
    is_bg_video = os.path.splitext(bg_visual_choice)[1].lower() in [".mp4", ".mov", ".avi", ".mkv"]
    if is_bg_video:
        bg_video_clip = VideoFileClip(bg_visual_choice).subclipped(0, total_duration)
    else:
        bg_image = cv2.imread(bg_visual_choice, cv2.IMREAD_COLOR)
        if bg_image is None:
            bg_image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        else:
            bg_image = cv2.resize(bg_image, (WIDTH, HEIGHT))

    # Cargar frames del GIF de cronómetro
    cronometro_frames = []
    if os.path.isfile(cronometro_gif_path):
        gif_frames = imageio.mimread(cronometro_gif_path)
        for frame in gif_frames:
            if frame.shape[2] == 4:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA)
            else:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cronometro_frames.append(frame_bgr)

    # Construir timeline de eventos
    timeline = []
    current_time = 0.0
    timeline.append({"type": "intro", "start": current_time, "end": current_time + intro_duration})
    current_time += intro_duration
    for modo_key, modo_data in modos.items():
        voice_modo_path = os.path.join(bg_voices_dir, f"voice_modo_{modo_key}.mp3")
        modo_dur = 0.0
        if os.path.isfile(voice_modo_path):
            modo_dur = AudioFileClip(voice_modo_path).duration
        timeline.append({"type": "modo", "modo_key": modo_key, "start": current_time, "end": current_time + modo_dur})
        current_time += modo_dur
        for vigneta_key, _ in modo_data["viñetas"].items():
            q_path = os.path.join(bg_voices_dir, f"voice_question_{vigneta_key}.mp3")
            a_path = os.path.join(bg_voices_dir, f"voice_answer_{vigneta_key}.mp3")
            q_dur = AudioFileClip(q_path).duration if os.path.isfile(q_path) else 0.0
            a_dur = AudioFileClip(a_path).duration if os.path.isfile(a_path) else 0.0
            timeline.append({"type": "question", "vigneta_key": vigneta_key, "start": current_time, "end": current_time + q_dur})
            current_time += q_dur
            timeline.append({"type": "cronometro", "vigneta_key": vigneta_key, "start": current_time, "end": current_time + cronometro_duration})
            current_time += cronometro_duration
            timeline.append({"type": "answer", "vigneta_key": vigneta_key, "start": current_time, "end": current_time + a_dur})
            current_time += a_dur

    # Configuración para la columna lateral
    lateral_lines = []
    for modo_key, modo_data in modos.items():
        lateral_lines.append(modo_data["texto_modo"].upper() + ":")
        for vigneta_key, vigneta_data in modo_data["viñetas"].items():
            lateral_lines.append(f"  {vigneta_key}) {vigneta_data['text_logo']}")
    lateral_font_scale = content_data.get("text_settings", {}).get("lateral_scale", 0.5)
    lateral_line_spacing = content_data.get("text_settings", {}).get("lateral_line_spacing", 40)
    lateral_color = (255, 255, 255)

    # Parámetros de oscilación
    osc_amplitude = 5
    osc_frequency = 0.5

    def get_events_at_time(t):
        active = []
        for ev in timeline:
            if ev["start"] <= t < ev["end"]:
                active.append(ev)
        return active

    # Definir la función make_frame (accederá a todas las variables definidas en este ámbito)
    def make_frame(t):
        if is_bg_video:
            frame = bg_video_clip.get_frame(t)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
        else:
            frame = bg_image.copy()
        if len(frame.shape) == 2 or frame.shape[2] == 1:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        active_events = [ev for ev in timeline if ev["start"] <= t < ev["end"]]
        # Dibujar header
        for elem in LAYOUT["elements"]:
            if elem["id"] == "header":
                for seg in elem["segments"]:
                    if seg.get("dura_hasta_el_final", False):
                        offx, offy = get_absolute_position(elem, seg["offset"])
                        dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        header_text = content_data.get("header_text", "QUIZ LOGOS")
                        draw_text_custom(frame, header_text, offx+dx, offy+dy, 1.0, hex_to_bgr(seg.get("text_color", "#FFFFFF")))
        # Dibujar columna lateral (después de intro)
        if t >= timeline[0]["end"]:
            for elem in LAYOUT["elements"]:
                if elem["id"] == "lateral_column":
                    offx, offy = get_absolute_position(elem, elem["segments"][0]["offset"])
                    draw_vertical_text(frame, lateral_lines, offx, offy, lateral_font_scale, lateral_color, lateral_line_spacing)
        # Dibujar intro
        if any(ev["type"] == "intro" for ev in active_events):
            for elem in LAYOUT["elements"]:
                if elem["id"] == "intro":
                    for seg in elem["segments"]:
                        offx, offy = get_absolute_position(elem, seg["offset"])
                        dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                        if seg["content_type"]=="Texto":
                            draw_text_custom(frame, content_data["intro"]["texto_intro"], offx+dx, offy+dy, 1.0, (255,255,255))
                        elif seg["content_type"]=="Imagen" and os.path.isfile(content_data["intro"]["imagen_intro"]):
                            intro_img = cv2.imread(content_data["intro"]["imagen_intro"], cv2.IMREAD_UNCHANGED)
                            if intro_img is not None:
                                intro_img = resize_to_fit(intro_img, 200, 200)
                                tlx = offx - intro_img.shape[1]//2 + dx
                                tly = offy - intro_img.shape[0]//2 + dy
                                superponer_imagen(frame, intro_img, tlx, tly)
        # Dibujar contenido (modos y viñetas)
        for ev in active_events:
            if ev["type"] == "modo":
                modo_key = ev["modo_key"]
                modo_data = content_data["modos"][modo_key]
                for elem in LAYOUT["elements"]:
                    if elem["id"] == "contenido":
                        for seg in elem["segments"]:
                            if seg["id"] == "texto_modo":
                                offx, offy = get_absolute_position(elem, seg["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                draw_text_custom(frame, modo_data["texto_modo"], offx+dx, offy+dy, 0.8, hex_to_bgr(seg.get("text_color", "#FFFFFF")))
                            if seg["id"] == "imagen_modo" and os.path.isfile(modo_data["imagen_modo"]):
                                modo_img = cv2.imread(modo_data["imagen_modo"], cv2.IMREAD_UNCHANGED)
                                if modo_img is not None:
                                    modo_img = resize_to_fit(modo_img, 200, 200)
                                    offx, offy = get_absolute_position(elem, seg["offset"])
                                    dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                    dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg.get("effect")=="Oscilación suave" else 0
                                    tlx = offx - modo_img.shape[1]//2 + dx
                                    tly = offy - modo_img.shape[0]//2 + dy
                                    superponer_imagen(frame, modo_img, tlx, tly)
            if ev["type"] in ["question", "cronometro", "answer"]:
                vigneta_key = ev["vigneta_key"]
                found_v = None
                for mk, md in content_data["modos"].items():
                    if vigneta_key in md["viñetas"]:
                        found_v = md["viñetas"][vigneta_key]
                        break
                if not found_v:
                    continue
                if ev["type"] == "question":
                    for elem in LAYOUT["elements"]:
                        if elem["id"] == "contenido":
                            seg_logo = next((s for s in elem["segments"] if s["id"] == "logo"), None)
                            if seg_logo and os.path.isfile(found_v["imagen_logo"]):
                                logo_img = cv2.imread(found_v["imagen_logo"], cv2.IMREAD_UNCHANGED)
                                if logo_img is not None:
                                    logo_img = resize_to_fit(logo_img, 200, 200)
                                    offx, offy = get_absolute_position(elem, seg_logo["offset"])
                                    dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_logo.get("effect")=="Oscilación suave" else 0
                                    dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_logo.get("effect")=="Oscilación suave" else 0
                                    tlx = offx - logo_img.shape[1]//2 + dx
                                    tly = offy - logo_img.shape[0]//2 + dy
                                    superponer_imagen(frame, logo_img, tlx, tly)
                            seg_text_logo = next((s for s in elem["segments"] if s["id"] == "text_logo"), None)
                            if seg_text_logo:
                                offx, offy = get_absolute_position(elem, seg_text_logo["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                draw_text_custom(frame, found_v["text_logo"], offx+dx, offy+dy, 0.8, (255,255,255))
                elif ev["type"] == "cronometro":
                    for elem in LAYOUT["elements"]:
                        if elem["id"] == "contenido":
                            seg_crono = next((s for s in elem["segments"] if s["id"] == "cronometro"), None)
                            if seg_crono and cronometro_frames:
                                offx, offy = get_absolute_position(elem, seg_crono["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_crono.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_crono.get("effect")=="Oscilación suave" else 0
                                local_time = t - ev["start"]
                                gif_fps = len(cronometro_frames) / cronometro_duration
                                c_index = int(local_time * gif_fps) % len(cronometro_frames)
                                crono_img = resize_to_fit(cronometro_frames[c_index], 200, 200)
                                tlx = offx - crono_img.shape[1]//2 + dx
                                tly = offy - crono_img.shape[0]//2 + dy
                                superponer_imagen(frame, crono_img, tlx, tly)
                elif ev["type"] == "answer":
                    for elem in LAYOUT["elements"]:
                        if elem["id"] == "contenido":
                            seg_text_logo = next((s for s in elem["segments"] if s["id"] == "text_logo"), None)
                            if seg_text_logo:
                                offx, offy = get_absolute_position(elem, seg_text_logo["offset"])
                                dx = int(osc_amplitude * math.sin(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                dy = int(osc_amplitude * math.cos(2*math.pi*osc_frequency*t)) if seg_text_logo.get("effect")=="Oscilación suave" else 0
                                draw_text_custom(frame, found_v["text_logo"], offx+dx, offy+dy, 0.8, (0,255,0))
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Crear VideoClip usando make_frame
    final_video_clip = VideoClip(lambda t: make_frame(t), duration=total_duration)
    
    # --- Componer audio final ---
    bg_audio_files = glob.glob(os.path.join(bg_audio_dir, "*"))
    if not bg_audio_files:
        raise ValueError(f"No se encontraron audios en {bg_audio_dir}")
    bg_audio_choice = random.choice(bg_audio_files)
    bg_audio_clip = AudioFileClip(bg_audio_choice).subclipped(0, total_duration)
    audio_clips = [bg_audio_clip]
    voice_intro_clip = AudioFileClip(voice_intro_path)
    audio_clips.append(voice_intro_clip)
    for ev in timeline:
        if ev["type"] == "modo":
            modo_key = ev["modo_key"]
            path = os.path.join(bg_voices_dir, f"voice_modo_{modo_key}.mp3")
            if os.path.isfile(path):
                clip_audio = AudioFileClip(path).with_start(ev["start"])
                audio_clips.append(clip_audio)
        elif ev["type"] == "question":
            vk = ev["vigneta_key"]
            path = os.path.join(bg_voices_dir, f"voice_question_{vk}.mp3")
            if os.path.isfile(path):
                clip_audio = AudioFileClip(path).with_start(ev["start"])
                audio_clips.append(clip_audio)
        elif ev["type"] == "answer":
            vk = ev["vigneta_key"]
            path = os.path.join(bg_voices_dir, f"voice_answer_{vk}.mp3")
            if os.path.isfile(path):
                clip_audio = AudioFileClip(path).with_start(ev["start"])
                audio_clips.append(clip_audio)
    from moviepy import CompositeAudioClip
    final_audio = CompositeAudioClip(audio_clips)
    final_video_clip = final_video_clip.with_audio(final_audio)
    final_video_clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")
    final_video_clip.close()
    bg_audio_clip.close()
    voice_intro_clip.close()
    for ac in audio_clips:
        if ac is not bg_audio_clip and ac is not voice_intro_clip:
            ac.close()
    print("¡Video generado exitosamente!", output_path)

if __name__ == "__main__":
    content_data_example = {
        "header_text": "QUIZ LOGOS DE JÓVENES",
        "intro": {
            "texto_intro": "¡Bienvenido al quiz de logos!",
            "imagen_intro": r"app\Resources\AlternativeQuiz\ImagesExample\intro_image.png"
        },
        "modos": {
            "1": {
                "texto_modo": "FÁCIL",
                "imagen_modo": r"app\Resources\AlternativeQuiz\easy.png",
                "viñetas": {
                    "1": {
                        "text_logo": "PlayStation",
                        "imagen_logo": r"app\Resources\AlternativeQuiz\ImagesExample\img1.png"
                    },
                    "2": {
                        "text_logo": "Xbox",
                        "imagen_logo": r"app\Resources\AlternativeQuiz\ImagesExample\img2.png"
                    }
                }
            },
            "2": {
                "texto_modo": "PROMEDIO",
                "imagen_modo": r"app\Resources\AlternativeQuiz\medium.png",
                "viñetas": {
                    "3": {
                        "text_logo": "TikTok",
                        "imagen_logo": r"app\Resources\AlternativeQuiz\ImagesExample\img3.png"
                    }
                }
            }
        },
        "cronometro_gif": r"app\Resources\AlternativeQuiz\clock_gif.gif",
        "image_default_size": [200, 200],
        "escala_segmentos": 1.0,
        "text_settings": {
            "lateral_scale": 0.5,
            "lateral_line_spacing": 40
        }
    }
    generate_tiktok_video(content_data_example, output_path=r"app\Services\gui\tests\results\demo_tiktok_video.mp4", fps=30)
