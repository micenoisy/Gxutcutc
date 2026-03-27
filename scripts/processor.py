import json, subprocess, os, gdown

def download_video(url, name):
    dest = f"input/{name}"
    if os.path.exists(dest): os.remove(dest)
    gdown.download(url, output=dest, quiet=False, fuzzy=True)
    return dest

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)
os.makedirs("input", exist_ok=True)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    # 1. DOWNLOAD FIRST
    input_path = download_video(job['gdrive_url'], job['original_file'])
    
    # 2. SEGMENTING & REFRAMING
    segment_files = []
    durations = []
    frame_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"t{task_idx}_s{i}.mp4"
        # Force 9:16 Vertical
        vf = f"{frame_filter},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        cmd = ["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg]
        subprocess.run(cmd)
        
        if os.path.exists(temp_seg):
            dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(dur))
            segment_files.append(temp_seg)

    # 3. STITCH
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    combined = f"combined_{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    # 4. CAPTION STYLE: FULL WIDTH WHITE BAR + BLACK TEXT
    cap_filters = []
    source_caps = job.get('captions', [])
    for j, c in enumerate(source_caps):
        txt = c['text'].replace("'", "").strip().upper()
        start, end = c['start'], c['end']
        
        # persistence: draw bar and text
        draw_bar = f"drawbox=y=ih-450:color=white@1:width=iw:height=130:t=fill:enable='between(t,{start},{end})'"
        draw_txt = f"drawtext=text='{txt}':fontcolor=black:fontsize=55:x=(w-text_w)/2:y=h-415:enable='between(t,{start},{end})'"
        cap_filters.append(draw_bar)
        cap_filters.append(draw_txt)

    # 5. FINAL EXPORT
    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters), "-c:a", "copy", final_output])
    
    # Cleanup to save disk
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)
    print(f"✅ Task {task_idx} Done: {final_output}")
