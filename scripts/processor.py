import json, subprocess, os, whisper, gdown

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def download_specific_file(url, target_name):
    print(f"📡 Downloading from Google Drive: {target_name}...")
    try:
        output_path = f"input/{target_name}"
        # fuzzy=True helps gdown find the file ID from a standard sharing link
        gdown.download(url, output=output_path, quiet=False, fuzzy=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
        else:
            return None
    except Exception as e:
        print(f"❌ DOWNLOAD ERROR: {e}")
        return None

print("🚀 Loading Whisper AI (Cached version)...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

for job in jobs:
    target_name = job['original_file']
    # Check for any possible link key
    link = job.get("gdrive_url") or job.get("video_url") or job.get("url")
    
    # STEP 1: Search locally
    input_path = find_file_case_insensitive("input/", target_name)
    
    # STEP 2: If not found locally, try downloading
    if not input_path or not os.path.exists(input_path):
        if link:
            input_path = download_specific_file(link, target_name)
        else:
            print(f"❌ ERROR: {target_name} not found and NO LINK provided in JSON.")
            continue

    # STEP 3: Validate file existence and size
    if not input_path or not os.path.exists(input_path) or os.path.getsize(input_path) < 100000:
        print(f"❌ ERROR: File {target_name} is missing or download failed.")
        continue

    print(f"✅ Processing: {input_path}")
    
    # 4. Transcription
    try:
        result = model.transcribe(input_path)
    except Exception as e:
        print(f"❌ WHISPER ERROR: {e}"); continue
    
    # 5. Segmenting & Vertical Reframe
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

    # 6. Stitching & Captioning
    if not segment_files: 
        print(f"❌ ERROR: No segments were created for {target_name}")
        continue

    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    cap_filters = []
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
    print(f"🚀 FINISHED: {job['new_title']} #viralitypoly")

print("✨ All jobs completed.")    if os.path.exists("combined.mp4"): os.remove("combined.mp4")
    print(f"🚀 FINISHED: {job['new_title']} #viralitypoly")

print("✨ All jobs completed.")    if os.path.exists("combined.mp4"): os.remove("combined.mp4")
    print(f"🚀 FINISHED: {job['new_title']} #viralitypoly")

print("✨ All jobs completed.")
