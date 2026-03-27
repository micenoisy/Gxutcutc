import whisper, subprocess, os, json

def get_video_info(path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json \"{path}\""
    output = subprocess.check_output(cmd, shell=True).decode()
    return json.loads(output)['streams'][0]

os.makedirs("reports", exist_ok=True)

# AUTO-DETECT: Find the video file in the input folder
input_files = [f for f in os.listdir("input") if f.endswith(('.mp4', '.mkv', '.mov'))]
if not input_files:
    print("❌ No video found in input folder!")
    exit(1)

input_path = os.path.join("input", input_files[0])
print(f"🎬 Analyzing: {input_path}")

# 1. ANALYZE
model = whisper.load_model("base")
info = get_video_info(input_path)
result = model.transcribe(input_path)

# 2. SAVE REPORT
report_path = f"reports/video_analysis.txt"
with open(report_path, "w") as f:
    f.write(f"FILE_DETECTED: {input_files[0]}\n")
    f.write(f"RESOLUTION: {info['width']}x{info['height']}\n")
    f.write("-" * 30 + "\n")
    for s in result['segments']:
        f.write(f"[{s['start']:.3f} -> {s['end']:.3f}] {s['text'].strip()}\n")

print(f"✅ Analysis complete for {input_files[0]}")
