import json, subprocess, os, whisper, gdown

def download_gdrive_folder(url):
    if not url: return
    print(f"📡 Syncing Google Drive Folder: {url}")
    # This downloads the entire folder into 'input/'
    # Note: Folder must be set to "Anyone with the link can view"
    gdown.download_folder(url, output="input/", quiet=False, use_cookies=False)

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

print("🚀 Loading Whisper AI...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

# 1. First, download files from the folder if a URL is provided in the first job
if jobs and "gdrive_folder_url" in jobs[0] and jobs[0]["gdrive_folder_url"]:
    download_gdrive_folder(jobs[0]["gdrive_folder_url"])

for job in jobs:
    input_path = find_file_case_insensitive("input/", job['original_file'])
    
    if not input_path or os.path.getsize(input_path) < 100000:
        print(f"❌ ERROR: {job['original_file']} not found or file is a corrupted link.")
        continue

    print(f"🎬 Processing: {input_path}")
    
    # 2. Whisper Transcription (Perfect Timing)
    result = model.transcribe(input_path)
    
    # 3. Trim and Reframe (9:16 Vertical)
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

    # 4. Concatenate segments (Hook First)
    if not segment_files: continue
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    # 5. Build Timed Captions
    cap_filters = []
    current_offset = 0.0
    # Use manual captions if they exist, otherwise use Whisper auto-captions
    source_caps = job.get('captions', [])
    if source_caps:
        for c in source_caps:
            txt = c['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black")
    else:
        for s in result['segments']:
            txt = s['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{s['start']},{s['end']})':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black")

    # 6. Final Export
    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:70]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    if os.path.exists("list.txt"): os.remove("list.txt")
    if os.path.exists("combined.mp4"): os.remove("combined.mp4")

print("✅ Batch complete. Check output folder!")
