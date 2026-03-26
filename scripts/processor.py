import json, subprocess, os, whisper, gdown, yt_dlp

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def smart_download(url, target_name):
    """Detects if URL is YouTube or GDrive and downloads accordingly."""
    os.makedirs("input", exist_ok=True)
    output_path = os.path.join("input", target_name)
    
    # Clean up old corrupted files
    if os.path.exists(output_path):
        os.remove(output_path)

    print(f"📡 Attempting download: {url}")
    
    try:
        if "youtube.com" in url or "youtu.be" in url:
            print("🎥 Detected YouTube Link. Using yt-dlp...")
            ydl_opts = {
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                'outtmpl': output_path,
                'quiet': False,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        elif "drive.google.com" in url:
            print("📂 Detected Google Drive Link. Using gdown...")
            gdown.download(url, output=output_path, quiet=False, fuzzy=True)
            
        else:
            print("❌ ERROR: Unsupported URL. Use YouTube or GDrive.")
            return None
            
        # Final check: If file is too small, it's not a video
        if os.path.exists(output_path) and os.path.getsize(output_path) < 100000:
            print(f"❌ ERROR: Downloaded file is too small ({os.path.getsize(output_path)} bytes). Likely a blocked link or error page.")
            return None

        print(f"✅ Download Success: {output_path} ({os.path.getsize(output_path)} bytes)")
        return output_path

    except Exception as e:
        print(f"❌ DOWNLOAD FAILED: {e}")
        return None

print("🚀 Starting AI Multi-Task Agent...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    target_name = job.get('original_file', f"task_{task_idx}.mp4")
    video_url = job.get('video_url', job.get('gdrive_url', None)) # Checks both keys
    
    # 1. Search Locally or Download
    input_path = find_file_case_insensitive("input/", target_name)
    if not input_path and video_url:
        input_path = smart_download(video_url, target_name)

    if not input_path or not os.path.exists(input_path):
        print(f"❌ Skipping {target_name}: File not available."); continue

    # 2. Transcribe (Whisper)
    print(f"🎙️ Transcribing {target_name}...")
    result = model.transcribe(input_path)
    
    # 3. Process Segments
    segment_files = []
    durations = []
    raw_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"t{task_idx}_s{i}.mp4"
        # Pro-Reframing Logic: Forces 9:16 vertical regardless of original style
        final_vf = f"{raw_filter},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", final_vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        subprocess.run(cmd)
        
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 4. Join and Caption
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    cap_filters = []
    # Use JSON captions
    for c in job.get('captions', []):
        txt = c['text'].replace("'", "").strip().upper()
        cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=h-300:borderw=3:bordercolor=black")

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:70]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)

print("🚀 ALL DONE! #viralitypoly")
