import cv2
import numpy as np
import os, math, random, imageio
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip

# ------------------------------------------------------------------
# Función para autoajustar texto en hasta dos líneas
# ------------------------------------------------------------------
def draw_text_with_autowrap(img, text, center_x, baseline_y, font=cv2.FONT_HERSHEY_DUPLEX,
                            max_width=700, max_lines=2, initial_scale=1.4, min_scale=0.5,
                            scale_step=0.1, main_color=(255,255,255), thickness=3,
                            outline_color=(0,0,0), outline_thickness=3):
    if not text:
        return img
    scale = initial_scale
    best_lines = [text]
    best_scale = scale

    def text_fits_one_line(txt, sc):
        size = cv2.getTextSize(txt, font, sc, thickness)[0]
        return size[0] <= max_width

    def can_fit_in_two_lines(txt, sc):
        words = txt.split()
        current_line = ""
        lines_formed = []
        line_count = 1
        for w in words:
            candidate = (current_line + " " + w).strip()
            size = cv2.getTextSize(candidate, font, sc, thickness)[0]
            if size[0] <= max_width:
                current_line = candidate
            else:
                lines_formed.append(current_line)
                current_line = w
                line_count += 1
                if line_count > 2:
                    return False, ["", ""]
        lines_formed.append(current_line)
        if len(lines_formed) <= 2:
            return True, lines_formed
        else:
            return False, ["", ""]

    while scale >= min_scale:
        # ¿Cabe en una sola línea?
        if text_fits_one_line(text, scale):
            best_lines = [text]
            best_scale = scale
            break
        # ¿Cabe en dos líneas?
        ok, splitted = can_fit_in_two_lines(text, scale)
        if ok:
            best_lines = splitted
            best_scale = scale
            break
        scale -= scale_step

    # Dibujar las líneas resultantes
    sizes = [cv2.getTextSize(line, font, best_scale, thickness)[0] for line in best_lines]
    current_y = baseline_y
    for i, line in enumerate(best_lines):
        s = sizes[i]
        x = int(center_x - s[0] / 2)
        y = int(current_y)
        cv2.putText(img, line, (x, y), font, best_scale, outline_color, outline_thickness, cv2.LINE_AA)
        cv2.putText(img, line, (x, y), font, best_scale, main_color, thickness, cv2.LINE_AA)
        current_y += s[1] + 10
    return img

# ------------------------------------------------------------------
# Funciones auxiliares para imágenes y video
# ------------------------------------------------------------------
def overlay_image(base, overlay, x, y):
    h_base, w_base = base.shape[:2]
    h_over, w_over = overlay.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + w_over, w_base), min(y + h_over, h_base)
    if x1 >= x2 or y1 >= y2:
        return base
    overlay_crop = overlay[y1-y:y2-y, x1-x:x2-x]
    base_roi = base[y1:y2, x1:x2]
    if overlay.shape[2] == 4:
        alpha = overlay_crop[:, :, 3] / 255.0
        for c in range(3):
            base_roi[:, :, c] = base_roi[:, :, c] * (1 - alpha) + overlay_crop[:, :, c] * alpha
    else:
        base_roi[:] = overlay_crop
    return base

def resize_image(img, max_width, max_height):
    h, w = img.shape[:2]
    scale = min(max_width/w, max_height/h)
    if scale < 1.0:
        new_size = (int(w*scale), int(h*scale))
        return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
    return img

def get_random_file(directory, exts=(".mp4", ".avi", ".mov", ".mkv", ".mp3", ".wav", ".aac")):
    if not os.path.isdir(directory):
        return None
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(exts)]
    return random.choice(files) if files else None

# ------------------------------------------------------------------
# Función para crear un header con texto (tipo “Quiz Logos”)
# ------------------------------------------------------------------
def draw_rounded_rect(img, pt1, pt2, color, radius, thickness=-1):
    x1, y1 = pt1
    x2, y2 = pt2
    cv2.rectangle(img, (x1+radius, y1), (x2-radius, y2), color, thickness)
    cv2.rectangle(img, (x1, y1+radius), (x2, y2-radius), color, thickness)
    cv2.circle(img, (x1+radius, y1+radius), radius, color, thickness)
    cv2.circle(img, (x2-radius, y1+radius), radius, color, thickness)
    cv2.circle(img, (x1+radius, y2-radius), radius, color, thickness)
    cv2.circle(img, (x2-radius, y2-radius), radius, color, thickness)
    return img

def create_header_custom(width, title, bg_color=(0,0,255,255), text_color=(255,255,255)):
    header_height = 100
    header_img = np.zeros((header_height, width, 4), dtype=np.uint8)
    rect_layer = np.zeros((header_height, width, 4), dtype=np.uint8)
    rect_color = bg_color  # BGRA
    radius = 20
    pt1 = (20,10)
    pt2 = (width-20, header_height-10)
    rect_layer = draw_rounded_rect(rect_layer, pt1, pt2, rect_color, radius, thickness=-1)
    header_img = rect_layer.copy()
    header_bgr = header_img[:,:,:3].copy()
    draw_text_with_autowrap(header_bgr, title, width//2, header_height//2,
                            initial_scale=1.5, main_color=text_color, thickness=2,
                            outline_color=(0,0,0))
    alpha_channel = header_img[:,:,3]
    header_img = cv2.merge([header_bgr[:,:,0], header_bgr[:,:,1], header_bgr[:,:,2], alpha_channel])
    return header_img

# ------------------------------------------------------------------
# Función principal: Generar el video de quiz con 3 alternativas
# ------------------------------------------------------------------
def generate_three_choice_quiz(
    output_path,
    width=720,
    height=1280,
    fps=30,
    # Archivos de intro y header
    intro_image_path=None,
    intro_voice_path=None,
    header_image_path=None,
    intro_text="",
    # Texto del header
    header_title="Quiz Logos",
    header_bg_color=(0,0,255,255),
    header_text_color=(255,255,255),
    # Lista de preguntas
    questions=[],
    # Segmento de promoción (tras la 2da pregunta)
    promo_image_path=None,
    promo_text="",
    promo_voice_path=None,
    # Carpetas para background video/audio
    bg_video_dir=None,
    bg_audio_dir=None,
    # Cronómetro (GIF)
    clock_gif_path=None,
    clock_time=3.0,
    # Offsets
    offsets={
        "header": (0,0),
        "intro_text": (0,0),
        "intro_image": (0,0),
        "center_question": (0,0),
        "alternative_question": (0,0),
        "question_image": (0,0),
        "clock": (0,0),
        "promo_image": (0,0),
        "promo_text": (0,0)
    },
    # Scales
    scales={
        "intro_image": 1.0,
        "center_question": 1.0,
        "alternative_question": 1.0,
        "question_image": 1.0,
        "clock": 1.0,
        "promo_image": 1.0,
        "promo_text": 1.0
    },
    # Oscilación
    oscillation_amplitude=5,
    oscillation_frequency=0.5,
    oscillation={
        "header": False,
        "intro_image": True,
        "intro_text": True,
        "center_question": True,
        "alternative_question": True,
        "question_image": True,
        "clock": True,
        "promo_image": True,
        "promo_text": True
    }
):
    # 1) Header con texto
    if header_image_path and os.path.isfile(header_image_path):
        header_img = cv2.imread(header_image_path, cv2.IMREAD_UNCHANGED)
        if header_img is not None and header_img.shape[1] != width:
            header_img = cv2.resize(header_img, (width, header_img.shape[0]))
    else:
        header_img = create_header_custom(width, header_title, bg_color=header_bg_color, text_color=header_text_color)
    
    # 2) Intro (imagen y audio)
    intro_img = None
    if intro_image_path and os.path.isfile(intro_image_path):
        intro_img = cv2.imread(intro_image_path, cv2.IMREAD_UNCHANGED)
        intro_img = resize_image(intro_img, width//2, height//2)
    intro_voice = None
    if intro_voice_path and os.path.isfile(intro_voice_path):
        intro_voice = AudioFileClip(intro_voice_path)
    
    # 3) Cronómetro (GIF)
    clock_gif_frames = []
    num_clock_frames = 0
    if clock_gif_path and os.path.isfile(clock_gif_path):
        clock_gif_frames = imageio.mimread(clock_gif_path)
        for i in range(len(clock_gif_frames)):
            frame_gif = clock_gif_frames[i]
            if frame_gif.shape[2] == 4:
                frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGBA2BGRA)
            else:
                frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGB2BGR)
            clock_gif_frames[i] = frame_gif
        num_clock_frames = len(clock_gif_frames)
    
    # 4) Promoción (GIF)
    promo_gif_frames = []
    num_promo_frames = 0
    if promo_image_path and os.path.isfile(promo_image_path):
        if promo_image_path.lower().endswith(".gif"):
            promo_gif_frames = imageio.mimread(promo_image_path)
            for i in range(len(promo_gif_frames)):
                frame_gif = promo_gif_frames[i]
                if frame_gif.shape[2] == 4:
                    frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGBA2BGRA)
                else:
                    frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGB2BGR)
                promo_gif_frames[i] = frame_gif
            num_promo_frames = len(promo_gif_frames)
        else:
            promo_img = cv2.imread(promo_image_path, cv2.IMREAD_UNCHANGED)
            promo_img = resize_image(promo_img, width//2, height//2)
            promo_gif_frames = [promo_img]
            num_promo_frames = 1
    
    # 5) Crear lista de segmentos
    segments = []
    current_time = 0.0
    def add_segment(duration, seg_type, draw_data, audio_clips):
        nonlocal current_time
        segments.append({
            "start": current_time,
            "duration": duration,
            "type": seg_type,
            "draw_data": draw_data,
            "audio_clips": audio_clips
        })
        current_time += duration
    
    # Intro
    if intro_voice:
        add_segment(
            duration=intro_voice.duration,
            seg_type="intro",
            draw_data={"intro_img": intro_img, "intro_text": intro_text},
            audio_clips=[(intro_voice, 0)]
        )
    
    # Preguntas
    for i, q in enumerate(questions):
        q_audio = AudioFileClip(q["voice_question"]) if os.path.isfile(q["voice_question"]) else None
        a_audio = AudioFileClip(q["voice_answer"]) if os.path.isfile(q["voice_answer"]) else None
        duration_q = q_audio.duration if q_audio else 2.0
        duration_a = a_audio.duration if a_audio else 2.0

        add_segment(
            duration=duration_q,
            seg_type="question",
            draw_data={
                "question_text": q["question_text"],
                "alternatives": q["alternatives"],
                "correct_index": q["correct_index"],
                "image_path": q["image_path"]
            },
            audio_clips=[(q_audio, 0)] if q_audio else []
        )
        add_segment(
            duration=clock_time,
            seg_type="clock",
            draw_data={
                "question_text": q["question_text"],
                "alternatives": q["alternatives"],
                "correct_index": q["correct_index"],
                "image_path": q["image_path"],
                "clock_gif_frames": clock_gif_frames,
                "num_clock_frames": num_clock_frames
            },
            audio_clips=[]
        )
        add_segment(
            duration=duration_a,
            seg_type="answer",
            draw_data={
                "question_text": q["question_text"],
                "alternatives": q["alternatives"],
                "correct_index": q["correct_index"],
                "image_path": q["image_path"]
            },
            audio_clips=[(a_audio, 0)] if a_audio else []
        )
        # Promo tras la 2da pregunta
        if i == 1 and promo_voice_path and os.path.isfile(promo_voice_path):
            promo_audio = AudioFileClip(promo_voice_path)
            add_segment(
                duration=promo_audio.duration,
                seg_type="promo",
                draw_data={
                    "promo_gif_frames": promo_gif_frames,
                    "num_promo_frames": num_promo_frames,
                    "promo_text": promo_text
                },
                audio_clips=[(promo_audio, 0)]
            )
    
    total_duration = segments[-1]["start"] + segments[-1]["duration"]
    total_frames = int(total_duration * fps)
    
    # Crear video temporal
    temp_video = "temp_three_choice_quiz.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

    # Background
    bg_cap = None
    if bg_video_dir:
        random_bg_video = get_random_file(bg_video_dir, exts=(".mp4", ".avi", ".mov", ".mkv"))
        if random_bg_video:
            bg_cap = cv2.VideoCapture(random_bg_video)

    # Renderizar frames
    for frame_idx in range(total_frames):
        t = frame_idx / fps
        seg = next(s for s in segments if s["start"] <= t < s["start"] + s["duration"])
        if bg_cap:
            ret, bg_frame = bg_cap.read()
            if not ret:
                bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, bg_frame = bg_cap.read()
            if ret and bg_frame is not None:
                bg_frame = cv2.resize(bg_frame, (width, height))
                frame = bg_frame.copy()
            else:
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:] = (30,30,30)
        else:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = (30,30,30)

        # Dibuja el header en la parte superior (con offset "header" + posible oscilación)
        if oscillation.get("header", False):
            osc_h_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
            osc_h_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
        else:
            osc_h_dx = 0
            osc_h_dy = 0
        hx, hy = offsets.get("header",(0,0))
        overlay_image(frame, header_img, hx+osc_h_dx, hy+osc_h_dy)

        # Segmentos
        seg_type = seg["type"]
        draw_data = seg["draw_data"]

        if seg_type == "intro":
            if draw_data.get("intro_img") is not None:
                if oscillation.get("intro_image", False):
                    osc_ii_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                    osc_ii_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
                else:
                    osc_ii_dx = 0
                    osc_ii_dy = 0
                off_i = offsets["intro_image"]
                intro_img_draw = draw_data["intro_img"]
                w_i = intro_img_draw.shape[1]
                h_i = intro_img_draw.shape[0]
                x_i = (width - w_i)//2 + off_i[0] + osc_ii_dx
                y_i = (height - h_i)//2 + off_i[1] + osc_ii_dy
                overlay_image(frame, intro_img_draw, x_i, y_i)
            if draw_data.get("intro_text"):
                if oscillation.get("intro_text", False):
                    osc_it_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                    osc_it_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
                else:
                    osc_it_dx = 0
                    osc_it_dy = 0
                off_it = offsets["intro_text"]
                draw_text_with_autowrap(frame, draw_data["intro_text"],
                                        width//2 + off_it[0] + osc_it_dx,
                                        200 + off_it[1] + osc_it_dy,
                                        max_width=width-40)
        elif seg_type in ["question", "clock", "answer"]:
            question_text = draw_data["question_text"]
            # Texto de la pregunta
            if oscillation.get("center_question", False):
                osc_cq_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                osc_cq_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
            else:
                osc_cq_dx = 0
                osc_cq_dy = 0
            off_cq = offsets["center_question"]
            draw_text_with_autowrap(frame, question_text,
                                    width//2 + off_cq[0] + osc_cq_dx,
                                    200 + off_cq[1] + osc_cq_dy,
                                    max_width=width-100,
                                    initial_scale=scales.get("center_question",1.0))
            # Alternativas
            alternatives = draw_data["alternatives"]
            correct_idx = draw_data["correct_index"]
            if oscillation.get("alternative_question", False):
                osc_alt_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                osc_alt_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
            else:
                osc_alt_dx = 0
                osc_alt_dy = 0
            off_alt = offsets["alternative_question"]
            alt_y_base = 300 + off_alt[1]
            for idx, (alt_text, alt_color) in enumerate(alternatives):
                if seg_type == "answer" and idx == correct_idx:
                    alt_color = (0,255,0)
                alt_y = alt_y_base + idx*60
                draw_text_with_autowrap(frame, alt_text,
                                        150 + off_alt[0] + osc_alt_dx,
                                        alt_y + osc_alt_dy,
                                        max_width=300,
                                        initial_scale=scales.get("alternative_question",1.0),
                                        main_color=alt_color)
            # Imagen a la derecha
            if "image_path" in draw_data and draw_data["image_path"] and os.path.isfile(draw_data["image_path"]):
                q_img = cv2.imread(draw_data["image_path"], cv2.IMREAD_UNCHANGED)
                q_img = resize_image(q_img, width//3, height//3)
                w_q = q_img.shape[1]
                h_q = q_img.shape[0]
                off_qi = offsets["question_image"]
                if oscillation.get("question_image", False):
                    osc_qi_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                    osc_qi_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
                else:
                    osc_qi_dx = 0
                    osc_qi_dy = 0
                x_q = width - w_q - 30 + off_qi[0] + osc_qi_dx
                y_q = (height//2) - (h_q//2) + off_qi[1] + osc_qi_dy
                overlay_image(frame, q_img, x_q, y_q)
            # Cronómetro
            if seg_type == "clock":
                rel_time = t - seg["start"]
                if draw_data.get("num_clock_frames",0) > 0:
                    gif_index = int((rel_time / seg["duration"]) * draw_data["num_clock_frames"])
                    if gif_index >= draw_data["num_clock_frames"]:
                        gif_index = draw_data["num_clock_frames"] - 1
                    current_clock_frame = draw_data["clock_gif_frames"][gif_index]
                    off_ck = offsets["clock"]
                    if oscillation.get("clock", False):
                        osc_ck_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                        osc_ck_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
                    else:
                        osc_ck_dx = 0
                        osc_ck_dy = 0
                    w_c = current_clock_frame.shape[1]
                    h_c = current_clock_frame.shape[0]
                    x_c = (width - w_c)//2 + off_ck[0] + osc_ck_dx
                    y_c = height - h_c - 50 + off_ck[1] + osc_ck_dy
                    overlay_image(frame, current_clock_frame, x_c, y_c)
        elif seg_type == "promo":
            if draw_data.get("num_promo_frames", 0) > 0:
                rel_time = t - seg["start"]
                gif_index = int((rel_time / seg["duration"]) * draw_data["num_promo_frames"])
                if gif_index >= draw_data["num_promo_frames"]:
                    gif_index = draw_data["num_promo_frames"] - 1
                current_promo_frame = draw_data["promo_gif_frames"][gif_index]
                off_p = offsets["promo_image"]
                if oscillation.get("promo_image", False):
                    osc_p_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                    osc_p_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
                else:
                    osc_p_dx = 0
                    osc_p_dy = 0
                w_p = current_promo_frame.shape[1]
                h_p = current_promo_frame.shape[0]
                x_p = (width - w_p)//2 + off_p[0] + osc_p_dx
                y_p = (height - h_p)//2 - 50 + off_p[1] + osc_p_dy
                overlay_image(frame, current_promo_frame, x_p, y_p)
            if draw_data.get("promo_text", ""):
                off_pt = offsets["promo_text"]
                if oscillation.get("promo_text", False):
                    osc_pt_dx = int(oscillation_amplitude * math.sin(2*math.pi*oscillation_frequency*t))
                    osc_pt_dy = int(oscillation_amplitude * math.cos(2*math.pi*oscillation_frequency*t))
                else:
                    osc_pt_dx = 0
                    osc_pt_dy = 0
                draw_text_with_autowrap(frame, draw_data["promo_text"],
                                        width//2 + off_pt[0] + osc_pt_dx,
                                        (height//2) + 200 + off_pt[1] + osc_pt_dy,
                                        max_width=width-40,
                                        initial_scale=scales.get("promo_text",1.0))

        video_writer.write(frame)

    video_writer.release()

    # Combinar audios
    video_clip = VideoFileClip(temp_video)
    audio_clips = []
    for seg in segments:
        for clip, rel_offset in seg["audio_clips"]:
            audio_clips.append(clip.with_start(seg["start"] + rel_offset))
    composite_audio = CompositeAudioClip(audio_clips)
    # Audio de fondo
    if bg_audio_dir:
        random_bg_audio = get_random_file(bg_audio_dir, exts=(".mp3", ".wav", ".aac"))
        if random_bg_audio:
            bg_audio_clip = AudioFileClip(random_bg_audio).subclipped(0, video_clip.duration)
            composite_audio = CompositeAudioClip([composite_audio, bg_audio_clip])
    final_video = video_clip.with_audio(composite_audio)
    final_video.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")


# ------------------------------------------------------------------
# Ejemplo de uso
# ------------------------------------------------------------------
if __name__ == "__main__":
    sample_questions = [
        {
            "question_text": "¿Cuál es el sinónimo de 'hermoso'?",
            "image_path": "app/Resources/AlternativeQuiz/ImagesExample/img1.png",
            "voice_question": "app/Resources/AlternativeQuiz/Sounds/voices/voice_question_1.mp3",
            "voice_answer": "app/Resources/AlternativeQuiz/Sounds/voices/voice_answer_1.mp3",
            "alternatives": [
                ("A) Atractivo", (255,255,255)),
                ("B) Yo", (255,255,255)),
                ("C) Feo", (255,255,255))
            ],
            "correct_index": 0
        },
        {
            "question_text": "¿Qué significa 'Hola' en inglés?",
            "image_path": "app/Resources/AlternativeQuiz/ImagesExample/img2.png",
            "voice_question": "app/Resources/AlternativeQuiz/Sounds/voices/voice_question_2.mp3",
            "voice_answer": "app/Resources/AlternativeQuiz/Sounds/voices/voice_answer_2.mp3",
            "alternatives": [
                ("A) Good bye", (255,255,255)),
                ("B) Hello", (255,255,255)),
                ("C) Yes", (255,255,255))
            ],
            "correct_index": 1
        },
        {
            "question_text": "¿Cuál es el resultado de 2+2?",
            "image_path": "app/Resources/AlternativeQuiz/ImagesExample/img3.png",
            "voice_question": "app/Resources/AlternativeQuiz/Sounds/voices/voice_question_3.mp3",
            "voice_answer": "app/Resources/AlternativeQuiz/Sounds/voices/voice_answer_3.mp3",
            "alternatives": [
                ("A) 3", (255,255,255)),
                ("B) 4", (255,255,255)),
                ("C) 22", (255,255,255))
            ],
            "correct_index": 1
        }
    ]

    generate_three_choice_quiz(
        output_path="my_three_choice_quiz.mp4",
        width=720,
        height=1280,
        fps=30,
        intro_image_path=r"app\Resources\AlternativeQuiz\ImagesExample\intro_image.png",
        intro_voice_path=r"app\Resources\AlternativeQuiz\Sounds\voices\voice_intro.mp3",
        intro_text="Bienvenidos al Quiz!",
        header_title="Quiz Logos",
        header_bg_color=(255,0,0,255), 
        header_text_color=(255,255,255),
        questions=sample_questions,
        promo_image_path=r"app\Resources\AlternativeQuiz\ImagesExample\promo_img.gif",
        promo_text="¡Síguenos para más quizzes!",
        promo_voice_path=r"app\Resources\AlternativeQuiz\Sounds\voices\voice_promo.mp3",
        bg_video_dir=r"app\Resources\AlternativeQuiz\Videos",
        bg_audio_dir=r"app\Resources\AlternativeQuiz\Sounds\backgrounds",
        clock_gif_path=r"app\Resources\AlternativeQuiz_v2\loading_bar.gif",
        clock_time=3.0,
        offsets={
            "header": (0,0),
            "intro_text": (0,0),
            "intro_image": (0,0),
            "center_question": (0,30),
            "alternative_question": (200,80),
            "question_image": (-210,100),
            "clock": (0,-100),
            "promo_image": (0,0),
            "promo_text": (0,0)
        },
        scales={
            "intro_image": 1.0,
            "center_question": 1.5,
            "alternative_question": 1.5,
            "question_image": 1.0,
            "clock": 1.0,
            "promo_image": 1.0,
            "promo_text": 1.0
        },
        oscillation_amplitude=5,
        oscillation_frequency=0.5,
        oscillation={
            "header": False,
            "intro_image": True,
            "intro_text": True,
            "center_question": True,
            "alternative_question": True,
            "question_image": True,
            "clock": True,
            "promo_image": True,
            "promo_text": True
        }
    )
