import json, subprocess, os, whisper, urllib.request

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def download_video(url, dest):
    print(f"📥 Downloading video from URL...")
    urllib.request.urlretrieve(url, dest)
    print(f"✅ Download complete: {dest} ({os.path.getsize(dest)} bytes)")

print("🚀 Loading Whisper AI...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

for job in jobs:
    # Use URL if provided, otherwise look in input folder
    if "video_url" in job and job["video_url"]:
        input_path = f"input/{job['original_file']}"
        download_video(job["video_url"], input_path)
    else:
        input_path = find_file_case_insensitive("input/", job['original_file'])
    
    if not input_path or os.path.getsize(input_path) < 1000:
        print(f"❌ ERROR: File {job['original_file']} is missing or too small (Corrupted).")
        continue

    print(f"🎬 Processing: {input_path}")
    
    # 1. Transcribe
    result = model.transcribe(input_path)
    
    # 2. Extract Segments and Crop
    segment_files = []
    durations = []
    for i, seg in enumerate(job['segments']):
        temp_seg = f"seg_{i}.mp4"
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", f"{job['frame_config']},fps=30",
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        subprocess.run(cmd)
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 3. Join and Caption
    if not segment_files: continue
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    cap_filters = []
    current_offset = 0.0
    # Use JSON captions if they exist, otherwise use Whisper
    source_caps = job.get('captions', [])
    
    if not source_caps: # Fallback to Whisper
        for s in result['segments']:
            text = s['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{text}':enable='between(t,{s['start']},{s['end']})':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black")
    else:
        for c in source_caps:
            text = c['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{text}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black")

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:60]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    if os.path.exists("list.txt"): os.remove("list.txt")
    if os.path.exists("combined.mp4"): os.remove("combined.mp4")

print("✅ Success! Check output folder.")
