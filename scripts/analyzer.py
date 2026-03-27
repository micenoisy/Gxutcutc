import whisper, subprocess, os, json, gdown

def get_video_info(path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json \"{path}\""
    output = subprocess.check_output(cmd, shell=True).decode()
    return json.loads(output)['streams'][0]

os.makedirs("reports", exist_ok=True)
os.makedirs("input", exist_ok=True)

# Load config
with open('analyze_config.json') as f:
    links = json.load(f)

for link in links:
    target_name = link['original_file']
    input_path = f"input/{target_name}"
    
    # 1. DOWNLOAD FIRST
    print(f"📡 Downloading: {target_name}")
    gdown.download(link['url'], output=input_path, quiet=False, fuzzy=True)

    # 2. ANALYZE (Resolution & Transcription)
    print("🎙️ Starting Deep Analysis...")
    model = whisper.load_model("base")
    info = get_video_info(input_path)
    result = model.transcribe(input_path)

    report_path = f"reports/{target_name}_analysis.txt"
    with open(report_path, "w") as f:
        f.write(f"VIDEO_NAME: {target_name}\n")
        f.write(f"RESOLUTION: {info['width']}x{info['height']}\n")
        layout = "STREAMER_STACK_REQUIRED" if info['width'] > info['height'] else "STANDARD_VERTICAL"
        f.write(f"SUGGESTED_LAYOUT: {layout}\n")
        f.write("-" * 30 + "\n")
        for s in result['segments']:
            f.write(f"[{s['start']:.3f} -> {s['end']:.3f}] {s['text'].strip()}\n")
    print(f"✅ Analysis Saved: {report_path}")
