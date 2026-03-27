import json, subprocess, os, whisper, gdown, re

# Function to clean Google Drive links to ensure they download the raw file
def get_clean_gdrive_id(url):
    if not url: return None
    match = re.search(r'[-\w]{25,}', url)
    return match.group() if match else None

def download_from_gdrive(url, target_name):
    print(f"📡 Downloading from Google Drive: {target_name}...")
    os.makedirs("input", exist_ok=True)
    output_path = f"input/{target_name}"
    
    # Clean up old corrupted attempts
    if os.path.exists(output_path): os.remove(output_path)
    
    file_id = get_clean_gdrive_id(url)
    if not file_id:
        print(f"❌ ERROR: Invalid Google Drive link for {target_name}")
        return None

    try:
        # Use gdown to bypass Google's "large file" warning page
        gdown.download(f'https://drive.google.com/uc?id={file_id}', output=output_path, quiet=False)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
            print(f"✅ GDrive Download Success: {output_path}")
            return output_path
        else:
            print(f"❌ ERROR: Downloaded file for {target_name} is corrupted or empty.")
            return None
    except Exception as e:
        print(f"❌ GDrive Error: {e}")
        return None

print("🚀 Starting AI Multi-Task Agent (Stable GDrive Mode)...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for task_idx, job in enumerate(jobs):
    if "__AI_GUIDE__" in job: continue
    
    target_name = job.get('original_file', f"task_{task_idx}.mp4")
    gdrive_url = job.get('gdrive_url', job.get('video_url', None))

    # LOGIC: 1. Check local folder FIRST | 2. Download from GDrive SECOND
    input_path = os.path.join("input", target_name)
    if not os.path.exists(input_path):
        if gdrive_url:
            input_path = download_from_gdrive(gdrive_url, target_name)
        else:
            print(f"❌ Skipping {target_name}: No local file and no GDrive link."); continue

    if not input_path or not os.path.exists(input_path):
        print(f"❌ Skipping {target_name}: File unavailable."); continue

    # 3. Transcribe (Cached Whisper base)
    print(f"🎙️ Transcribing {target_name}...")
    result = model.transcribe(input_path)
    
    # 4. Multi-Segment Trimming & Reframing
    segment_files = []
    durations = []
    raw_filter = job.get('frame_filter', "crop=w=ih*9/16:h=ih:x=(iw-ow)/2")
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"task{task_idx}_seg{i}.mp4"
        # Pro Framing: Apply JSON setting + Force Social Media Size (1080x1920)
        vf = f"{raw_filter},fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        print(f"✂️ Cutting segment {i}...")
        subprocess.run(["ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], "-i", input_path, "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg])
        
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 5. Stitching and Burning Captions
    if not segment_files: continue
    list_file = f"list_{task_idx}.txt"
    with open(list_file, "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = f"combined_task{task_idx}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", combined])

    cap_filters = []
    for c in job.get('captions', []):
        txt = c['text'].replace("'", "").strip().upper()
        cap_filters.append(f"drawtext=text='{txt}':enable='between(t,{c['start']},{c['end']})':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=h-300:borderw=3:bordercolor=black")

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:75]), "-c:a", "copy", final_output])

    # Cleanup Task Files
    for s in segment_files: os.remove(s)
    os.remove(list_file); os.remove(combined)
    print(f"✅ PRODUCTION FINISHED: {job['new_title']} #viralitypoly")

print("\n🚀 ALL JOBS COMPLETED SUCCESSFULLY!")
