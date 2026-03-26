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
        gdown.download(url, output=output_path, quiet=False, fuzzy=True)
        return output_path
    except Exception as e:
        print(f"❌ DOWNLOAD ERROR: {e}")
        return None

print("🚀 Starting AI Multi-Task Agent...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

for task_idx, job in enumerate(jobs):
    # Skip the __AI_GUIDE__ section if it's there
    if "__AI_GUIDE__" in job or "__INSTRUCTIONS__" in job: continue
    
    target_name = job['original_file']
    input_path = find_file_case_insensitive("input/", target_name)
    
    if not input_path and job.get("video_url"):
        input_path = download_specific_file(job["video_url"], target_name)

    if not input_path or not os.path.exists(input_path):
        print(f"❌ Skipping {target_name}: Not found."); continue

    # 1. Transcribe
    result = model.transcribe(input_path)
    
    # 2. Process Segments with "Visual Recipe"
    segment_files = []
    durations = []
    
    # Logic: Get filter from JSON. Default to standard 9:16 crop if missing.
    raw_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_seg{i}.mp4"
        
        # FIX: Wrap the complex filter so it plays nice with scale/fps
        # This ensures the output is always 1080x1920 regardless of layout
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

    # 3. Join & Caption
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    cap_filters = []
    current_offset = 0.0
    for i, seg in enumerate(job['segments']):
        seg_start = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['start'].split(':'))))
        seg_end = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['end'].split(':'))))
        
        # Use JSON captions if they exist
        for c in job.get('captions', []):
            txt = c['text'].replace("'", "").strip().upper()
            cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=h-300:borderw=3:bordercolor=black")
        
        # If no manual captions, you can uncomment this to use Whisper auto-caps
        # for s in result['segments']:
        #    if s['start'] >= seg_start and s['end'] <= seg_end:
        #        ... (Logic to add whisper caps) ...

        current_offset += durations[i]

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:70]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)

print("🚀 ALL DONE! #viralitypoly")
