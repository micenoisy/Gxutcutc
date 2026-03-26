import json, subprocess, os, whisper, gdown, yt_dlp

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def download_video_segments(url, task_idx, segments):
    """Downloads ONLY the required seconds from a long YouTube video."""
    os.makedirs("input", exist_ok=True)
    segment_files = []
    
    print(f"📡 YouTube detected. Downloading specific segments from 1.5hr video...")
    
    try:
        for i, seg in enumerate(segments):
            output_path = f"t{task_idx}_seg{i}_raw.mp4"
            
            # Convert HH:MM:SS to seconds for yt-dlp
            def to_secs(ts):
                parts = ts.split(':')
                return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])

            start_sec = to_secs(seg['start'])
            end_sec = to_secs(seg['end'])

            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]', # Lower res for speed
                'outtmpl': output_path,
                'download_ranges': lambda info, ctx: [{'start_time': start_sec, 'end_time': end_sec}],
                'force_keyframes_at_cuts': True,
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if os.path.exists(output_path):
                segment_files.append(output_path)
        
        return segment_files
    except Exception as e:
        print(f"❌ YOUTUBE SEGMENT DOWNLOAD FAILED: {e}")
        return None

print("🚀 Starting AI Agent (Ultra-Fast Segment Mode)...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    target_name = job.get('original_file', f"task_{task_idx}.mp4")
    video_url = job.get('video_url', None)
    
    # 1. SPECIAL LOGIC: For YouTube, download segments directly
    if video_url and ("youtube.com" in video_url or "youtu.be" in video_url):
        raw_segments = download_video_segments(video_url, task_idx, job['segments'])
        if not raw_segments:
            print(f"❌ Skipping {target_name}: Bot detection or link error."); continue
    else:
        # Fallback to local or GDrive (Full Download)
        print("📂 Using standard download/local mode...")
        # (Standard code for GDrive/Local goes here - same as previous versions)
        continue 

    # 2. Transcribe the FIRST segment to get speech data (Fastest for 1.5hr videos)
    print(f"🎙️ Transcribing segment 0 for captions...")
    result = model.transcribe(raw_segments[0])
    
    # 3. Final Reframe & Edit
    processed_segments = []
    durations = []
    raw_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, raw_seg in enumerate(raw_segments):
        final_seg = f"t{task_idx}_final_s{i}.mp4"
        # Reframing
        vf = f"{raw_filter},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        subprocess.run(["ffmpeg", "-y", "-i", raw_seg, "-vf", vf, "-c:v", "libx264", "-crf", "18", final_seg])
        
        if os.path.exists(final_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", final_seg])
            durations.append(float(prob))
            processed_segments.append(final_seg)

    # 4. Join and Apply Captions
    if not processed_segments: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in processed_segments: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    cap_filters = []
    for c in job.get('captions', []):
        txt = c['text'].replace("'", "").strip().upper()
        cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=h-300:borderw=3:bordercolor=black")

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:70]), "-c:a", "copy", final_output])

    # Cleanup
    for s in raw_segments + processed_segments: 
        if os.path.exists(s): os.remove(s)
    os.remove(list_file); os.remove(combined)

print("🚀 ALL DONE! #viralitypoly")