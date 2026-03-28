import whisper, os, json, subprocess

def get_video_info(path):
    try:
        cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json \"{path}\""
        output = subprocess.check_output(cmd, shell=True).decode()
        return json.loads(output)['streams'][0]
    except:
        return {"width": "unknown", "height": "unknown"}

os.makedirs("reports", exist_ok=True)

# 1. Load the original config
if os.path.exists('analyze_config.json'):
    with open('analyze_config.json') as f:
        jobs = json.load(f)
else:
    jobs = []

# 2. Get actual video files in input folder
input_files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
input_files.sort() # Ensure consistent order

print(f"🚀 Found {len(input_files)} files. Starting Transcription...")
model = whisper.load_model("base")

report_path = "reports/precision_report.txt"
with open(report_path, "w") as f:
    f.write("=== SURGICAL WORD ANALYSIS REPORT ===\n\n")

for index, filename in enumerate(input_files):
    input_path = os.path.join("input", index_file := filename)
    url = jobs[index]['url'] if index < len(jobs) else "N/A"

    print(f"🎙️ Transcribing [{index+1}/{len(input_files)}]: {filename}")
    
    # Analyze visual specs
    info = get_video_info(input_path)
    
    # Perform microsecond word-level transcription
    result = model.transcribe(input_path, word_timestamps=True)

    with open(report_path, "a") as f:
        f.write(f"VIDEO_ID: {index + 1}\n")
        f.write(f"FILENAME: {filename}\n")
        f.write(f"GDRIVE_LINK: {url}\n")
        f.write(f"RESOLUTION: {info.get('width')}x{info.get('height')}\n")
        f.write("-" * 30 + "\n")
        
        for segment in result['segments']:
            # Log the energy level for the AI to find hooks
            f.write(f"\n[Segment Energy: {segment['avg_logprob']:.2f}]\n")
            for word in segment.get('words', []):
                # WORD | START | END (Microsecond Precision)
                f.write(f"{word['word'].strip().upper():<15} | {word['start']:>8.3f}s | {word['end']:>8.3f}s\n")
        
        f.write("\n" + "="*60 + "\n\n")

print(f"✅ Full report generated at {report_path}")
