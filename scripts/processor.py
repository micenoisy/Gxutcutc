import json, subprocess, os

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

if not os.path.exists('master_config.json'):
    print("❌ master_config.json not found!")
    exit(1)

with open('master_config.json') as f:
    jobs = json.load(f)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job or "__AI_DOCUMENTATION__" in job: continue
    
    # Matching video logic
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
    if len(input_files) <= task_idx:
        print(f"⚠️ Task {task_idx}: No video file available for this index.")
        continue
    
    input_path = os.path.join("input", input_files[task_idx])
    print(f"🎬 Task {task_idx}: Using {input_path}")

    segment_files = []
    durations = []
    
    raw_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"t{task_idx}_s{i}.mp4"
        final_vf = f"{raw_filter},fps=30"
        
        print(f"✂️ Cutting {temp_seg}: {seg['start']} to {seg['end']}")
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", final_vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        
        subprocess.run(cmd)
        
        # FIXED: Robust check for valid file
        if os.path.exists(temp_seg) and os.path.getsize(temp_seg) > 500:
            try:
                dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg]
                dur_raw = subprocess.check_output(dur_cmd).decode().strip()
                
                # Check if result is a valid number
                if dur_raw != "N/A" and dur_raw != "":
                    durations.append(float(dur_raw))
                    segment_files.append(temp_seg)
                else:
                    print(f"⚠️ Warning: Segment {temp_seg} has invalid duration. Skipping.")
            except Exception as e:
                print(f"⚠️ Warning: Failed to probe {temp_seg}. Error: {e}")
        else:
            print(f"❌ Error: Segment {temp_seg} failed to encode or is empty.")

    if not segment_files: continue
        
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # PRO CAPTIONS: White bar style
    cap_filters = []
    source_caps = job.get('captions', [])
    for j, c in enumerate(source_caps):
        txt = c['text'].replace("'", "").upper().strip()
        start, end = float(c['start']), float(c['end'])
        
        draw_bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=140:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:x=(w-text_w)/2:y=h-410:enable='between(t,{start},{end})'"
        cap_filters.extend([draw_bar, draw_txt])

    final_output = f"output/{job['new_title']}"
    if cap_filters:
        subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    else:
        os.rename(combined, final_output)
    
    # Cleanup
    for s in segment_files: os.remove(s)
    if os.path.exists(list_file): os.remove(list_file)
    if os.path.exists(combined) and os.path.exists(final_output): os.remove(combined)

print("🚀 ALL TASKS FINISHED #viralitypoly")
