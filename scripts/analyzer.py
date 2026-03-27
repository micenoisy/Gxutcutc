import whisper, subprocess, os, json

os.makedirs("reports", exist_ok=True)
model = whisper.load_model("base")

def get_video_info(path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json {path}"
    output = subprocess.check_output(cmd, shell=True).decode()
    return json.loads(output)['streams'][0]

print("🎙️ Starting Deep Analysis...")
# We analyze 'input/raw.mp4' which was downloaded first
video_path = "input/raw.mp4"
info = get_video_info(video_path)
result = model.transcribe(video_path)

report_path = "reports/analysis_summary.txt"
with open(report_path, "w") as f:
    f.write(f"--- VIDEO VISUAL SPECS ---\n")
    f.write(f"Resolution: {info['width']}x{info['height']}\n")
    layout = "STREAMER_STACK_REQUIRED" if info['width'] > info['height'] else "STANDARD_VERTICAL"
    f.write(f"Suggested Layout: {layout}\n\n")
    
    f.write(f"--- MICROSECOND TRANSCRIPT ---\n")
    for s in result['segments']:
        f.write(f"[{s['start']:.3f} -> {s['end']:.3f}] {s['text'].strip()}\n")

print(f"✅ Analysis Ready at {report_path}")
