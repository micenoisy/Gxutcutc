import json, subprocess, os, whisper, gdown, urllib.request

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
        gdown.download(url, output=output_path, quiet=False, fuzzy=True)
        return output_path
    except Exception as e:
        print(f"❌ DOWNLOAD ERROR for {target_name}: {e}")
        return None

print("🚀 Starting AI Agent (Multi-Task Mode)...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

for task_index, job in enumerate(jobs):
    target_name = job['original_file']
    print(f"\n--- 🛠️ TASK {task_index + 1}: {target_name} ---")
    
    # 1. Search Locally or Download
    input_path = find_file_case_insensitive("input/", target_name)
    if not input_path and "gdrive_url" in job and job["gdrive_url"]:
        input_path = download_specific_file(job["gdrive_url"], target_name)
    
    if not input_path or not os.path.exists(input_path):
        print(f"❌ SKIPPING: File {target_name} not found."); continue

    # 2. Transcription (Whisper v2 Cached)
    print(f"🎙️ Transcribing {target_name}...")
    result = model.transcribe(input_path)
    
    # 3. Framing & Segmenting (DYNAMIC CROP/LAYOUT)
    segment_files = []
    durations = []
    
    # Get the framing instruction from JSON (Default to 9:16 center if missing)
    frame_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_index}_seg{i}.mp4"
        print(f"✂️ Trimming Segment {i} with frame style: {frame_filter[:30]}...")
        
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", f"{frame_filter},fps=30,scale=1080:1920",
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        subprocess.run(cmd)
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 4. Concatenate segments (Hook First)
    if not segment_files: continue
    list_file = f"list_task{task_index}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_task{task_index}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # 5. Captions (Aligned to segments)
    cap_filters = []
    current_offset = 0.0
    source_caps = job.get('captions', [])
    
    if source_caps: # Manual Captions
        for c in source_caps:
            txt = c['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=48:x=(w-text_w)/2:y=h-250:borderw=3:bordercolor=black")
    else: # Whisper Auto-Captions
        for s in result['segments']:
            txt = s['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{s['start']},{s['end']})':fontcolor=yellow:fontsize=48:x=(w-text_w)/2:y=h-250:borderw=3:bordercolor=black")

    # 6. Final Production
    final_output = f"output/{job['new_title']}"
    # Use first 80 captions to prevent command-line overflow
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:80]), "-c:a", "copy", final_output])

    # 7. Cleanup task files
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)
    print(f"✅ TASK COMPLETE: {job['new_title']} #viralitypoly")

print("\n🚀 ALL TASKS FINISHED SUCCESSFULLY!")
