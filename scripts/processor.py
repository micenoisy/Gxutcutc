import json, subprocess, os, whisper, gdown, re

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def sync_gdrive(url):
    if not url: return
    print(f"📡 Syncing Google Drive Folder...")
    os.makedirs("input", exist_ok=True)
    gdown.download_folder(url, output="input/", quiet=False, use_cookies=False)

print("🚀 AI Agent: Multi-Clip Pro Edition Loading...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

# 1. Initial Sync
if jobs and jobs[0].get("gdrive_folder_url"):
    sync_gdrive(jobs[0]["gdrive_folder_url"])

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    target_name = job['original_file']
    input_path = find_file_case_insensitive("input/", target_name)
    
    if not input_path:
        print(f"❌ Skipping {target_name}: Not found."); continue

    print(f"🎬 Creating Task: {job['new_title']}")

    # 2. Segmenting & Reframing
    # The 'frame_filter' is provided by the Analyzer AI in the JSON
    recipe = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    segment_files = []
    durations = []
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_s{i}.mp4"
        # Apply visual recipe + social media standardization (1080x1920)
        vf = f"{recipe},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        subprocess.run(["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg])
        
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 3. Join Segments
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # 4. Viral Caption Engine (Whisper-Powered)
    # Transcribe the combined video for perfect alignment
    print(f"🎙️ Generating full-video captions...")
    result = model.transcribe(combined)
    
    cap_filters = []
    # Add Manual Captions from JSON first (Higher Priority)
    for c in job.get('captions', []):
        txt = c['text'].replace("'", "").strip().upper()
        cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=55:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-450")

    # Add Whisper Auto-Captions for the rest of the dialogue
    for s in result['segments']:
        txt = s['text'].replace("'", "").strip().upper()
        cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{s['start']},{s['end']})':fontcolor=white:fontsize=45:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-250")

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:100]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)

print("🚀 PRODUCTION RUN COMPLETE #viralitypoly")
