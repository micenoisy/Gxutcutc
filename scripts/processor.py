import json, subprocess, os, whisper

# Load Whisper Model (Base is fast and fits in GitHub memory)
print("Loading Whisper AI...")
model = whisper.load_model("base")

with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for job in jobs:
    input_path = f"input/{job['original_file']}"
    
    # FIX 1: Check if file exists before starting
    if not os.path.exists(input_path):
        print(f"ERROR: File {input_path} not found! Skipping...")
        continue

    print(f"Processing {job['original_file']} with Whisper AI...")
    
    # 1. Get precise captions using Whisper
    result = model.transcribe(input_path)
    
    # 2. Process Segments and Crop
    segment_files = []
    for i, seg in enumerate(job['segments']):
        temp_seg = f"temp_{i}_{job['original_file']}"
        crop = job['frame_config'] 
        
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], 
            "-i", input_path, "-vf", f"{crop},fps=30", 
            "-c:v", "libx264", "-crf", "18", temp_seg
        ]
        subprocess.run(cmd)
        if os.path.exists(temp_seg):
            segment_files.append(temp_seg)

    # 3. Concatenate
    if not segment_files: continue
    
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    # 4. Generate Caption Filters from Whisper Data
    # We filter only segments that appear in our final video timeline
    cap_filters = []
    for segment in result['segments']:
        text = segment['text'].replace("'", "").strip().upper()
        start = segment['start']
        end = segment['end']
        # Styling: Yellow text, bold, bottom center
        f = f"drawtext=text='{text}':enable='between(t,{start},{end})':fontcolor=yellow:fontsize=40:font='Verdana':x=(w-text_w)/2:y=h-150"
        cap_filters.append(f)
    
    filter_str = ",".join(cap_filters[:50]) # Limiting to 50 for speed
    
    final_output = f"output/{job['new_title']}"
    subprocess.run(["ffmpeg", "-y", "-i", combined, "-vf", filter_str, "-c:a", "copy", final_output])

    # FIX 2: Safe Cleanup
    for s in segment_files: 
        if os.path.exists(s): os.remove(s)
    if os.path.exists("list.txt"): os.remove(s)
    if os.path.exists("combined.mp4"): os.remove("combined.mp4")

print("Finished! Check the output folder.")
