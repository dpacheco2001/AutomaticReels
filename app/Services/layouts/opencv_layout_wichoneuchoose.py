import cv2
import numpy as np
import os, math, random, imageio
from moviepy import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip


def draw_text_with_autowrap(img, text, center_x, baseline_y, font=cv2.FONT_HERSHEY_DUPLEX,
                            max_width=None, max_lines=2, initial_scale=1.4, min_scale=0.5,
                            scale_step=0.1, main_color=(255,255,255), thickness=3,
                            outline_color=(0,0,0), outline_thickness=None):
    if max_width is None:
        max_width = img.shape[1] - 40
    if outline_thickness is None:
        outline_thickness = thickness + 2
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
        return True, lines_formed

    while scale >= min_scale:
        if max_lines == 1:
            if text_fits_one_line(text, scale):
                best_lines = [text]
                best_scale = scale
                break
        else:
            if text_fits_one_line(text, scale):
                best_lines = [text]
                best_scale = scale
                break
            ok, splitted = can_fit_in_two_lines(text, scale)
            if ok:
                best_lines = splitted
                best_scale = scale
                break
        scale -= scale_step

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


def draw_neon_text_with_autowrap(img, text, center_x, baseline_y, font=cv2.FONT_HERSHEY_DUPLEX,
                                 max_width=None, max_lines=2, initial_scale=1.4, min_scale=0.5,
                                 scale_step=1.0, main_color=(255,255,255), thickness=2,
                                 glow_color=(0,255,255), glow_thickness=10, blur_ksize=21, alpha=0.7):
    glow_layer = np.zeros_like(img, dtype=np.uint8)
    glow_layer = draw_text_with_autowrap(glow_layer, text, center_x, baseline_y,
                                          font=font, max_width=max_width, max_lines=max_lines,
                                          initial_scale=initial_scale, min_scale=min_scale,
                                          scale_step=scale_step, main_color=glow_color,
                                          thickness=glow_thickness, outline_color=(0,0,0),
                                          outline_thickness=glow_thickness)

    glow_layer = cv2.GaussianBlur(glow_layer, (blur_ksize, blur_ksize), 0)
    img_float = img.astype(np.float32)
    glow_float = glow_layer.astype(np.float32)
    combined = cv2.add(img_float, alpha * glow_float)
    np.clip(combined, 0, 255, out=combined)
    img[:] = combined.astype(np.uint8)
    draw_text_with_autowrap(img, text, center_x, baseline_y,
                            font=font, max_width=max_width, max_lines=max_lines,
                            initial_scale=initial_scale, min_scale=min_scale,
                            scale_step=scale_step, main_color=main_color, thickness=thickness,
                            outline_color=(0,0,0), outline_thickness=thickness+2)


def resize_and_crop(img, target_width, target_height):
    orig_h, orig_w = img.shape[:2]
    scale = max(target_width / orig_w, target_height / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    x0 = (new_w - target_width) // 2
    y0 = (new_h - target_height) // 2
    cropped = resized[y0:y0+target_height, x0:x0+target_width]
    return cropped


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
        alpha_val = overlay_crop[:, :, 3] / 255.0
        for c in range(3):
            base_roi[:, :, c] = base_roi[:, :, c] * (1 - alpha_val) + overlay_crop[:, :, c] * alpha_val
    else:
        base_roi[:] = overlay_crop
    return base


def get_random_file(directory, exts=(".mp3", ".wav", ".aac", ".mp4", ".avi", ".mov", ".mkv")):
    if not os.path.isdir(directory):
        return None
    files = [os.path.join(directory, f) for f in os.listdir(directory)
             if f.lower().endswith(exts)]
    return random.choice(files) if files else None


def generate_which_one_u_choose_video(
    output_path,
    width=1080,          
    height=1920,
    fps=30,
    intro_duration=3.0,  
    bg_audio_dir="app/Resources/WhichOneUChoose/Sounds/backgrounds",
    images_dir="app/Resources/WhichOneUChoose/ImagesExample",
    intro_path=None,     
    text_intro="¡Bienvenidos!",
    intro_text_offset=(0, 20),
    intro_text_scale=2.0,
    intro_text_oscillation_amplitude=2,
    intro_text_oscillation_frequency=0.2,
    slides=[],           
    slide_text_offset=(0, 20),
    slide_text_scale=1.5,
    slide_text_oscillation_amplitude=3,
    slide_text_oscillation_frequency=0.3,
    logo_gif_path=None,
    logo_offset_cell=None,
    use_neon_text=False,         
    neon_settings=None,          
    use_intro_audio=False        
):
    if neon_settings is None:
        neon_settings = {
            "main_color": (255,255,255),
            "glow_color": (0,255,255),
            "thickness": 2,
            "glow_thickness": 10,
            "blur_ksize": 21,
            "alpha": 0.7
        }

  
    intro_video_clip = None
    intro_bg = None
    if intro_path is not None:
        ext = os.path.splitext(intro_path)[1].lower()
        if ext in [".mp4", ".mov", ".avi"]:
            clip = VideoFileClip(intro_path)
            real_dur = min(intro_duration, clip.duration)
            intro_video_clip = clip.subclipped(0, real_dur).with_duration(real_dur)
            intro_duration = real_dur
        elif ext in [".png", ".jpg", ".jpeg"]:
            intro_bg = cv2.imread(intro_path, cv2.IMREAD_UNCHANGED)
            if intro_bg is None:
                raise ValueError("No se pudo cargar el archivo de intro: " + intro_path)
            intro_bg = resize_and_crop(intro_bg, width, height)
        else:
            raise ValueError("Tipo de archivo intro no soportado: " + ext)
    else:
        default_intro = os.path.join(images_dir, "img0.png")
        intro_bg = cv2.imread(default_intro, cv2.IMREAD_UNCHANGED)
        if intro_bg is None:
            raise ValueError("No se pudo cargar la imagen de intro por defecto: " + default_intro)
        intro_bg = resize_and_crop(intro_bg, width, height)


    bg_audio_file = get_random_file(bg_audio_dir, exts=(".mp3", ".wav", ".aac"))
    if bg_audio_file is None:
        raise ValueError("No se encontró sonido de fondo en: " + bg_audio_dir)

 
    total_slides_duration = sum(slide.get("duration", 0) for slide in slides)
    total_duration = intro_duration + total_slides_duration


    logo_frames = []
    if logo_gif_path and os.path.isfile(logo_gif_path):
        frames = imageio.mimread(logo_gif_path)
        if len(frames) > 1:
            frames.pop(0)
        for fr in frames:
            if fr.shape[2] == 4:
                fr = cv2.cvtColor(fr, cv2.COLOR_RGBA2BGRA)
            else:
                fr = cv2.cvtColor(fr, cv2.COLOR_RGB2BGR)
            logo_frames.append(fr)
    num_logo_frames = len(logo_frames)
    cell_width = width // 2    
    cell_height = height // 3   
    logo_target_x = 0
    logo_target_y = cell_height  
    if logo_offset_cell:
        logo_target_x += logo_offset_cell[0]
        logo_target_y += logo_offset_cell[1]


    segments = []
    current_time = 0.0
    if intro_video_clip is not None:
        segments.append({
            "start": current_time,
            "duration": intro_duration,
            "type": "intro",
            "draw_data": {
                "video_clip": intro_video_clip,
                "text": text_intro,
                "offset": intro_text_offset,
                "scale": intro_text_scale,
                "osc_amplitude": intro_text_oscillation_amplitude,
                "osc_frequency": intro_text_oscillation_frequency,
                "use_neon": False
            }
        })
    else:
        segments.append({
            "start": current_time,
            "duration": intro_duration,
            "type": "intro",
            "draw_data": {
                "bg": intro_bg,
                "text": text_intro,
                "offset": intro_text_offset,
                "scale": intro_text_scale,
                "osc_amplitude": intro_text_oscillation_amplitude,
                "osc_frequency": intro_text_oscillation_frequency,
                "use_neon": False
            }
        })
    current_time += intro_duration

    for idx, slide in enumerate(slides):
        seg_duration = slide.get("duration", 3.0)
        segments.append({
            "start": current_time,
            "duration": seg_duration,
            "type": "slide",
            "draw_data": {
                "image_path": os.path.join(images_dir, slide.get("image")),
                "text": slide.get("text", ""),
                "offset": slide_text_offset,
                "scale": slide_text_scale,
                "osc_amplitude": slide_text_oscillation_amplitude,
                "osc_frequency": slide_text_oscillation_frequency,
                "slide_index": idx,
                "use_neon": slide.get("use_neon", use_neon_text) if "use_neon" in slide else use_neon_text,
                "neon_settings": slide.get("neon_settings", neon_settings)
            }
        })
        current_time += seg_duration


    def make_frame(t):
        seg = next(s for s in segments if s["start"] <= t < s["start"] + s["duration"])
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (30, 30, 30)
        seg_rel = t - seg["start"]

        if seg["type"] == "intro":
            data = seg["draw_data"]
            if "video_clip" in data:
                base_frame_rgb = data["video_clip"].get_frame(seg_rel)
                base_frame_bgr = cv2.cvtColor(base_frame_rgb, cv2.COLOR_RGB2BGR)
                base_frame_bgr = resize_and_crop(base_frame_bgr, width, height)
            else:
                base_frame_bgr = data["bg"].copy()
            if data.get("use_neon", False):
                draw_neon_text_with_autowrap(base_frame_bgr, data["text"],
                                             center_x=width//2 + data["offset"][0],
                                             baseline_y=50 + data["offset"][1],
                                             font=cv2.FONT_HERSHEY_DUPLEX,
                                             max_width=width-40,
                                             initial_scale=data["scale"],
                                             main_color=data.get("neon_settings", neon_settings).get("main_color", (255,255,255)),
                                             glow_color=data.get("neon_settings", neon_settings).get("glow_color", (0,255,255)),
                                             thickness=data.get("neon_settings", neon_settings).get("thickness", 2),
                                             glow_thickness=data.get("neon_settings", neon_settings).get("glow_thickness", 10),
                                             blur_ksize=data.get("neon_settings", neon_settings).get("blur_ksize", 21),
                                             alpha=data.get("neon_settings", neon_settings).get("alpha", 0.7))
            else:
                osc_dx = int(data["osc_amplitude"] * math.sin(2*math.pi*data["osc_frequency"]*t))
                osc_dy = int(data["osc_amplitude"] * math.cos(2*math.pi*data["osc_frequency"]*t))
                off = data["offset"]
                draw_text_with_autowrap(base_frame_bgr, data["text"],
                                        center_x=width//2 + off[0] + osc_dx,
                                        baseline_y=50 + off[1] + osc_dy,
                                        max_width=width-40,
                                        initial_scale=data["scale"])
            frame = base_frame_bgr

        elif seg["type"] == "slide":
            data = seg["draw_data"]
            slide_img = cv2.imread(data["image_path"], cv2.IMREAD_UNCHANGED)
            if slide_img is None:
                slide_img = np.zeros((height, width, 3), dtype=np.uint8)
                slide_img[:] = (50,50,50)
            slide_img = resize_and_crop(slide_img, width, height)
            frame = slide_img.copy()
            if data.get("use_neon", False):
                draw_neon_text_with_autowrap(frame, data["text"],
                                             center_x=width//2 + data["offset"][0],
                                             baseline_y=50 + data["offset"][1],
                                             font=cv2.FONT_HERSHEY_DUPLEX,
                                             max_width=width-40,
                                             initial_scale=data["scale"],
                                             main_color=data.get("neon_settings", neon_settings).get("main_color", (255,255,255)),
                                             glow_color=data.get("neon_settings", neon_settings).get("glow_color", (0,255,255)),
                                             thickness=data.get("neon_settings", neon_settings).get("thickness", 2),
                                             glow_thickness=data.get("neon_settings", neon_settings).get("glow_thickness", 10),
                                             blur_ksize=data.get("neon_settings", neon_settings).get("blur_ksize", 21),
                                             alpha=data.get("neon_settings", neon_settings).get("alpha", 0.7))
            else:
                osc_dx = int(data["osc_amplitude"] * math.sin(2*math.pi*data["osc_frequency"]*t))
                osc_dy = int(data["osc_amplitude"] * math.cos(2*math.pi*data["osc_frequency"]*t))
                off = data["offset"]
                draw_text_with_autowrap(frame, data["text"],
                                        center_x=width//2 + off[0] + osc_dx,
                                        baseline_y=50 + off[1] + osc_dy,
                                        max_width=width-40,
                                        initial_scale=data["scale"])
            if data.get("slide_index", -1) == 2 and num_logo_frames > 0:
                logo_time = seg_rel
                logo_index = int((logo_time / seg["duration"]) * num_logo_frames)
                if logo_index >= num_logo_frames:
                    logo_index = num_logo_frames - 1
                logo_frame = logo_frames[logo_index]
                logo_final = resize_and_crop(logo_frame, cell_width, cell_height)
                overlay_image(frame, logo_final, logo_target_x, logo_target_y)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    video_clip = VideoClip(make_frame, duration=total_duration)
    bg_audio = AudioFileClip(bg_audio_file).subclipped(0, total_duration)


    if use_intro_audio and intro_video_clip is not None and intro_video_clip.audio is not None:
        intro_audio = intro_video_clip.audio.subclipped(0, intro_duration)
        composite_intro_audio = CompositeAudioClip([
            bg_audio.subclipped(0, intro_duration),
            intro_audio.with_start(0)
        ])
        remainder_audio = bg_audio.subclipped(intro_duration, total_duration)
        final_audio = CompositeAudioClip([composite_intro_audio, remainder_audio.with_start(intro_duration)])
    else:
        final_audio = bg_audio

    final_clip = video_clip.with_audio(final_audio)
    final_clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")


if __name__ == "__main__":
    slides = [
        {"image": "img1.png", "text": "1.", "duration": 3, "use_neon": True, 
         "neon_settings": {"main_color": (255,255,255), "glow_color": (255,0,128), "thickness": 5, "glow_thickness": 12, "blur_ksize": 25, "alpha": 0.8}},
        {"image": "img2.png", "text": "2.", "duration": 3, "use_neon": True,"neon_settings": {"main_color": (255,255,255), "glow_color": (255,0,128), "thickness": 5, "glow_thickness": 12, "blur_ksize": 25, "alpha": 0.8}},
        {"image": "img3.png", "text": "3. No olvides suscribirte!", "duration": 6, "use_neon": True,
         "neon_settings": {"main_color": (0,0,255), "glow_color": (255,0,128), "thickness": 5, "glow_thickness": 12, "blur_ksize": 25, "alpha": 0.8}},
        {"image": "img4.png", "text": "4. ", "duration": 5, "use_neon": True,"neon_settings": {"main_color": (255,255,255), "glow_color": (255,0,128), "thickness": 5, "glow_thickness": 12, "blur_ksize": 25, "alpha": 0.8}},
    ]
    use_neon_text = False  
    neon_params = {
        "main_color": (255,255,255),
        "glow_color": (0,255,255),
        "thickness": 2,
        "glow_thickness": 10,
        "blur_ksize": 21,
        "alpha": 0.7
    }

    generate_which_one_u_choose_video(
        output_path="whichone_video.mp4",
        width=1080,
        height=1920,
        fps=30,
        intro_duration=3.1,
        bg_audio_dir="app/Resources/WhichOneUChoose/Sounds/backgrounds",
        images_dir="app/Resources/WhichOneUChoose/ImagesExample",
        intro_path=r"app\Resources\WhichOneUChoose\Videos\rain_house.mp4",  
        text_intro="*Ganas una casa en cualquier sitio* Donde te quedarias?",
        intro_text_offset=(0, 70),
        intro_text_scale=2.0,
        intro_text_oscillation_amplitude=2,
        intro_text_oscillation_frequency=0.2,
        slides=slides,
        slide_text_offset=(0, 120),
        slide_text_scale=2.3,
        slide_text_oscillation_amplitude=3,
        slide_text_oscillation_frequency=0.3,
        logo_gif_path="app/Resources/WhichOneUChoose/follow_gif.gif",
        logo_offset_cell=(0,0),
        use_neon_text=use_neon_text,
        neon_settings=neon_params,
        use_intro_audio=True
    )
