"""
Video Renderer for Make.com Integration
========================================
Downloads video + audio, generates word-synced subtitles,
merges everything with FFmpeg, uploads result, and calls back.
"""

import sys
import os
import json
import subprocess
import requests
import re
import time


def download_file(url, output_path):
    """Download a file from URL with streaming."""
    print(f"  → Downloading to {output_path}...")
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    total = 0
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=65536):
            f.write(chunk)
            total += len(chunk)
    size_mb = total / (1024 * 1024)
    print(f"  ✓ Downloaded {size_mb:.1f} MB")


def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
         '-of', 'json', audio_path],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return float(data['format']['duration'])


def generate_srt_whisper(audio_path):
    """Generate SRT subtitles using faster-whisper with word timestamps."""
    from faster_whisper import WhisperModel

    print("  → Loading whisper model (tiny)...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")

    print("  → Transcribing audio...")
    segments, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en"
    )

    # Collect all words with timestamps
    words = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                w = word.word.strip()
                if w:
                    words.append({
                        'start': word.start,
                        'end': word.end,
                        'word': w
                    })

    if not words:
        return None

    print(f"  ✓ Detected {len(words)} words")

    # Group words into subtitle chunks (5-7 words per line)
    srt_entries = []
    chunk_size = 6
    idx = 1

    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        start = chunk[0]['start']
        end = chunk[-1]['end']
        # Add small padding to end
        end = min(end + 0.1, chunk[-1]['end'] + 0.5)
        text = ' '.join(w['word'] for w in chunk)
        srt_entries.append(format_srt_entry(idx, start, end, text))
        idx += 1

    return '\n'.join(srt_entries)


def generate_srt_from_script(script_text, audio_duration):
    """Fallback: generate SRT from script text distributed over audio duration."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        # Split by words if no sentences
        words = script_text.split()
        chunk_size = 8
        sentences = [' '.join(words[i:i + chunk_size])
                     for i in range(0, len(words), chunk_size)]

    if not sentences:
        return ""

    time_per_sentence = audio_duration / len(sentences)
    srt_entries = []

    for i, sentence in enumerate(sentences):
        start = i * time_per_sentence
        end = (i + 1) * time_per_sentence - 0.05
        # Split long sentences into max 2 lines
        if len(sentence) > 80:
            mid = len(sentence) // 2
            space_idx = sentence.find(' ', mid)
            if space_idx != -1:
                sentence = sentence[:space_idx] + '\n' + sentence[space_idx + 1:]
        srt_entries.append(format_srt_entry(i + 1, start, end, sentence))

    return '\n'.join(srt_entries)


def format_srt_entry(index, start, end, text):
    """Format a single SRT entry."""
    return f"{index}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{text}\n"


def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def render_video(video_path, audio_path, srt_path, output_path):
    """Merge video + audio and burn subtitles with FFmpeg."""
    # Subtitle style: white text, black outline, bottom center, modern look
    style = (
        "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BackColour=&H80000000,"
        "Outline=2,Shadow=1,Alignment=2,MarginV=35,"
        "Bold=1"
    )

    # Escape the subtitle path for FFmpeg filter (replace \ and : )
    srt_escaped = srt_path.replace('\\', '/').replace(':', r'\:')

    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-vf', f"subtitles={srt_escaped}:force_style='{style}'",
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-movflags', '+faststart',
        '-max_muxing_queue_size', '1024',
        output_path
    ]

    print(f"  → Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ✗ FFmpeg stderr:\n{result.stderr[-2000:]}")
        raise RuntimeError(f"FFmpeg failed with return code {result.returncode}")

    # Get output file size
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  ✓ Rendered video: {size_mb:.1f} MB")


def upload_to_catbox(file_path):
    """Upload file to catbox.moe (free, no signup, permanent hosting)."""
    print(f"  → Uploading to catbox.moe...")
    file_size = os.path.getsize(file_path)

    if file_size > 200 * 1024 * 1024:
        raise ValueError(f"File too large for catbox.moe: {file_size / 1024 / 1024:.0f}MB (max 200MB)")

    with open(file_path, 'rb') as f:
        response = requests.post(
            'https://catbox.moe/user/api.php',
            data={'reqtype': 'fileupload'},
            files={'fileToUpload': ('output.mp4', f, 'video/mp4')},
            timeout=600
        )

    response.raise_for_status()
    url = response.text.strip()

    if not url.startswith('http'):
        raise RuntimeError(f"Unexpected catbox response: {url}")

    print(f"  ✓ Uploaded: {url}")
    return url


def upload_to_litterbox(file_path, expiry='72h'):
    """Upload to litterbox (temporary hosting, 24h/72h). Fallback option."""
    print(f"  → Uploading to litterbox ({expiry} expiry)...")

    with open(file_path, 'rb') as f:
        response = requests.post(
            'https://litterbox.catbox.moe/resources/internals/api.php',
            data={'reqtype': 'fileupload', 'time': expiry},
            files={'fileToUpload': ('output.mp4', f, 'video/mp4')},
            timeout=600
        )

    response.raise_for_status()
    url = response.text.strip()

    if not url.startswith('http'):
        raise RuntimeError(f"Unexpected litterbox response: {url}")

    print(f"  ✓ Uploaded: {url}")
    return url


def send_callback(callback_url, status, video_url=None, error=None):
    """Send result back to Make.com webhook."""
    payload = {'status': status}
    if video_url:
        payload['video_url'] = video_url
    if error:
        payload['error'] = str(error)[:500]

    print(f"  → Sending callback to Make.com...")
    try:
        response = requests.post(callback_url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"  ✓ Callback sent successfully")
    except Exception as e:
        print(f"  ✗ Callback failed: {e}")


def main():
    print("=" * 60)
    print("VIDEO RENDERER - GitHub Actions + Make.com")
    print("=" * 60)

    # Read inputs from environment variables
    video_url = os.environ.get('VIDEO_URL', '')
    audio_url = os.environ.get('AUDIO_URL', '')
    script = os.environ.get('SCRIPT', '')
    callback_url = os.environ.get('CALLBACK_URL', '')

    if not video_url or not audio_url:
        print("ERROR: VIDEO_URL and AUDIO_URL are required")
        if callback_url:
            send_callback(callback_url, 'error', error='Missing VIDEO_URL or AUDIO_URL')
        sys.exit(1)

    try:
        # Create work directory
        os.makedirs('work', exist_ok=True)

        # Step 1: Download files
        print("\n[1/4] DOWNLOADING FILES")
        download_file(video_url, 'work/input_video.mp4')
        download_file(audio_url, 'work/input_audio.mp3')

        # Step 2: Generate subtitles
        print("\n[2/4] GENERATING SUBTITLES")
        srt_content = generate_srt_whisper('work/input_audio.mp3')

        if srt_content is None:
            print("  ⚠ Whisper detected no words, falling back to script-based subtitles")
            if script:
                duration = get_audio_duration('work/input_audio.mp3')
                srt_content = generate_srt_from_script(script, duration)
            else:
                print("  ⚠ No script provided either, rendering without subtitles")
                srt_content = ""

        if srt_content:
            with open('work/subtitles.srt', 'w', encoding='utf-8') as f:
                f.write(srt_content)
            print(f"  ✓ Generated {srt_content.count(chr(10) + chr(10))} subtitle entries")

        # Step 3: Render video
        print("\n[3/4] RENDERING VIDEO")
        if srt_content:
            render_video(
                'work/input_video.mp4',
                'work/input_audio.mp3',
                'work/subtitles.srt',
                'work/output.mp4'
            )
        else:
            # No subtitles, just merge video + audio
            cmd = [
                'ffmpeg', '-y',
                '-i', 'work/input_video.mp4',
                '-i', 'work/input_audio.mp3',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k',
                '-shortest',
                '-movflags', '+faststart',
                'work/output.mp4'
            ]
            subprocess.run(cmd, check=True)

        # Step 4: Upload
        print("\n[4/4] UPLOADING")
        try:
            output_url = upload_to_catbox('work/output.mp4')
        except Exception as e:
            print(f"  ⚠ Catbox failed: {e}, trying litterbox...")
            output_url = upload_to_litterbox('work/output.mp4')

        # Write output for GitHub Actions
        github_output = os.environ.get('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write(f"video_url={output_url}\n")

        # Send callback to Make.com
        if callback_url:
            send_callback(callback_url, 'success', video_url=output_url)

        print(f"\n{'=' * 60}")
        print(f"✅ DONE! Video URL: {output_url}")
        print(f"{'=' * 60}")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        if callback_url:
            send_callback(callback_url, 'error', error=str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
