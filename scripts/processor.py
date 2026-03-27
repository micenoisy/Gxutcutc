import json, subprocess, os, gdown

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

with open('master_config.json') as f:
    jobs = json.load(f)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    # 1. Download directly using URL
    print(f"📡 Downloading Task {task_idx}...")
    downloaded_path = gdown.download(job['gdrive_url'], output='input/', quiet=False, fuzzy=True)
    
    if not downloaded_path or not os.path.exists(downloaded_path):
        print("❌ Download failed!"); continue

    # 2. Clipping & Framing
    segment_files = []
    durations = []
    frame_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_seg{i}.mp4"
        vf = f"{frame_filter},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        subprocess.run(["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", downloaded_path, "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg])
        
        if os.path.exists(temp_seg):
            dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(dur)); segment_files.append(temp_seg)

    # 3. Join & Caption (Horizontal White Bar style)
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    cap_filters = []
    for j, c in enumerate(job.get('captions', [])):
        txt = c['text'].replace("'", "").upper()
        draw_bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=130:t=fill:enable='between(t,{c['start']},{c['end']})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:x=(w-text_w)/2:y=h-415:enable='between(t,{c['start']},{c['end']})'"
        cap_filters.extend([draw_bar, draw_txt])

    # 4. Final Save
    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    
    # Cleanup
    os.remove(downloaded_path) # Delete heavy raw video after use
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)

print("🚀 ALL TASKS FINISHED #viralitypoly")
