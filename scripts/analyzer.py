import whisper, subprocess, os, json

def get_video_info(path):
    try:
        cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json \"{path}\""
        output = subprocess.check_output(cmd, shell=True).decode()
        return json.loads(output)['streams'][0]
    except:
        return {"width": "unknown", "height": "unknown"}

os.makedirs("reports", exist_ok=True)

# 1. Load the original config to get the URLs
with open('analyze_config.json') as f:
    jobs = json.load(f)

print(f"🚀 Starting Batch Analysis for {len(jobs)} videos...")
model = whisper.load_model("base")

report_path = "reports/master_analysis.txt"

# Clear old report
with open(report_path, "w") as master_file:
    master_file.write("=== BATCH VIDEO ANALYSIS REPORT ===\n\n")

for job in jobs:
    target_name = job['original_file']
    url = job['url']
    
    # Find the file in input/ (case-insensitive)
    input_path = None
    for f in os.listdir("input"):
        if f.lower() == target_name.lower():
            input_path = os.path.join("input", f)
            break
    
    if not input_path:
        print(f"⚠️ Could not find downloaded file for: {target_name}")
        continue

    print(f"🎬 Analyzing: {target_name}")
    info = get_video_info(input_path)
    result = model.transcribe(input_path)

    # Append to the single master report
    with open(report_path, "a") as master_file:
        master_file.write(f"VIDEO_NAME: {target_name}\n")
        master_file.write(f"GDRIVE_LINK: {url}\n") # FIXED: Added the link here
        master_file.write(f"RESOLUTION: {info['width']}x{info['height']}\n")
        master_file.write("--- TRANSCRIPT ---\n")
        for s in result['segments']:
            master_file.write(f"[{s['start']:.3f} -> {s['end']:.3f}] {s['text'].strip()}\n")
        master_file.write("\n" + "="*50 + "\n\n")

print(f"✅ All transcripts saved to {report_path}")
