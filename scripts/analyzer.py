import whisper, os, json, subprocess

def get_video_info(path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json \"{path}\""
    output = subprocess.check_output(cmd, shell=True).decode()
    return json.loads(output)['streams'][0]

os.makedirs("reports", exist_ok=True)
model = whisper.load_model("base")

with open('analyze_config.json') as f:
    jobs = json.load(f)

report_path = "reports/precision_report.txt"
with open(report_path, "w") as f: f.write("=== SURGICAL WORD ANALYSIS ===\n")

for job in jobs:
    # Auto-detect file in input/
    input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov'))]
    target_file = None
    for f in input_files:
        if f.lower() in job['url'].lower() or len(input_files) == 1:
            target_file = os.path.join("input", f)
            break
    
    if not target_file: continue

    print(f"🎙️ Extracting Microseconds: {target_file}")
    info = get_video_info(target_file)
    # word_timestamps=True is the key for surgical editing
    result = model.transcribe(target_file, word_timestamps=True)

    with open(report_path, "a") as f:
        f.write(f"\nVIDEO: {target_file}\nLINK: {job['url']}\nRES: {info['width']}x{info['height']}\n")
        for segment in result['segments']:
            f.write(f"\n--- Segment [Energy: {segment['avg_logprob']:.2f}] ---\n")
            for word in segment['words']:
                # WORD | START | END (Microsecond Precision)
                f.write(f"{word['word'].strip().upper():<15} | {word['start']:>8.3f}s | {word['end']:>8.3f}s\n")
        f.write("\n" + "="*50 + "\n")

print("✅ Analysis Complete.")
