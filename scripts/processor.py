import json, subprocess, os, whisper, gdown, re

def sync_gdrive_folder(url):
    print(f"📡 Syncing Google Drive Folder...")
    os.makedirs("input", exist_ok=True)
    # This downloads the entire folder content into 'input/'
    gdown.download_folder(url, output="input/", quiet=False, use_cookies=False)

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

print("🚀 Loading AI Agent: Pro Visual Architect Edition...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

# 1. Sync Folder if URL is provided in the first task
if jobs and jobs[0].get("gdrive_folder_url"):
    sync_gdrive_folder(jobs[0]["gdrive_folder_url"])

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    target_name = job['original_file']
    input_path = find_file_case_insensitive("input/", target_name)
    
    if not input_path:
        print(f"❌ Skipping {target_name}: Not found in folder."); continue

    # 2. Transcribe for Auto-Captions
    print(f"🎙️ Generating perfect timestamps for {target_name}...")
    result = model.transcribe(input_path)
    
    # 3. Process Segments with Complex Layouts
    segment_files = []
    durations = []
    
    # COMPLEX LOGIC: The 'frame_filter' is now a full FFmpeg recipe
    frame_recipe = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"t{task_idx}_s{i}.mp4"
        # We apply the recipe and force a social media export size (1080x1920)
        final_vf = f"{frame_recipe},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        print(f"✂️ Rendering Layout for Segment {i}...")
        subprocess.run(["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", final_vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg])
        
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 4. Stitching
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # 5. Advanced Viral Captions
    # Style: Yellow bold text, black thick border, centered bottom
    cap_filters = []
    current_offset = 0.0
    
    # Priority 1: Manual 'Hook' Captions from JSON
    for c in job.get('captions', []):
        txt = c['text'].replace("'", "").strip().upper()
        cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=55:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-400")
    
    # Priority 2: Auto-Whisper Captions for the rest of the video
    for s in result['segments']:
        # We only add auto-caps if there isn't a manual cap overlapping (simplified)
        txt = s['text'].replace("'", "").strip().upper()
        cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{s['start']},{s['end']})':fontcolor=white:fontsize=45:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-250")

    final_output = f"output/{job['new_title']}"
    # Join first 100 caption filters
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:100]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)

print(f"✅ BATCH FINISHED! #viralitypoly")
