
import cv2,sys,os
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from app.Utils.general_utils import print_colored
from moviepy import AudioFileClip
from PIL import ImageSequence,Image


def add_animated_clock_to_video(video_path, output_path, clock_gif_path, intro_time, delay_first_img,
                                delay_second_img, clock_time, percent_time, voice_files,
                                width=720, height=1280, fps=30, gif_width=None, gif_height=None, transition_clip=None):
    print_colored("Iniciando integración de reloj animado...", 36)
    
    # Load the video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video desde {video_path}")
    
    # Get video properties
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = frame_count / video_fps
    
    # Load GIF with PIL
    gif = Image.open(clock_gif_path)
    gif_frames = []
    for frame in ImageSequence.Iterator(gif):
        if frame.mode != 'RGBA':
            frame = frame.convert('RGBA')
        # Resize if dimensions are provided
        if gif_width and gif_height:
            frame = frame.resize((gif_width, gif_height), Image.LANCZOS)
        gif_frames.append(np.array(frame))
    
    gif_frame_count = len(gif_frames)
    print_colored(f"GIF cargado: {gif_frame_count} frames", 36)
    
    # Calculate timing for each clock segment
    clock_segments = []
    num_pairs = len(voice_files) - 1
    accum = AudioFileClip(voice_files[0]).duration  # Intro duration
    transition_duration = transition_clip.duration if transition_clip else 0
    
    for i in range(num_pairs):
        current_voice = AudioFileClip(voice_files[i+1])
        d_first = current_voice.duration / 2
        d_second = current_voice.duration / 2
        pair_duration = d_first + d_second + clock_time + percent_time
        
        # Calculate when the clock should appear
        clock_start = accum + d_first + d_second
        clock_end = clock_start + clock_time
        
        clock_segments.append((clock_start, clock_end))
        accum += pair_duration
        
        # Add transition duration after each segment (except the last one)
        if i < num_pairs - 1 and transition_clip:
            accum += transition_duration
            
        current_voice.close()
    
    # Set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, video_fps, (width, height))
    
    # Process each frame
    frame_index = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        current_time = frame_index / video_fps
        
        # Check if we need to overlay the animated clock at this time
        for i, (start_time, end_time) in enumerate(clock_segments):
            if start_time <= current_time < end_time:
                # Calculate which frame of the GIF to use
                elapsed_in_clock = current_time - start_time
                gif_index = int((elapsed_in_clock * fps) % gif_frame_count)
                
                # Get the corresponding GIF frame
                gif_frame = gif_frames[gif_index]
                
                # Calculate center position for overlay
                y_offset = (height - gif_frame.shape[0]) // 2
                x_offset = (width - gif_frame.shape[1]) // 2
                
                # Extract alpha channel and RGB
                alpha = gif_frame[:, :, 3:4] / 255.0
                rgb = gif_frame[:, :, :3]
                rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                
                # Define ROI and overlay
                roi = frame[y_offset:y_offset + gif_frame.shape[0], 
                            x_offset:x_offset + gif_frame.shape[1]]
                
                # Apply alpha blending
                blended = roi * (1 - alpha) + rgb_bgr * alpha
                frame[y_offset:y_offset + gif_frame.shape[0], 
                      x_offset:x_offset + gif_frame.shape[1]] = blended
                
                break
        
        # Write the frame
        out.write(frame.astype(np.uint8))
        frame_index += 1
        
        # Progress indicator
        if frame_index % 30 == 0:
            progress = (frame_index / frame_count) * 100
            print_colored(f"Progreso: {progress:.1f}%", 36, end="\r")
    
    # Release resources
    cap.release()
    out.release()
    print_colored("\nProcesamiento de video con reloj animado completado.", 36)
    
    return output_path


if __name__ == "__main__":
    # Paths
    input_video_path = r"app\Resources\RatherThan\VideosTests\final_with_audio.mp4"  # Input video
    output_video_path = r"app\Resources\RatherThan\VideosTests\test_clock_overlay.mp4"  # Output path
    clock_gif_path = r"app\Resources\RatherThan\clock_gif.gif"  # Clock GIF
    
    # Create dummy voice files for testing or use existing files
    voices_folder = r"app\Resources\RatherThan\Sounds\voices"
    voice_files = sorted([os.path.join(voices_folder, f) for f in os.listdir(voices_folder) if f.startswith("voice_")])
    
    if not voice_files:
        print_colored("No voice files found, creating dummy files for testing", 33)
        # Create dummy voice files if none exist
        os.makedirs(voices_folder, exist_ok=True)
        dummy_audio = np.zeros((44100 * 3,))  # 3 seconds of silence
        import scipy.io.wavfile as wav
        for i in range(3):
            wav.write(os.path.join(voices_folder, f"voice_{i}.wav"), 44100, dummy_audio)
        voice_files = sorted([os.path.join(voices_folder, f) for f in os.listdir(voices_folder) if f.startswith("voice_")])
    
    # Timing parameters
    intro_time = 5.0
    delay_first_img = 2.0
    delay_second_img = 2.0
    clock_time = 3.0
    percent_time = 2.0
    
    # Call the function
    print("Running animated clock overlay test...")
    output = add_animated_clock_to_video(
        video_path=input_video_path,
        output_path=output_video_path,
        clock_gif_path=clock_gif_path,
        intro_time=intro_time,
        delay_first_img=delay_first_img,
        delay_second_img=delay_second_img,
        clock_time=clock_time,
        percent_time=percent_time,
        voice_files=voice_files,
        gif_width=200,
        gif_height=200,
        transition_clip=None  # You can create a transition clip if needed
    )
    
    print(f"Test completed. Output saved to: {output}")
    
    # Optional: Open the resulting video with the default player
    import subprocess
    try:
        os.startfile(output)  # Windows-specific
    except:
        print("Couldn't open the video automatically. Please check the output path.")