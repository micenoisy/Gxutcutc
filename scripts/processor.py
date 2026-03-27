import json, subprocess, os

# Ensure folders exist at the very start
os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

with open('master_config.json') as f:
    jobs = json.load(f)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job or "__AI_DOCUMENTATION__" in job: continue
    
    # AUTO-DETECT: Find the video file in the input folder (ignore filename from JSON)
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
    if not input_files:
        print(f"❌ No video found for task {task_idx}")
        continue
    
    input_path = os.path.join("input", input_files[0])
    print(f"🎬 Processing Task {task_idx} with file: {input_path}")

    # 1. Clipping & Framing (9:16 Vertical)
    segment_files = []
    durations = []
    frame_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_seg{i}.mp4"
        # Pro-Reframing: Force 1080x1920
        vf = f"{frame_filter},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        subprocess.run(["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg])
        
        if os.path.exists(temp_seg):
            dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(dur))
            segment_files.append(temp_seg)

    # 2. Stitch Segments
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # 3. Caption Style: Full Width White Bar + Persistent Black Text
    cap_filters = []
    source_caps = job.get('captions', [])
    for j, c in enumerate(source_caps):
        txt = c['text'].replace("'", "").upper().strip()
        start = float(c['start'])
        # Persistent logic: End of current is Start of next
        end = float(source_caps[j+1]['start']) if j+1 < len(source_caps) else float(sum(durations))
        
        draw_bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=140:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:x=(w-text_w)/2:y=h-410:enable='between(t,{start},{end})'"
        cap_filters.extend([draw_bar, draw_txt])

    # 4. Final Export
    final_output = f"output/{job['new_title']}"
    # Use as many captions as needed; ffmpeg handles the chain
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    
    # 5. Cleanup to save disk space (Crucial for 8-hour runs)
    for s in segment_files: os.remove(s)
    if os.path.exists(list_file): os.remove(list_file)
    if os.path.exists(combined): os.remove(combined)
    os.remove(input_path) # Delete original huge video to keep disk clean

print("🚀 ALL TASKS FINISHED #viralitypoly")
