import whisper, subprocess, os, json

def get_pro_metadata(path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate,bit_rate -of json \"{path}\""
    return json.loads(subprocess.check_output(cmd, shell=True).decode())['streams'][0]

print("🧠 Starting Titan Analysis...")
model = whisper.load_model("medium") # Upgraded to Medium for better accuracy

files = [f for f in os.listdir("input") if f.lower().endswith(('.mp4', '.mkv', '.mov'))]
report_path = "reports/titan_analysis_report.txt"

with open(report_path, "w") as r:
    for f_name in files:
        path = os.path.join("input", f_name)
        meta = get_pro_metadata(path)
        
        print(f"🎙️ Deep Transcribing: {f_name}")
        # Task='transcribe' with word_timestamps for micro-precision
        result = model.transcribe(path, word_timestamps=True)
        
        r.write(f"VIDEO_ID: {f_name}\n")
        r.write(f"PRO_SPECS: {meta['width']}x{meta['height']} @ {meta['avg_frame_rate']}fps\n")
        r.write("--- SURGICAL TIMELINE (MICROSECONDS) ---\n")
        
        for s in result['segments']:
            # Calculate 'Energy Score' based on average probability
            energy = "HIGH" if s['avg_logprob'] > -0.5 else "LOW"
            r.write(f"[{s['start']:.4f} -> {s['end']:.4f}] [ENERGY: {energy}] {s['text'].strip()}\n")
            
            # Silence Detection: If gap between segments > 1.5s, mark it as a cut point
            # (Logic handled by LLM AI in next step)
        r.write("\n" + "="*70 + "\n\n")

print(f"✅ Titan Report Generated: {report_path}")
