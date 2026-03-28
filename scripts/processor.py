import json, subprocess, os

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

with open('master_config.json') as f:
    jobs = json.load(f)

# Global Cleanup List
raw_videos = []

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    # REUSE LOGIC: Find existing file or fail
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov'))]
    input_path = os.path.join("input", input_files[0]) # Simplest reuse
    raw_videos.append(input_path)

    print(f"🎬 Task {task_idx}: Processing {job['new_title']}")
    
    # Custom Styling from JSON
    res = job.get('target_resolution', "1080:1920")
    f_color = job.get('font_color', "black")
    b_color = job.get('bg_color', "white")
    y_pos = job.get('caption_y_pos', "ih-450")
    
    segment_files = []
    durations = []
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_seg{i}.mp4"
        vf = f"{job.get('frame_filter', 'scale=1080:1920')},fps=30"
        
        subprocess.run(["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg])
        
        if os.path.exists(temp_seg):
            dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg]).decode().strip()
            durations.append(float(dur))
            segment_files.append(temp_seg)

    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f: [f.write(f"file '{s}'\n") for s in segment_files]
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # CAPTION ENGINE: PERSISTENT WHITE BAR + CUSTOM COLORS
    cap_filters = []
    source_caps = job.get('captions', [])
    for j, c in enumerate(source_caps):
        txt = c['text'].replace("'", "").upper()
        start = float(c['start'])
        # Persistence: stays until next caption
        end = float(source_caps[j+1]['start']) if j+1 < len(source_caps) else sum(durations)
        
        draw_bar = f"drawbox=y={y_pos}:color={b_color}@1:width=iw:height=140:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor={f_color}:fontsize=55:x=(w-text_w)/2:y={y_pos}+35:enable='between(t,{start},{end})'"
        cap_filters.extend([draw_bar, draw_txt])

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    
    # Task Cleanup
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)

# Final raw video cleanup
for f in set(raw_videos):
    if os.path.exists(f): os.remove(f)

print("🚀 ALL TASKS COMPLETED #viralitypoly")
