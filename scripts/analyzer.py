import whisper, json, os

model = whisper.load_model("base")
os.makedirs("reports", exist_ok=True)

with open('analyze_config.json') as f:
    links = json.load(f)

for idx, link in enumerate(links):
    # Download logic
    path = f"input/raw_{idx}.mp4"
    print(f"📡 Analyzing Link: {link['url']}")
    # gdown download here... (truncated for brevity)
    
    # Word-level transcription
    result = model.transcribe(path, word_timestamps=True)
    
    report_path = f"reports/analysis_{idx}.txt"
    with open(report_path, "w") as f:
        f.write(f"--- MICRO-TIMESTAMP REPORT ---\n")
        for seg in result['segments']:
            f.write(f"\n[SEGMENT {seg['start']:.2f} -> {seg['end']:.2f}]\n")
            for word in seg['words']:
                f.write(f"{word['start']:.3f}|{word['end']:.3f}|{word['word']}\n")
    print(f"✅ Micro-Report Saved: {report_path}")
