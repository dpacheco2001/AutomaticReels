import cv2
import numpy as np
import os, math, random
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip
import imageio

def draw_text_centered(img, text, center_x, center_y, font=cv2.FONT_HERSHEY_DUPLEX,
                       font_scale=1.0, color=(255,255,255), thickness=2, outline_color=(0,0,0)):
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    text_x = center_x - text_size[0] // 2
    text_y = center_y + text_size[1] // 2
    cv2.putText(img, text, (text_x, text_y), font, font_scale, outline_color, thickness+2, cv2.LINE_AA)
    cv2.putText(img, text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)

def overlay_image(base, overlay, x, y):
    h_base, w_base = base.shape[:2]
    h_over, w_over = overlay.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x+w_over, w_base), min(y+h_over, h_base)
    if x1 >= x2 or y1 >= y2:
        return base
    overlay_crop = overlay[y1-y:y2-y, x1-x:x2-x]
    base_roi = base[y1:y2, x1:x2]
    if overlay.shape[2] == 4:
        alpha = overlay_crop[:, :, 3] / 255.0
        for c in range(3):
            base_roi[:, :, c] = (1 - alpha) * base_roi[:, :, c] + alpha * overlay_crop[:, :, c]
    else:
        mask = cv2.inRange(overlay_crop, np.array([1,1,1]), np.array([255,255,255]))
        base_roi[mask>0] = overlay_crop[mask>0]
    return base

def resize_image(img, max_width, max_height):
    h, w = img.shape[:2]
    scale = min(max_width/w, max_height/h, 1.0)
    if scale < 1.0:
        return cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
    return img

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

def create_header_custom(width, title):
    header_height = 100
    header_img = np.zeros((header_height, width, 4), dtype=np.uint8)
    rect_layer = np.zeros((header_height, width, 4), dtype=np.uint8)
    rect_color = (200,100,50,255)
    radius = 20
    pt1 = (20,10)
    pt2 = (width-20, header_height-10)
    rect_layer = draw_rounded_rect(rect_layer, pt1, pt2, rect_color, radius, thickness=-1)
    header_img = rect_layer.copy()
    header_bgr = header_img[:,:,:3].copy()
    draw_text_centered(header_bgr, title, width//2, header_height//2, font_scale=1.5, color=(255,255,255), thickness=2, outline_color=(0,0,0))
    alpha_channel = header_img[:,:,3]
    header_img = cv2.merge([header_bgr[:,:,0], header_bgr[:,:,1], header_bgr[:,:,2], alpha_channel])
    return header_img

def build_left_panel(modes):
    panel = []
    for mode in modes:
        panel.append((mode["name"].upper(), mode["color"]))
        for q in mode["questions"]:
            panel.append((f"{q['number']})", (255,255,255)))
    return panel

def draw_layout(frame, width, height, header_img, left_items, answers, center_text, 
                logo_img, clock_img=None, extra_overlay_img=None, offsets=None,
                scales=None, oscillation_amplitude=5, oscillation_frequency=0.5, t=0,
                seg_start=0, seg_duration=0, current_answer="", show_left_panel=True):
    if offsets is None:
        offsets = {"header": (0,30), "left_panel": (0,0), "center_text": (0,0), "logo": (0,0), "clock": (0,0)}
    if scales is None:
        scales = {"logo": 1.0, "clock": 1.0, "extra": 1.0}
    
    dx_header, dy_header = offsets.get("header", (0,0))
    dx_left, dy_left = offsets.get("left_panel", (0,0))
    dx_center, dy_center = offsets.get("center_text", (0,0))
    dx_logo, dy_logo = offsets.get("logo", (0,0))
    dx_clock, dy_clock = offsets.get("clock", (0,0))
    
    header_h = header_img.shape[0]
    frame = overlay_image(frame, header_img, dx_header, dy_header)
    
    if show_left_panel:
        y_pos = dy_header + header_h + 20 + dy_left
        for text, color in left_items:
            q_num = text[:-1] if text.endswith(")") else None
            disp = f"{text} {answers[q_num]}" if q_num and (q_num in answers) else text
            draw_text_centered(frame, disp, 100 + dx_left, y_pos, font_scale=0.9, color=color)
            y_pos += 40
    
    if center_text:
        base_center_x = width // 2 + dx_center
        base_center_y = dy_header + header_h + 100 + dy_center
        osc_dx = int(oscillation_amplitude * math.sin(2 * math.pi * oscillation_frequency * t))
        osc_dy = int(oscillation_amplitude * math.cos(2 * math.pi * oscillation_frequency * t))
        draw_text_centered(frame, center_text, base_center_x+osc_dx, base_center_y+osc_dy, font_scale=1.2)
        if center_text.strip().lower() == "respuesta:" and current_answer:
            draw_text_centered(frame, current_answer, base_center_x+osc_dx, base_center_y+60+osc_dy,
                               font_scale=1.0, color=(0,255,0), thickness=2, outline_color=(0,0,0))
    
    if logo_img is not None:
        if isinstance(logo_img, list):
            if seg_duration > 0:
                idx = int(((t - seg_start) / seg_duration) * len(logo_img))
                if idx >= len(logo_img): idx = len(logo_img) - 1
            else:
                idx = 0
            logo_img = logo_img[idx]
        entrance_duration = 0.5
        relative_time = t - seg_start if t >= seg_start else entrance_duration
        if relative_time < entrance_duration:
            entrance_offset_x = int(-100*(1 - relative_time/entrance_duration))
            entrance_angle = 30*(1 - relative_time/entrance_duration)
        else:
            entrance_offset_x = 0
            entrance_angle = 0
        oscillation_angle = 5 * math.sin(2 * math.pi * oscillation_frequency * t)
        total_angle = entrance_angle + oscillation_angle
        effective_logo_scale = scales.get("logo", 1.0)
        new_width = max(1, int(logo_img.shape[1] * effective_logo_scale))
        new_height = max(1, int(logo_img.shape[0] * effective_logo_scale))
        logo_resized = cv2.resize(logo_img, (new_width, new_height))
        M = cv2.getRotationMatrix2D((logo_resized.shape[1]//2, logo_resized.shape[0]//2), total_angle, 1.0)
        logo_rotated = cv2.warpAffine(logo_resized, M, (logo_resized.shape[1], logo_resized.shape[0]), borderValue=(0,0,0))
        x_logo = width - logo_rotated.shape[1] - 20 + dx_logo + entrance_offset_x
        y_logo = (height - logo_rotated.shape[0]) // 2 + dy_logo
        overlay_image(frame, logo_rotated, x_logo, y_logo)
    
    if clock_img is not None:
        scale_clock = scales.get("clock", 1.0)
        overlay_resized = cv2.resize(clock_img, (int(clock_img.shape[1]*scale_clock), int(clock_img.shape[0]*scale_clock)))
        overlay_h, overlay_w = overlay_resized.shape[:2]
        x_overlay = (width - overlay_w) // 2 + dx_clock
        y_overlay = dy_header + header_h + 150 + dy_clock
        overlay_image(frame, overlay_resized, x_overlay, y_overlay)
    
    if extra_overlay_img is not None:
        scale_extra = scales.get("extra", 1.0)
        overlay_resized = cv2.resize(extra_overlay_img, (int(extra_overlay_img.shape[1]*scale_extra), int(extra_overlay_img.shape[0]*scale_extra)))
        overlay_h, overlay_w = overlay_resized.shape[:2]
        x_overlay = (width - overlay_w) // 2
        y_overlay = dy_header + header_h + 200
        overlay_image(frame, overlay_resized, x_overlay, y_overlay)
    
    return frame

def get_random_file(directory, exts=(".mp4", ".avi", ".mov", ".mkv")):
    if not os.path.isdir(directory):
        return None
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(exts)]
    return random.choice(files) if files else None

def generate_quiz_video(params, output_path):
    width = params.get("width", 720)
    height = params.get("height", 1280)
    fps = params.get("fps", 30)
    offsets = params.get("offsets", {"header":(0,30), "left_panel":(30,120), "center_text":(70,-60), "logo":(-100,-100), "clock":(70,-60)})
    scales = params.get("scales", {"logo":1.0, "clock":1.0, "extra":1.0})
    logo_size = params.get("logo_size", (width//3, height//3))
    
    header = create_header_custom(width, params.get("title", "Quiz"))
    modes = params.get("modes", [])
    left_panel = build_left_panel(modes)
    
    intro_img = resize_image(cv2.imread(params["intro_image"], cv2.IMREAD_UNCHANGED),
                             *params.get("intro_image_size", (width//2, height//2)))
    
    for mode in modes:
        if mode.get("mode_overlay"):
            if mode["mode_overlay"].lower().endswith(".gif"):
                frames = imageio.mimread(mode["mode_overlay"])
                for i in range(len(frames)):
                    frame_gif = frames[i]
                    if frame_gif.shape[2] == 4:
                        frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGBA2BGRA)
                    else:
                        frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGB2BGR)
                    frames[i] = frame_gif
                mode["mode_overlay_img"] = frames
            else:
                mode["mode_overlay_img"] = resize_image(cv2.imread(mode["mode_overlay"], cv2.IMREAD_UNCHANGED),
                                                         *logo_size)
        else:
            mode["mode_overlay_img"] = None
        for q in mode["questions"]:
            if q.get("logo"):
                q["logo_img"] = resize_image(cv2.imread(q["logo"], cv2.IMREAD_UNCHANGED),
                                             *logo_size)
            else:
                q["logo_img"] = None
            if "question_text" not in q:
                q["question_text"] = "¿Te suena este logo?"
    
    clock_gif_frames = imageio.mimread(params["clock_gif"])
    for i in range(len(clock_gif_frames)):
        frame_gif = clock_gif_frames[i]
        if frame_gif.shape[2] == 4:
            frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGBA2BGRA)
        else:
            frame_gif = cv2.cvtColor(frame_gif, cv2.COLOR_RGB2BGR)
        clock_gif_frames[i] = frame_gif
    num_gif_frames = len(clock_gif_frames)
    
    audio_intro = AudioFileClip(params["intro_voice"])
    clock_sfx = AudioFileClip(params.get("clock_sfx", "")) if params.get("clock_sfx") else None
    accert_sfx = AudioFileClip(params.get("accert_sfx", "")) if params.get("accert_sfx") else None
    
    segments = []
    current_time = 0.0
    def add_segment(duration, center_text, logo, clock, answer_update, audios, show_left_panel=True):
        nonlocal current_time
        segments.append({
            "start": current_time,
            "duration": duration,
            "center_text": center_text,
            "logo": logo,
            "clock": clock,
            "answer_update": answer_update,
            "audios": audios,
            "show_left_panel": show_left_panel
        })
        current_time += duration
    
    add_segment(audio_intro.duration, params["intro_text"], intro_img, False, None, [(audio_intro, 0)], show_left_panel=False)
    
    for mode in modes:
        mode_voice = AudioFileClip(mode["voice"])
        add_segment(mode_voice.duration, f"Modo: {mode['name']}", mode["mode_overlay_img"], False, None, [(mode_voice, 0)])
        for q in mode["questions"]:
            voice_q = AudioFileClip(q["voice_question"])
            duration_q = voice_q.duration + 0.5
            add_segment(duration_q, q.get("question_text", "¿Te suena este logo?"), q["logo_img"], False, None, [(voice_q, 0)])
            clock_dur = 3.0
            audios_clock = [(clock_sfx, 0)] if clock_sfx else []
            add_segment(clock_dur, params.get("clock_text", "¡Piensa rápido!"), None, True, None, audios_clock)
            voice_a = AudioFileClip(q["voice_answer"])
            duration_a = max(voice_a.duration, accert_sfx.duration) if accert_sfx else voice_a.duration
            add_segment(duration_a, "Respuesta:", None, False, (str(q["number"]), q["answer_text"]),
                        [(voice_a, 0), (accert_sfx, 0)] if accert_sfx else [(voice_a, 0)])
    
    total_duration = segments[-1]["start"] + segments[-1]["duration"]
    total_frames = int(total_duration * fps)
    
    temp_video = "temp_video.mp4"
    video_writer = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    bg_video_path = get_random_file(params["bg_video_dir"], exts=(".mp4", ".avi", ".mov", ".mkv"))
    cap_bg = cv2.VideoCapture(bg_video_path) if bg_video_path else None
    
    active_logo = None
    logo_seg_start = 0
    logo_seg_duration = 0
    current_ans = ""
    answers = {}
    
    for frame_idx in range(total_frames):
        t = frame_idx / fps
        seg = next(s for s in segments if s["start"] <= t < s["start"] + s["duration"])
        if not seg.get("show_left_panel", True):
            current_left_panel = []
        else:
            current_left_panel = build_left_panel(modes)
        if seg["center_text"].strip().lower().startswith("modo:"):
            active_logo = seg["logo"]
            logo_seg_start = seg["start"]
            logo_seg_duration = seg["duration"]
        elif seg["logo"] is not None:
            active_logo = seg["logo"]
            logo_seg_start = seg["start"]
            logo_seg_duration = seg["duration"]
        if seg["center_text"].strip().lower() == "respuesta:" and seg["answer_update"] is not None:
            current_ans = seg["answer_update"][1]
        if cap_bg:
            ret, bg_frame = cap_bg.read()
            if not ret:
                cap_bg.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, bg_frame = cap_bg.read()
            bg_frame = cv2.resize(bg_frame, (width, height))
            frame = bg_frame.copy()
        else:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = (30,30,30)
        if seg["clock"]:
            relative_time = t - seg["start"]
            gif_index = int((relative_time/seg["duration"])*num_gif_frames)
            if gif_index >= num_gif_frames:
                gif_index = num_gif_frames - 1
            current_clock_frame = clock_gif_frames[gif_index]
        else:
            current_clock_frame = None
        
        if active_logo is not None and seg["center_text"].strip().lower() == q.get("question_text", "¿te suena este logo?").strip().lower():
            entrance_duration = 0.5
            rel_t = t - logo_seg_start if t>=logo_seg_start else entrance_duration
            if rel_t < entrance_duration:
                entrance_offset_x = int(-100*(1 - rel_t/entrance_duration))
                entrance_angle = 30*(1 - rel_t/entrance_duration)
            else:
                entrance_offset_x = 0
                entrance_angle = 0
        else:
            entrance_offset_x = 0
            entrance_angle = 0
        
        frame = draw_layout(frame, width, height, header, current_left_panel, answers,
                            seg["center_text"], active_logo, current_clock_frame, None,
                            offsets, scales, params.get("oscillation_amplitude", 5),
                            params.get("oscillation_frequency", 0.5), t,
                            seg_start=logo_seg_start, seg_duration=logo_seg_duration,
                            current_answer=current_ans)
        video_writer.write(frame)
        if t + 1/fps >= seg["start"] + seg["duration"] and seg["answer_update"]:
            q_key, resp_val = seg["answer_update"]
            answers[q_key] = resp_val
            answers["current_answer"] = resp_val
    
    video_writer.release()
    
    composite_audio_clips = []
    for seg in segments:
        for clip, rel_offset in seg["audios"]:
            composite_audio_clips.append(clip.with_start(seg["start"] + rel_offset))
    composite_audio = CompositeAudioClip(composite_audio_clips)
    
    bg_audio_path = get_random_file(params["bg_audio_dir"], exts=(".mp3", ".wav", ".aac"))
    if bg_audio_path:
        bg_audio = AudioFileClip(bg_audio_path).subclipped(0, total_duration)
    else:
        bg_audio = None
    
    final_audio = CompositeAudioClip([composite_audio, bg_audio]) if bg_audio else composite_audio
    video_clip = VideoFileClip(temp_video)
    final_video = video_clip.with_audio(final_audio)
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

if __name__ == "__main__":
    params = {
        "width": 720,
        "height": 1280,
        "fps": 30,
        "title": "Adivina logos!",
        "intro_image": r"app\Resources\AlternativeQuiz\ImagesExample\intro_image.png",
        "intro_text": "Heidinger es babosin",
        "intro_voice": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_intro.mp3",
        "intro_image_size": (360, 640),
        "logo_size": (240, 240),
        "clock_gif": r"app\Resources\AlternativeQuiz\clock_gif.gif",
        "clock_sfx": r"app\Resources\AlternativeQuiz\Sounds\sound_effects\clock.mp3",
        "accert_sfx": r"app\Resources\AlternativeQuiz\Sounds\sound_effects\accert.mp3",
        "offsets": {
            "header": (0, 30),
            "left_panel": (30, 120),
            "center_text": (70, -60),
            "logo": (-100, -100),
            "clock": (70, -60)
        },
        "scales": {
            "logo": 1.3,
            "clock": 0.6,
            "extra": 1.0
        },
        "bg_video_dir": r"app\Resources\AlternativeQuiz\Videos",
        "bg_audio_dir": r"app\Resources\AlternativeQuiz\Sounds\backgrounds",
        "oscillation_amplitude": 5,
        "oscillation_frequency": 0.5,
        "clock_text": "Se te va el tren!",
        "modes": [
            {
                "name": "Facilitooo",
                "color": (0,255,0),
                "voice": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_easy.mp3",
                "mode_overlay": r"app\Resources\AlternativeQuiz\easy.png",
                "questions": [
                    {
                        "number": 1,
                        "voice_question": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_question_1.mp3",
                        "voice_answer": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_answer_1.mp3",
                        "answer_text": "PlayStation",
                        "logo": r"app\Resources\AlternativeQuiz\ImagesExample\img1.png",
                        "question_text": "Interesante este logo"
                    },
                    {
                        "number": 2,
                        "voice_question": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_question_2.mp3",
                        "voice_answer": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_answer_2.mp3",
                        "answer_text": "Nintendo",
                        "logo": r"app\Resources\AlternativeQuiz\ImagesExample\img2.png",
                        "question_text": "Uhmm, que sera?"
                    }
                ]
            },
            {
                "name": "Un promedio",
                "color": (0,255,255),
                "voice": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_medium.mp3",
                "mode_overlay": r"app\Resources\AlternativeQuiz\medium.png",
                "questions": [
                    {
                        "number": 3,
                        "voice_question": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_question_3.mp3",
                        "voice_answer": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_answer_3.mp3",
                        "answer_text": "Pepsi",
                        "logo": r"app\Resources\AlternativeQuiz\ImagesExample\img3.png",
                        "question_text": "Vamos de nuevo!"
                    },
                    {
                        "number": 4,
                        "voice_question": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_question_4.mp3",
                        "voice_answer": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_answer_4.mp3",
                        "answer_text": "Coca-Cola",
                        "logo": r"app\Resources\AlternativeQuiz\ImagesExample\img4.png",
                        "question_text": "Uhm..."
                    }
                ]
            },
            {
                "name": "Dificil",
                "color": (255,0,0),
                "voice": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_difficult.mp3",
                "mode_overlay": r"app\Resources\AlternativeQuiz\follow_gif.gif",
                "questions": [
                    {
                        "number": 5,
                        "voice_question": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_question_5.mp3",
                        "voice_answer": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_answer_5.mp3",
                        "answer_text": "Meta",
                        "logo": r"app\Resources\AlternativeQuiz\ImagesExample\img5.png",
                        "question_text": "RV nomas dire..."
                    },
                    {
                        "number": 6,
                        "voice_question": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_question_6.mp3",
                        "voice_answer": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_answer_6.mp3",
                        "answer_text": "Sodimac",
                        "logo": r"app\Resources\AlternativeQuiz\ImagesExample\img6.png",
                        "question_text": "Vamos a ver si sabes"
                    }
                ]
            },
            {
                "name": "Un chuchas",
                "color": (255,0,255),
                "voice": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_expert.mp3",
                "mode_overlay": r"app\Resources\AlternativeQuiz\experto.png",
                "questions": [
                    {
                        "number": 7,
                        "voice_question": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_question_7.mp3",
                        "voice_answer": r"app\Resources\AlternativeQuiz\Sounds\voices\voice_answer_7.mp3",
                        "answer_text": "BCP",
                        "logo": r"app\Resources\AlternativeQuiz\ImagesExample\img7.png",
                        "question_text": "Un banco famoso"
                    }
                ]
            }
        ]
    }
    generate_quiz_video(params, "quiz_tiktok_final.mp4")
