import json, subprocess, os, whisper, gdown, yt_dlp

# --- NEW: DOWNLOAD HANDLER ---
def smart_download(url, target_filename):
    """Detects source and downloads video to input folder."""
    os.makedirs("input", exist_ok=True)
    output_path = os.path.join("input", target_filename)
    
    # Overwrite check: remove old file if it exists to avoid conflicts
    if os.path.exists(output_path):
        os.remove(output_path)

    print(f"📡 Attempting download from: {url}")
    
    try:
        if "youtube.com" in url or "youtu.be" in url:
            # YouTube Download Logic
            ydl_opts = {
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print(f"✅ YouTube download successful: {output_path}")
            
        elif "drive.google.com" in url:
            # Google Drive Download Logic
            gdown.download(url, output=output_path, quiet=False, fuzzy=True)
            print(f"✅ Google Drive download successful: {output_path}")
            
        else:
            print("❌ ERROR: Unsupported URL source. Use YouTube or GDrive.")
            return None
            
        return output_path

    except Exception as e:
        print(f"❌ DOWNLOAD FAILED for {url}: {e}")
        return None

# --- EXISTING: FILE SEARCH ---
def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

# --- MAIN ENGINE ---
print("🚀 Initializing AI Video Agent...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for task_index, job in enumerate(jobs):
    target_name = job.get('original_file', f"video_{task_index}.mp4")
    video_url = job.get('video_url', None)
    
    print(f"\n--- 🛠️ TASK {task_index + 1}: {target_name} ---")

    # LOGIC: Download if URL exists, else look locally
    if video_url:
        input_path = smart_download(video_url, target_name)
    else:
        input_path = find_file_case_insensitive("input/", target_name)

    if not input_path or not os.path.exists(input_path):
        print(f"❌ SKIPPING: Could not find or download {target_name}. Check your link/folder.")
        continue

    # --- YOUR EXISTING CLIPPING/WHISPER LOGIC STARTS HERE ---
    print(f"🎙️ Transcribing {target_name}...")
    result = model.transcribe(input_path)
    
    segment_files = []
    durations = []
    frame_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_index}_seg{i}.mp4"
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", f"{frame_filter},fps=30,scale=1080:1920",
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        subprocess.run(cmd)
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    if not segment_files: continue
    list_file = f"list_task{task_index}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_task{task_index}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    cap_filters = []
    current_offset = 0.0
    source_caps = job.get('captions', [])
    
    # Timeline Adjustment for Captions
    for i, seg in enumerate(job['segments']):
        seg_start = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['start'].split(':'))))
        seg_end = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['end'].split(':'))))
        
        # Priority: Manual Captions if present, else Whisper
        if source_caps:
            # Note: This uses your manual logic if you provided it
            for c in source_caps:
                txt = c['text'].replace("'", "").strip().upper()
                cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=48:x=(w-text_w)/2:y=h-250:borderw=3:bordercolor=black")
        else:
            for s in result['segments']:
                if s['start'] >= seg_start and s['end'] <= seg_end:
                    new_start = s['start'] - seg_start + current_offset
                    new_end = s['end'] - seg_start + current_offset
                    txt = s['text'].replace("'", "").strip().upper()
                    cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{new_start},{new_end})':fontcolor=yellow:fontsize=48:x=(w-text_w)/2:y=h-250:borderw=3:bordercolor=black")
        
        current_offset += durations[i]

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:80]), "-c:a", "copy", final_output])

    # Cleanup task files
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)
    print(f"✅ SUCCESS: {job['new_title']} produced.")

print("\n🚀 ALL TASKS COMPLETED #viralitypoly")
