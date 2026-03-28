import json, subprocess, os

os.makedirs("output", exist_ok=True)

with open('master_config.json') as f:
    jobs = json.load(f)

for job in jobs:
    if "__AI_GUIDE__" in job: continue
    
    # Smart File Matching
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov'))]
    input_path = None
    for f in input_files:
        if f.lower() in job['original_file'].lower() or job['original_file'].lower() in f.lower():
            input_path = os.path.join("input", f)
            break

    if not input_path: continue
    print(f"🎬 Titan Producing: {job['new_title']}")

    segment_files = []
    durations = []
    
    # ADVANCED: Layout Logic from JSON
    vf_base = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        out_seg = f"titan_t{i}.mp4"
        # Standardize everything to 1080x1920 30fps for Social Media
        full_vf = f"{vf_base},scale=1080:1920,fps=30"
        
        cmd = ["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", full_vf, "-c:v", "libx264", "-crf", "17", "-preset", "slow", out_seg]
        subprocess.run(cmd)
        
        if os.path.exists(out_seg):
            dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", out_seg]).decode().strip()
            durations.append(float(dur))
            segment_files.append(out_seg)

    if not segment_files: continue
    
    # Join Segments
    list_f = "join.txt"
    with open(list_f, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_f, "-c", "copy", combined])

    # KINETIC CAPTIONS: Black on White with Dynamic Persistence
    cap_filters = []
    caps = job.get('captions', [])
    for idx, c in enumerate(caps):
        txt = c['text'].replace("'", "").upper().strip()
        start = float(c['start'])
        # Persistence: Auto-extend until next caption or end of video
        end = float(caps[idx+1]['start']) if idx+1 < len(caps) else sum(durations)
        
        # UI/UX: Professional lower-third bar
        draw_bar = f"drawbox=y=ih-480:color=white@1:width=iw:height=150:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=60:font='Verdana-Bold':x=(w-text_w)/2:y=h-435:enable='between(t,{start},{end})'"
        cap_filters.extend([draw_bar, draw_txt])

    final_out = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "aac", "-b:a", "192k", final_out])
    
    # Cleanup
    for s in segment_files: os.remove(s)
    os.remove(list_f); os.remove(combined)

print("🚀 TITAN AGENT: BATCH COMPLETE #viralitypoly")
