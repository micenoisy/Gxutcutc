import json, subprocess, os

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

with open('master_config.json') as f:
    jobs = json.load(f)

files_to_cleanup = []

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job or "__AI_DOCUMENTATION__" in job: continue
    
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
    if not input_files: continue
    
    input_path = os.path.join("input", input_files[0])
    files_to_cleanup.append(input_path)
    print(f"🎬 Processing Task {task_idx}: {job['new_title']}")

    segment_files = []
    durations = []
    user_filter = job.get('frame_filter', "scale=1080:1920")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_seg{i}.mp4"
        final_vf = f"{user_filter},scale=1080:1920,fps=30"
        
        cmd = ["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", final_vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg]
        subprocess.run(cmd)
        
        if os.path.exists(temp_seg) and os.path.getsize(temp_seg) > 500:
            try:
                dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg]
                dur = subprocess.check_output(dur_cmd).decode().strip()
                durations.append(float(dur))
                segment_files.append(temp_seg)
            except: pass

    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f: [f.write(f"file '{s}'\n") for s in segment_files]
    
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # FIXED CAPTION ENGINE: Uses 'h' (compatible with drawtext and drawbox)
    cap_filters = []
    source_caps = job.get('captions', [])
    total_dur = sum(durations)
    y_pos_raw = job.get('caption_y_pos', "h-450").replace("ih", "h") # Safety fix

    for j, c in enumerate(source_caps):
        txt = c['text'].replace("'", "").upper().strip()
        start = float(c['start'])
        end = float(source_caps[j+1]['start']) if j+1 < len(source_caps) else total_dur
        
        # Using standardized 'h' instead of 'ih' to fix the 0-byte error
        draw_bar = f"drawbox=y={y_pos_raw}:color={job.get('bg_color', 'white')}@1:width=iw:height=140:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor={job.get('font_color', 'black')}:fontsize=55:x=(w-text_w)/2:y={y_pos_raw}+35:enable='between(t,{start},{end})'"
        cap_filters.extend([draw_bar, draw_txt])

    final_output = f"output/{job['new_title']}"
    if cap_filters:
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output]
        subprocess.run(ffmpeg_cmd)
    else:
        os.rename(combined, final_output)
    
    # 0-BYTE PROTECTION: If ffmpeg failed, delete the empty file so it's not pushed
    if os.path.exists(final_output) and os.path.getsize(final_output) < 1000:
        print(f"❌ Error: {final_output} generated empty. Removing.")
        os.remove(final_output)

    # Cleanup
    for s in segment_files: os.remove(s)
    if os.path.exists(list_file): os.remove(list_file)
    if os.path.exists(combined): os.remove(combined)

for f in set(files_to_cleanup):
    if os.path.exists(f): os.remove(f)

print("🚀 ALL TASKS FINISHED #viralitypoly")
