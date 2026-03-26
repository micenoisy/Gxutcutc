import json, subprocess, os, whisper

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    target = filename.lower().strip()
    for f in os.listdir(directory):
        if f.lower().strip() == target:
            return os.path.join(directory, f)
    return None

def is_lfs_pointer(path):
    # Check if the file is just a small text file (Git LFS pointer)
    if os.path.getsize(path) < 500:
        with open(path, 'r') as f:
            content = f.read()
            if "version https://git-lfs.github.com" in content:
                return True
    return False

print("🚀 Loading Whisper AI...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for job in jobs:
    input_path = find_file_case_insensitive("input/", job['original_file'])
    
    if not input_path:
        print(f"❌ File Not Found: {job['original_file']}")
        continue

    if is_lfs_pointer(input_path):
        print(f"❌ ERROR: {input_path} is an LFS Pointer, not a real video.")
        print("FIX: Ensure you uploaded the video fully to GitHub.")
        continue

    print(f"🎬 Processing: {input_path}")
    
    # 1. Transcribe
    result = model.transcribe(input_path)
    
    # 2. Extract Segments and Crop
    segment_files = []
    durations = []
    for i, seg in enumerate(job['segments']):
        temp_seg = f"seg_{i}.mp4"
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", f"{job['frame_config']},fps=30",
            "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", temp_seg
        ]
        subprocess.run(cmd)
        if os.path.exists(temp_seg):
            prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
            durations.append(float(prob))
            segment_files.append(temp_seg)

    # 3. Join and Caption (Timeline Adjusted)
    if not segment_files: continue
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

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
                cap_filters.append(f"drawtext=text='{text}':enable='between(t,{new_start},{new_end})':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-160:borderw=2:bordercolor=black")
        current_offset += durations[i]

    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", ",".join(cap_filters[:80]), "-c:a", "copy", final_output])

    # Cleanup
    for s in segment_files: os.remove(s)
    if os.path.exists("list.txt"): os.remove("list.txt")
    if os.path.exists("combined.mp4"): os.remove("combined.mp4")

print("✅ Success! #viralitypoly")
