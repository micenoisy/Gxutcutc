import json, subprocess, os

# Ensure folders exist
os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

with open('master_config.json') as f:
    jobs = json.load(f)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job or "__AI_DOCUMENTATION__" in job: continue
    
    # AUTO-DETECT Video in input folder
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
    if not input_files:
        print(f"❌ Task {task_idx}: No video file found in input folder.")
        continue
    
    input_path = os.path.join("input", input_files[0])
    print(f"🎬 Processing Task {task_idx}: {input_path}")

    # 1. Clipping & Vertical Framing
    segment_files = []
    durations = []
    
    # Get the raw filter and ensure multiplication symbols are safe
    user_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_seg{i}.mp4"
        
        # We process the user's crop first, then force the 1080x1920 output size
        # Added quotes and escape-safe formatting for FFmpeg
        final_vf = f"{user_filter},scale=1080:1920,fps=30"
        
        print(f"✂️ Cutting Segment {i}: {seg['start']} to {seg['end']}")
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", final_vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ FFmpeg Error on segment {i}: {result.stderr}")
            continue

        if os.path.exists(temp_seg) and os.path.getsize(temp_seg) > 0:
            try:
                dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg]
                dur = subprocess.check_output(dur_cmd).decode().strip()
                durations.append(float(dur))
                segment_files.append(temp_seg)
            except:
                print(f"⚠️ Warning: Could not read duration for {temp_seg}")

    # 2. Stitch Segments
    if not segment_files: 
        print(f"❌ Task {task_idx} failed: No valid segments were produced.")
        continue
        
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # 3. Caption Style: Full Width Horizontal White Bar + Persistent Black Text
    cap_filters = []
    source_caps = job.get('captions', [])
    total_duration = sum(durations)
    
    for j, c in enumerate(source_caps):
        txt = c['text'].replace("'", "").upper().strip()
        start = float(c['start'])
        # Persistent logic: Stay until the next caption starts or video ends
        end = float(source_caps[j+1]['start']) if j+1 < len(source_caps) else total_duration
        
        # Position: y=ih-450 (Bottom third)
        # Bar: Full width (iw), 130 pixels high
        draw_bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=130:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:x=(w-text_w)/2:y=h-415:enable='between(t,{start},{end})'"
        cap_filters.extend([draw_bar, draw_txt])

    # 4. Final Export with Captions
    final_output = f"output/{job['new_title']}"
    if cap_filters:
        subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    else:
        os.rename(combined, final_output)
    
    # 5. Safe Cleanup
    for s in segment_files: 
        if os.path.exists(s): os.remove(s)
    if os.path.exists(list_file): os.remove(list_file)
    if os.path.exists(combined) and os.path.exists(final_output): os.remove(combined)
    if os.path.exists(input_path): os.remove(input_path) # Fre
