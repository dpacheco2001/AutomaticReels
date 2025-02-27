import cv2
import numpy as np
import math
import random
import glob
import os
from moviepy import VideoFileClip, concatenate_videoclips, CompositeAudioClip, AudioFileClip, CompositeVideoClip
def print_colored(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")


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
        line1, line2 = "", ""
        current_line = ""
        line_count = 1
        lines_formed = []
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

    sizes = []
    for line in best_lines:
        s = cv2.getTextSize(line, font, best_scale, thickness)[0]
        sizes.append(s)

    current_y = baseline_y
    for i, line in enumerate(best_lines):
        s = sizes[i]
        x = int(center_x - s[0] / 2)
        y = int(current_y)
        cv2.putText(img, line, (x, y), font, best_scale, outline_color, outline_thickness, cv2.LINE_AA)
        cv2.putText(img, line, (x, y), font, best_scale, main_color, thickness, cv2.LINE_AA)
        current_y += s[1] + 10
    return img

def resize_to_fit(img, max_width, max_height):
    h, w = img.shape[:2]
    scale = min(max_width / w, max_height / h)
    if scale < 1:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img

def rotate_image(img, angle):
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return rotated

def tint_green(img):
    if img.shape[2] == 4:
        bgr = img[:, :, :3]
        alpha = img[:, :, 3:]
        green_layer = np.full(bgr.shape, (0, 255, 0), dtype=np.uint8)
        tinted = cv2.addWeighted(bgr, 0.5, green_layer, 0.5, 0)
        return np.concatenate([tinted, alpha], axis=2)
    else:
        green_layer = np.full(img.shape, (0, 255, 0), dtype=np.uint8)
        tinted = cv2.addWeighted(img, 0.5, green_layer, 0.5, 0)
        return tinted

oscillation_frequency = 0.5
def create_intro_segment(intro_image_path, intro_text, layout_path, width, height, fps, intro_duration,
                           intro_scale_factor=1.2, oscillation_amplitude=5, oscillation_frequency=0.5):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output = r"app\Resources\RatherThan\VideosTests\segment_intro.mp4"
    video_out = cv2.VideoWriter(output, fourcc, fps, (width, height))
    if layout_path:
        layout = cv2.imread(layout_path, cv2.IMREAD_COLOR)
        if layout is None:
            layout = np.zeros((height, width, 3), dtype=np.uint8)
        else:
            layout = cv2.resize(layout, (width, height))
    else:
        layout = np.zeros((height, width, 3), dtype=np.uint8)
    intro_img = cv2.imread(intro_image_path, cv2.IMREAD_UNCHANGED)
    if intro_img is not None:
        
        intro_img = resize_to_fit(intro_img, int(width//2 * intro_scale_factor), int(height//2 * intro_scale_factor))
    def get_base_frame():
        return layout.copy()
    intro_frames = int(intro_duration * fps)
    for f in range(intro_frames):
        frame = get_base_frame()
       
        t = f / fps
        osc_dx = int(oscillation_amplitude * math.sin(2 * math.pi * oscillation_frequency * t))
        osc_dy = int(oscillation_amplitude * math.cos(2 * math.pi * oscillation_frequency * t))
        if intro_img is not None:
            h_intro, w_intro = intro_img.shape[:2]
            
            x_intro = (width - w_intro) // 2 + osc_dx
            y_intro = (height - h_intro) // 2 + osc_dy
            text_y_intro = y_intro - 20 if y_intro - 20 > 0 else 20
            superponer_imagen(frame, intro_img, x_intro, y_intro)
            draw_text_with_autowrap(frame, intro_text, x_intro + w_intro//2, text_y_intro,
                                    max_width=width-40, initial_scale=1.4, thickness=2, outline_thickness=2)
        else:
            draw_text_with_autowrap(frame, intro_text, width//2, height//2,
                                    max_width=width-40, initial_scale=1.4, thickness=2, outline_thickness=2)
        video_out.write(frame)
    video_out.release()
    cv2.destroyAllWindows()
    return output

def create_pair_segment(pair, output_path, layout_path, width, height, fps,
                        delay_first, delay_second, clock_time, percent_time,
                        vertical_adjust_1, vertical_adjust_2, scale_factor_pairs, oscillation_amplitude):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if layout_path:
        layout = cv2.imread(layout_path, cv2.IMREAD_COLOR)
        if layout is None:
            layout = np.zeros((height, width, 3), dtype=np.uint8)
        else:
            layout = cv2.resize(layout, (width, height))
    else:
        layout = np.zeros((height, width, 3), dtype=np.uint8)
    img1_path, text1, pct1 = pair[0]
    img2_path, text2, pct2 = pair[1]
    im1 = cv2.imread(img1_path, cv2.IMREAD_UNCHANGED)
    if im1 is not None:
        im1 = resize_to_fit(im1, width//2, height//2)
        im1 = cv2.resize(im1, None, fx=scale_factor_pairs, fy=scale_factor_pairs, interpolation=cv2.INTER_LINEAR)
    im2 = cv2.imread(img2_path, cv2.IMREAD_UNCHANGED)
    if im2 is not None:
        im2 = resize_to_fit(im2, width//2, height//2)
        im2 = cv2.resize(im2, None, fx=scale_factor_pairs, fy=scale_factor_pairs, interpolation=cv2.INTER_LINEAR)
    if im1 is not None:
        h1, w1 = im1.shape[:2]
        x1 = (width - w1) // 2
        y1 = (height//4) - (h1//2) + 20 + vertical_adjust_1
    if im2 is not None:
        h2, w2 = im2.shape[:2]
        x2 = (width - w2) // 2
        y2 = (height - height//4) - (h2//2) + 20 + vertical_adjust_2
    pct1_str = f"{pct1}%"
    pct2_str = f"{pct2}%"
    color1 = (0,255,0) if pct1 > pct2 else (255,255,255)
    color2 = (0,255,0) if pct2 > pct1 else (255,255,255)
    text_offset = 30
    frames_first = int(delay_first * fps)
    frames_second = int(delay_second * fps)
    frames_clock = int(clock_time * fps)
    frames_percent = int(percent_time * fps)
    def get_base_frame():
        return layout.copy()

    for f in range(frames_first):
        frame = get_base_frame()
        t = f / fps  
        osc_dx = int(oscillation_amplitude * math.sin(2 * math.pi * oscillation_frequency * t))
        osc_dy = int(oscillation_amplitude * math.cos(2 * math.pi * oscillation_frequency * t))
        if im1 is not None:
               superponer_imagen(frame, im1, x1 + osc_dx, y1 + osc_dy)
               draw_text_with_autowrap(frame, text1, x1 + w1//2 + osc_dx, (y1 - text_offset) + osc_dy,
                                max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
        video_out.write(frame)

    for f in range(frames_second):
        frame = get_base_frame()
        t = f / fps
        osc_dx = int(oscillation_amplitude * math.sin(2 * math.pi * oscillation_frequency * t))
        osc_dy = int(oscillation_amplitude * math.cos(2 * math.pi * oscillation_frequency * t))
        if im1 is not None:
            superponer_imagen(frame, im1, x1 + osc_dx, y1 + osc_dy)
            draw_text_with_autowrap(frame, text1, x1 + w1//2 + osc_dx, (y1 - text_offset) + osc_dy,
                                    max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
        if im2 is not None:
            superponer_imagen(frame, im2, x2 + osc_dx, y2 + osc_dy)
            draw_text_with_autowrap(frame, text2, x2 + w2//2 + osc_dx, (y2 - text_offset) + osc_dy,
                                    max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
        video_out.write(frame)

    clock_img_path = "app/Resources/RatherThan/clock.png"
    clock_img = cv2.imread(clock_img_path, cv2.IMREAD_UNCHANGED)
    if clock_img is not None:
        hc, wc = clock_img.shape[:2]
        cx = (width - wc) // 2
        cy = (height - hc) // 2
        for _ in range(frames_clock):
            frame = get_base_frame()
            if im1 is not None:
                superponer_imagen(frame, im1, x1, y1)
                draw_text_with_autowrap(frame, text1, x1 + w1//2, y1 - text_offset,
                                        max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
            if im2 is not None:
                superponer_imagen(frame, im2, x2, y2)
                draw_text_with_autowrap(frame, text2, x2 + w2//2, y2 - text_offset,
                                        max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
            superponer_imagen(frame, clock_img, (width - wc) // 2, (height - hc) // 2)
            video_out.write(frame)
    else:
        for _ in range(frames_clock):
            frame = get_base_frame()
            if im1 is not None:
                superponer_imagen(frame, im1, x1, y1)
                draw_text_with_autowrap(frame, text1, x1 + w1//2, y1 - text_offset,
                                        max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
            if im2 is not None:
                superponer_imagen(frame, im2, x2, y2)
                draw_text_with_autowrap(frame, text2, x2 + w2//2, y2 - text_offset,
                                        max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
            video_out.write(frame)

    for f in range(frames_percent):
        frame = get_base_frame()
        dx = int((oscillation_amplitude/2) * math.sin(2 * math.pi * f / frames_percent))
        if im1 is not None:
            im1_mod = rotate_image(im1, (f / frames_percent) * 5)
            if pct1 < pct2:
                tremor_dx = random.randint(-4, 4)
                tremor_dy = random.randint(-4, 4)
                x1_mod = x1 + tremor_dx
                y1_mod = y1 + tremor_dy
                final_im1 = im1_mod
            else:
                final_im1 = tint_green(im1_mod)
                x1_mod = x1
                y1_mod = y1
            superponer_imagen(frame, final_im1, x1_mod + dx, y1_mod)
            draw_text_with_autowrap(frame, text1, x1 + w1//2 + dx, y1 - text_offset,
                                    max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
            draw_text_with_autowrap(frame, pct1_str, x1 + w1//2 + dx, y1 + h1 + 50,
                                    max_width=width-40, initial_scale=1.8, thickness=5, outline_thickness=5,
                                    main_color=color1)
        if im2 is not None:
            im2_mod = rotate_image(im2, (f / frames_percent) * 5)
            if pct2 < pct1:
                tremor_dx = random.randint(-4, 4)
                tremor_dy = random.randint(-4, 4)
                x2_mod = x2 + tremor_dx
                y2_mod = y2 + tremor_dy
                final_im2 = im2_mod
            else:
                final_im2 = tint_green(im2_mod)
                x2_mod = x2
                y2_mod = y2
            superponer_imagen(frame, final_im2, x2_mod + dx, y2_mod)
            draw_text_with_autowrap(frame, text2, x2 + w2//2 + dx, y2 - text_offset,
                                    max_width=width-40, initial_scale=1.2, thickness=3, outline_thickness=3)
            draw_text_with_autowrap(frame, pct2_str, x2 + w2//2 + dx, y2 + h2 + 50,
                                    max_width=width-40, initial_scale=1.8, thickness=5, outline_thickness=5,
                                    main_color=color2)
        video_out.write(frame)
    video_out.release()
    cv2.destroyAllWindows()
    return output_path

def add_audio_and_voices_to_video(video_path, output_path, clock_effect_path, accert_effect_path,
                                  backgrounds_folder, voices_folder, clock_time, percent_time, voice_files,
                                  voice_delay=0, fps=30, intro_time=5.0):
    try:
        video_clip = VideoFileClip(video_path)
        total_duration = video_clip.duration
        bg_files = glob.glob(os.path.join(backgrounds_folder, "*"))
        if not bg_files:
            raise ValueError("No se encontraron archivos de backgrounds.")
        bg_choice = random.choice(bg_files)
        bg_audio = AudioFileClip(bg_choice)
        bg_audio = bg_audio.subclipped(0, total_duration) 


        intro_voice = AudioFileClip(voice_files[0])
        intro_duration = intro_voice.duration

        effect_clips = []
        num_pairs = len(voice_files) - 1
        accum = intro_duration

        for i in range(num_pairs):
            clock_effect = AudioFileClip(clock_effect_path)
            accert_effect = AudioFileClip(accert_effect_path)
            current_voice = AudioFileClip(voice_files[i+1])
            d_first = current_voice.duration / 2
            d_second = current_voice.duration / 2
            pair_duration_i = d_first + d_second + clock_time + percent_time
            voice_clip = current_voice.with_start(accum)
            clock_start = accum + d_first + d_second + voice_delay
            clock_clip = clock_effect.with_start(clock_start)
            accert_start = accum + d_first + d_second + clock_time
            accert_clip = accert_effect.with_start(accert_start)

            effect_clips.extend([voice_clip, clock_clip, accert_clip])
            accum += pair_duration_i


        all_audio_clips = [bg_audio, intro_voice] + effect_clips
        composite_audio = CompositeAudioClip(all_audio_clips)
        
        final_video = video_clip.with_audio(composite_audio)
        final_video.write_videofile(output_path, 
                                  codec="libx264", 
                                  audio_codec="aac",
                                  fps=fps,
                                  threads=4,
                                  preset='ultrafast')
        
        return output_path

    except Exception as e:
        print(f"Error: {str(e)}")
        raise

    finally:
        if 'video_clip' in locals():
            video_clip.close()
        if 'bg_audio' in locals():
            bg_audio.close()
        if 'intro_voice' in locals():
            intro_voice.close()
        if 'effect_clips' in locals():
            for clip in effect_clips:
                clip.close()
        if 'final_video' in locals():
            final_video.close()


def add_animated_clock_to_video(video_path, output_path, clock_gif_path, intro_time, delay_first_img,
                                delay_second_img, clock_time, percent_time, voice_files,
                                width=720, height=1280, fps=30, gif_width=None, gif_height=None):
    video_clip = VideoFileClip(video_path)
    total_duration = video_clip.duration
    clock_gif = VideoFileClip(clock_gif_path, has_mask=True)
    if gif_width or gif_height:
        clock_gif = clock_gif.resized(height=gif_height, width=gif_width)
    gif_duration = clock_gif.duration

    clock_clips = []
    num_pairs = len(voice_files) - 1  
    accum = AudioFileClip(voice_files[0]).duration

    for i in range(num_pairs):
        current_voice = AudioFileClip(voice_files[i+1])                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
        d_first = current_voice.duration / 2
        d_second = current_voice.duration / 2
        pair_duration_i = d_first + d_second + clock_time + percent_time
        t_start = accum + d_first + d_second
        num_loops = int(clock_time / gif_duration) + 1
        looped = concatenate_videoclips([clock_gif] * num_loops)
        looped = looped.subclipped(0, clock_time)
        looped = looped.with_start(t_start).with_position(("center", "center"))
        clock_clips.append(looped)
        accum += pair_duration_i
        current_voice.close()

    final_clip = CompositeVideoClip([video_clip] + clock_clips, size=(width, height))
    final_clip.duration = total_duration
    final_clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")
    video_clip.close()
    clock_gif.close()
    for c in clock_clips:
        c.close()
    return output_path

def generate_ratherof_video(intro_image,intro_text,pairs,voices_folder):
    clock_image = "app/Resources/RatherThan/clock.png"
    voice_files = sorted(glob.glob(os.path.join(voices_folder, "voice_*.*")),
                         key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
    if not voice_files:
        raise ValueError("No se encontraron archivos de voz en la carpeta de voces.")
    intro_time = AudioFileClip(voice_files[0]).duration
    delay_first_img = AudioFileClip(voice_files[1]).duration / 2
    delay_second_img = AudioFileClip(voice_files[1]).duration / 2
    clock_time = 2.85
    percent_time = 2.0
    vertical_adjust_1 = -20
    vertical_adjust_2 = 20
    scale_factor_pairs = 1.3
    oscillation_amplitude = 5


    intro_segment = create_intro_segment(intro_image, intro_text, "app/Resources/RatherThan/RatherThanLayout.png",
                                          720, 1280, 30, intro_time,intro_scale_factor=1.8)
    pair_segments = []
    num_pairs = len(pairs) // 2
    for i in range(num_pairs):
        seg_output = f"app\Resources\RatherThan\VideosTests\segment_pair_{i}.mp4"
        pair = [pairs[2*i], pairs[2*i+1]]
        vclip = AudioFileClip(voice_files[i+1])
        d_first = vclip.duration / 2
        d_second = vclip.duration / 2
        segment = create_pair_segment(pair, seg_output, "app/Resources/RatherThan/RatherThanLayout.png",
                                      720, 1280, 30, d_first, d_second, clock_time, percent_time,
                                      vertical_adjust_1, vertical_adjust_2, scale_factor_pairs, oscillation_amplitude)
        pair_segments.append(segment)
        vclip.close()

    all_segments = [VideoFileClip(intro_segment)] + [VideoFileClip(s) for s in pair_segments]
    final_video = concatenate_videoclips(all_segments)
    final_video.write_videofile(r"app\Resources\RatherThan\VideosTests\output_flow.mp4", fps=30, codec="libx264", audio_codec="aac")
    final_video.close()
    for clip in all_segments:
        clip.close()

    print_colored("Segmentos concatenados correctamente.", 32)

    video_path = r"app\Resources\RatherThan\VideosTests\output_flow.mp4"
    output_final = r"app\Resources\RatherThan\VideosTests\final_with_audio.mp4"
    clock_effect_path = "app/Resources/RatherThan/Sounds/sound_effects/clock.mp3"
    accert_effect_path = "app/Resources/RatherThan/Sounds/sound_effects/accert.mp3"
    backgrounds_folder = "app/Resources/RatherThan/Sounds/backgrounds"
    add_audio_and_voices_to_video(video_path, output_final, clock_effect_path, accert_effect_path,
                                  backgrounds_folder, voices_folder, clock_time, percent_time,
                                  voice_files, voice_delay=0, fps=30, intro_time=intro_time)
    print_colored("Audio y voces integrados correctamente.", 32)

    animated_clock_gif = "app/Resources/RatherThan/clock_gif.gif"
    output_final_animated = r"app\Resources\RatherThan\VideosTests\final_with_animated_clock.mp4"
    add_animated_clock_to_video(output_final, output_final_animated, animated_clock_gif,
                            intro_time, delay_first_img, delay_second_img, clock_time, percent_time,
                            voice_files, width=720, height=1280, fps=30, gif_width=200, gif_height=200)
    print_colored("Reloj animado integrado correctamente.", 32)

if __name__ == "__main__":
    intro_image = "app/Resources/RatherThan/ImagesExample/img0.png"
    intro_text  = "Veamos si eres un genio estrategico o simplemente un cobarde. Contesta con honestidad"
    pairs = [
        ("app/Resources/RatherThan/ImagesExample/img1.png", "Tener acceso a toda la informacion del mundo, pero no poder compartirla con nadie", 72),
        ("app/Resources/RatherThan/ImagesExample/img2.png", "Que todos tengan acceso a la informacion menos tu", 28),
        ("app/Resources/RatherThan/ImagesExample/img3.png", " Ser la persona mas inteligente del mundo, pero nadie te cree nunca", 80),
        ("app/Resources/RatherThan/ImagesExample/img4.png", "Ser promedio, pero que todos piensen que eres un genio", 20),
        ("app/Resources/RatherThan/ImagesExample/img5.png", "Tener el control total del mundo por un solo dia", 55),
        ("app/Resources/RatherThan/ImagesExample/img6.png", "Tener influencia sobre el mundo por toda tu vida, pero sin que nadie lo note", 45),
    ]
    voices_folder = "app/Resources/RatherThan/Sounds/voices"
    generate_ratherof_video(intro_image, intro_text, pairs, voices_folder)
    