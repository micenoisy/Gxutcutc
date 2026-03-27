import json, subprocess, os, whisper, gdown

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def download_from_gdrive(url, target_name):
    print(f"📡 Syncing Large File from Google Drive: {target_name}...")
    try:
        os.makedirs("input", exist_ok=True)
        output_path = f"input/{target_name}"
        if os.path.exists(output_path): os.remove(output_path)
        # fuzzy=True handles both file and folder links
        gdown.download(url, output=output_path, quiet=False, fuzzy=True)
        return output_path
    except Exception as e:
        print(f"❌ DOWNLOAD ERROR: {e}")
        return None

print("🚀 Starting AI Video House (Long-Form Support Mode)...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    target_name = job['original_file']
    input_path = find_file_case_insensitive("input/", target_name)
    
    if not input_path and job.get("gdrive_url"):
        input_path = download_from_gdrive(job["gdrive_url"], target_name)

    if not input_path or not os.path.exists(input_path):
        print(f"❌ Skipping {target_name}: File not found."); continue

    # 1. Transcribe the whole video (even 8 hours)
    print(f"🎙️ Analyzing Audio for {target_name}...")
    result = model.transcribe(input_path)
    
    # 2. Process Viral Segments
    segment_files = []
    durations = []
    raw_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"t{task_idx}_s{i}.mp4"
        # Pro-Vertical Reframe logic
        final_vf = f"{raw_filter},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        print(f"✂️ Cutting Segment {i}: {seg['start']} to {seg['end']}")
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

    # 3. Stitch Segments
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # 4. Professional Caption Engine (Black Text on White Bar)
    cap_filters = []
    # Logic: Draw a white box across the full width, then center the black text inside it.
    # The bar is positioned at the bottom third (y=h-450)
    
    source_caps = job.get('captions', [])
    for j, c in enumerate(source_caps):
        txt = c['text'].replace("'", "").strip().upper()
        start = c['start']
        # Persistence: If next caption exists, extend current one until then
        end = source_caps[j+1]['start'] if j+1 < len(source_caps) else durations[0]
        
        # DRAWBOX creates the white bar, DRAWTEXT creates the black text
        draw_bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=120:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:font='Verdana':x=(w-text_w)/2:y=h-420:enable='between(t,{start},{end})'"
        cap_filters.append(draw_bar)
        cap_filters.append(draw_txt)

    # 5. Export Final Viral Video
    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])

    # 6. Cleanup (Essential for 8-hour files to save disk space)
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)
    print(f"✅ PRODUCTION COMPLETE: {final_output}")

print("🚀 ALL TASKS FINISHED #viralitypoly")
