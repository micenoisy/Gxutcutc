import json, subprocess, os, whisper

def find_file_case_insensitive(directory, filename):
    if not os.path.exists(directory): return None
    for f in os.listdir(directory):
        if f.lower() == filename.lower():
            return os.path.join(directory, f)
    return None

# Load Whisper
print("🚀 Loading Whisper AI...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for job in jobs:
    input_path = find_file_case_insensitive("input/", job['original_file'])
    if not input_path:
        print(f"❌ Missing: {job['original_file']}"); continue

    print(f"🎬 Processing: {input_path}")
    
    # 1. Transcribe the WHOLE video once
    result = model.transcribe(input_path)
    
    # 2. Extract Segments (Hook, Body, etc.) with 9:16 Crop
    segment_files = []
    durations = []
    
    for i, seg in enumerate(job['segments']):
        temp_seg = f"seg_{i}.mp4"
        crop = job['frame_config']
        
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'],
            "-i", input_path, "-vf", f"{crop},fps=30",
            "-c:v", "libx264", "-crf", "18", temp_seg
        ]
        subprocess.run(cmd)
        
        # Get duration of this segment for caption shifting
        prob = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", temp_seg])
        durations.append(float(prob))
        segment_files.append(temp_seg)

    # 3. Join Segments (Hook first)
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    # 4. Map Captions to the NEW timeline
    cap_filters = []
    current_offset = 0.0
    
    for i, seg in enumerate(job['segments']):
        seg_start = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['start'].split(':'))))
        seg_end = float(sum(float(x) * 60**(1-j) for j, x in enumerate(seg['end'].split(':'))))
        
        for s in result['segments']:
            # If the original caption falls within this segment's original time
            if s['start'] >= seg_start and s['end'] <= seg_end:
                new_start = s['start'] - seg_start + current_offset
                new_end = s['end'] - seg_start + current_offset
                text = s['text'].replace("'", "").strip().upper()
                
                f = f"drawtext=text='{text}':enable='between(t,{new_start},{new_end})':fontcolor=yellow:fontsize=45:x=(w-text_w)/2:y=h-180:box=1:boxcolor=black@0.4"
                cap_filters.append(f)
        
        current_offset += durations[i]

    # 5. Final Export
    final_output = f"output/{job['new_title']}"
    filter_str = ",".join(cap_filters[:70])
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", filter_str, "-c:a", "copy", final_output])

    # 6. Cleanup
    for s in segment_files: os.remove(s)
    os.remove("list.txt"); os.remove("combined.mp4")

print("✅ Success! #viralitypoly")
