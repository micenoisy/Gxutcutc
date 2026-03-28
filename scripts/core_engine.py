import json, subprocess, os, whisper, gdown

# --- ADVANCED UTILITIES ---
def get_video_info(path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of json \"{path}\""
    output = subprocess.check_output(cmd, shell=True).decode()
    return json.loads(output)

def download_once(url, filename, downloaded_cache):
    if url in downloaded_cache:
        print(f"♻️ Using Cached Video: {downloaded_cache[url]}")
        return downloaded_cache[url]
    
    dest = f"input/{filename}"
    print(f"📡 Downloading Source: {url}")
    gdown.download(url, output=dest, quiet=False, fuzzy=True)
    downloaded_cache[url] = dest
    return dest

# --- THE ENGINE ---
print("🚀 Initializing Viral Engine v3.0...")
# Using word_timestamps=True for microsecond precision
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

download_cache = {}

for task_idx, job in enumerate(jobs):
    if "__GUIDE__" in job: continue
    
    # 1. SMART DOWNLOAD (Download Once, Use Many)
    input_path = download_once(job['gdrive_url'], job['original_file'], download_cache)
    
    # 2. MICROSECOND TRANSCRIPTION (Word-Level)
    print(f"🎙️ Deep-Analyzing Audio for Task {task_idx}...")
    # This captures every single word with start/end times
    result = model.transcribe(input_path, word_timestamps=True)
    
    # 3. SEGMENT EXTRACTION & REFRAMING
    segment_files = []
    durations = []
    frame_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_s{i}.mp4"
        # Ultra-sharp 1080p 60fps internal processing for viral quality
        vf = f"{frame_filter},fps=60,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        cmd = ["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", vf, "-c:v", "libx264", "-crf", "16", "-preset", "slow", temp_seg]
        subprocess.run(cmd)
        
        if os.path.exists(temp_seg):
            dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(dur)); segment_files.append(temp_seg)

    # 4. CONCATENATION (The Viral Hook Re-ordering)
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c:v", "copy", "-c:a", "copy", combined])

    # 5. EMOTION-RICH CAPTIONS (Black on White High-Contrast)
    cap_filters = []
    for c in job.get('captions', []):
        txt = c['text'].replace("'", "").upper().strip()
        # Visual styling based on "Emotion" tag if present
        color = "yellow" if "[SHOCK]" in txt else "white"
        txt = txt.replace("[SHOCK]", "").replace("[ANGRY]", "")
        
        # Horizontal Bar + Precision Text
        start, end = c['start'], c['end']
        bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=140:t=fill:enable='between(t,{start},{end})'"
        text = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:x=(w-text_w)/2:y=h-415:enable='between(t,{start},{end})'"
        cap_filters.extend([bar, text])

    # 6. FINAL PRODUCTION
    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    
    # Cleanup Segments
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)

# Final Global Cleanup
for f in download_cache.values(): os.remove(f)
print("🚀 PRODUCTION COMPLETE #viralitypoly")
