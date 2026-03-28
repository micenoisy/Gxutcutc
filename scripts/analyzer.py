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

# 2. Get list of actual video files downloaded in input folder
downloaded_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
downloaded_files.sort() # Ensure consistent order

print(f"🚀 Starting Smart Analysis for {len(downloaded_files)} videos...")
model = whisper.load_model("base")

report_path = "reports/master_analysis.txt"

with open(report_path, "w") as master_file:
    master_file.write("=== BATCH VIDEO ANALYSIS REPORT ===\n\n")

# Match the downloaded files to the URLs in your JSON by order
for index, filename in enumerate(downloaded_files):
    input_path = os.path.join("input", filename)
    
    # Get the URL from the JSON based on index (File 1 = Link 1)
    # If there are more files than links, it uses 'N/A'
    url = jobs[index]['url'] if index < len(jobs) else "URL NOT PROVIDED"

    print(f"🎬 Analyzing [{index+1}/{len(downloaded_files)}]: {filename}")
    
    info = get_video_info(input_path)
    result = model.transcribe(input_path)

    # Append to the master report
    with open(report_path, "a") as master_file:
        master_file.write(f"VIDEO_ID: {index + 1}\n")
        master_file.write(f"FILENAME_IN_INPUT: {filename}\n")
        master_file.write(f"GDRIVE_LINK: {url}\n") 
        master_file.write(f"RESOLUTION: {info['width']}x{info['height']}\n")
        master_file.write("--- TRANSCRIPT ---\n")
        for s in result['segments']:
            # microsecond precision for other AI to understand
            master_file.write(f"[{s['start']:.3f} -> {s['end']:.3f}] {s['text'].strip()}\n")
        master_file.write("\n" + "="*60 + "\n\n")

print(f"✅ Full report generated at {report_path}")
