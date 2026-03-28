import json, subprocess, os

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

with open('master_config.json') as f:
    jobs = json.load(f)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job or "__AI_DOCUMENTATION__" in job: continue
    
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
    if len(input_files) <= task_idx:
        print(f"❌ Task {task_idx}: No video file found.")
        continue
    
    # Matching video to task by index
    input_path = os.path.join("input", input_files[task_idx])
    print(f"🎬 Task {task_idx}: Using {input_path}")

    segment_files = []
    durations = []
    
    # DYNAMIC FILTERING: This takes the AI's complex math directly
    raw_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"t{task_idx}_s{i}.mp4"
        
        # We allow the AI's filter to do the work, then just ensure standard FPS
        final_vf = f"{raw_filter},fps=30"
        
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", final_vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        
        subprocess.run(cmd)
        
        if os.path.exists(temp_seg) and os.path.getsize(temp_seg) > 0:
            dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg]
            dur = subprocess.check_output(dur_cmd).decode().strip()
            durations.append(float(dur))
            segment_files.append(temp_seg)

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
        start = float(c['start'])
        end = float(c['end'])
        
        # Position fixed to bottom area
        draw_bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=140:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:x=(w-text_w)/2:y=h-410:enable='between(t,{start},{end})'"
        cap_filters.extend([draw_bar, draw_txt])

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    
    # Cleanup
    for s in segment_files: os.remove(s)
    if os.path.exists(list_file): os.remove(list_file)
    if os.path.exists(combined): os.remove(combined)

print("🚀 ALL TASKS FINISHED #viralitypoly")
