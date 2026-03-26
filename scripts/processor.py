import json, subprocess, os, whisper

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    # Standardize name: remove spaces and lowercase for comparison
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

print("🚀 Loading Whisper AI...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for job in jobs:
    # Use the search function to find the file even with spaces/caps
    input_path = find_file_case_insensitive("input/", job['original_file'])
    
    if not input_path:
        print(f"❌ File Not Found: {job['original_file']}")
        continue

    print(f"🎬 Processing: {input_path}")
    
    # 1. Transcribe
    try:
        result = model.transcribe(input_path)
    except Exception as e:
        print(f"❌ Whisper Error: {e}. Check if file is corrupted.")
        continue
    
    # 2. Extract Segments with 9:16 Crop
    segment_files = []
    durations = []
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"seg_{i}.mp4"
        crop = job['frame_config']
        
        # Wrapped input_path in quotes internally via subprocess list
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", f"{crop},fps=30",
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        subprocess.run(cmd)
        
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 3. Join Segments
    if not segment_files: continue
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    # 4. Timeline Caption Logic
    cap_filters = []
    current_offset = 0.0
    for i, seg in enumerate(job['segments']):
        seg_start = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['start'].split(':'))))
        seg_end = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['end'].split(':'))))
        
        for s in result['segments']:
            if s['start'] >= seg_start and s['end'] <= seg_end:
                new_start = s['start'] - seg_start + current_offset
                new_end = s['end'] - seg_start + current_offset
                text = s['text'].replace("'", "").strip().upper()
                # Clean style: Yellow bold text with small shadow
                f = f"drawtext=text='{text}':enable='between(t,{new_start},{new_end})':fontcolor=yellow:fontsize=42:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black"
                cap_filters.append(f)
        current_offset += durations[i]

    # 5. Export Final Video
    final_output = f"output/{job['new_title']}"
    # Join first 80 filters (prevents command line length errors)
    filter_str = ",".join(cap_filters[:80])
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", filter_str, "-c:a", "copy", final_output])

    # 6. Clean up
    for s in segment_files: os.remove(s)
    if os.path.exists("list.txt"): os.remove("list.txt")
    if os.path.exists("combined.mp4"): os.remove("combined.mp4")

print("✅ Agent finished processing batch.")
