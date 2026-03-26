import json, subprocess, os

# Load instructions
with open('master_config.json') as f:
    jobs = json.load(f)

os.makedirs("output", exist_ok=True)

for job in jobs:
    input_path = f"input/{job['original_file']}"
    final_output = f"output/{job['new_title']}"
    
    # 1. Create Segments (Hook, Body, End) and Crop them
    segment_files = []
    for i, seg in enumerate(job['segments']):
        temp_seg = f"temp_{i}_{job['original_file']}"
        # Reframing: crop=width:height:x:y
        crop = job['frame_config'] 
        
        cmd = [
            "ffmpeg", "-y", "-ss", seg['start'], "-to", seg['end'], 
            "-i", input_path, "-vf", f"{crop},fps=30", 
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", temp_seg
        ]
        subprocess.run(cmd)
        segment_files.append(temp_seg)

    # 2. Join Segments (Hook first, then rest)
    with open("list.txt", "w") as f:
        for s in segment_files: f.write(f"file '{s}'\n")
    
    combined = "combined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", combined])

    # 3. Add Hardcoded Captions
    cap_filters = []
    for cap in job['captions']:
        # Simple caption: white text, centered, bottom
        text = cap['text'].replace("'", "")
        f = f"drawtext=text='{text}':enable='between(t,{cap['start']},{cap['end']})':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h-150"
        cap_filters.append(f)
    
    filter_str = ",".join(cap_filters)
    
    # Final export
    subprocess.run([
        "ffmpeg", "-y", "-i", combined, "-vf", filter_str, "-c:a", "copy", final_output
    ])

    # Cleanup temp files
    for s in segment_files: os.remove(s)
    if os.path.exists("list.txt"): os.remove("list.txt")
    if os.path.exists("combined.mp4"): os.remove("combined.mp4")

print("All videos processed successfully!")
