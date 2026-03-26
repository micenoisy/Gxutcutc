import json, subprocess, os, whisper, gdown

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def download_specific_file(url, target_name):
    print(f"📡 File not found locally. Downloading from Google Drive: {target_name}...")
    try:
        # Downloads specific file and renames it to match your JSON
        output_path = f"input/{target_name}"
        gdown.download(url, output=output_path, quiet=False, fuzzy=True)
        return output_path
    except Exception as e:
        print(f"❌ DOWNLOAD ERROR: Could not download {target_name}. Error: {e}")
        return None

print("🚀 Loading Whisper AI (Cached version)...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

for job in jobs:
    target_name = job['original_file']
    
    # STEP 1: Search locally in input/ folder
    input_path = find_file_case_insensitive("input/", target_name)
    
    # STEP 2: If not found, download from GDrive
    if not input_path:
        if "gdrive_url" in job and job["gdrive_url"]:
            input_path = download_specific_file(job["gdrive_url"], target_name)
        else:
            print(f"❌ ERROR: {target_name} not found locally and no Google Drive link provided.")
            continue

    # STEP 3: Final validation of file
    if not input_path or os.path.getsize(input_path) < 100000:
        print(f"❌ ERROR: {target_name} is missing or corrupted (File too small).")
        continue

    print(f"✅ Processing: {input_path}")
    
    # 4. Transcription & Timing
    try:
        result = model.transcribe(input_path)
    except Exception as e:
        print(f"❌ WHISPER ERROR on {target_name}: {e}"); continue
    
    # 5. Segmenting & 9:16 Vertical Reframing
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

    # 6. Stitching & Timeline Captioning
    if not segment_files: continue
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    cap_filters = []
    # If JSON has captions, use them. Else, use Whisper auto-captions.
    source_caps = job.get('captions', [])
    if source_caps:
        for c in source_caps:
            txt = c['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black")
    else:
        for s in result['segments']:
            txt = s['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{s['start']},{s['end']})':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black")

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:75]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    if os.path.exists("list.txt"): os.remove("list.txt")
    if os.path.exists("combined.mp4"): os.remove("combined.mp4")

print(f"🚀 Job for {job['new_title']} finished successfully! #viralitypoly")
