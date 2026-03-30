# 🎬 Video Renderer — GitHub Actions + Make.com

A **free** automated video renderer that runs entirely on GitHub Actions.  
It merges video + audio and burns synced subtitles, then returns a public URL.

## How It Works

```
Make.com → GitHub API (repository_dispatch) → GitHub Actions Runner
                                                  ↓
                                          1. Download video & audio
                                          2. Generate subtitles (faster-whisper)
                                          3. Merge with FFmpeg
                                          4. Upload to catbox.moe
                                                  ↓
                                          Callback → Make.com webhook
```

## Setup

### 1. Create GitHub Repository

1. Go to [github.com/new](https://github.com/new) and create a **public** repository (e.g. `video-renderer`)
2. Push this code to the repository:

```bash
cd Renderer
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/video-renderer.git
git push -u origin main
```

### 2. Create a GitHub Personal Access Token (PAT)

1. Go to [GitHub Settings → Tokens](https://github.com/settings/tokens?type=beta)
2. Click **"Generate new token"** (Fine-grained)
3. Give it a name like `make-renderer`
4. Set **Repository access** → Select the `video-renderer` repo
5. Under **Permissions → Repository permissions**:
   - **Actions**: Read and write
   - **Contents**: Read
6. Click **Generate token** and copy it

### 3. Set Up Make.com Scenario

You need **two modules** in your Make.com scenario to integrate with the renderer:

---

#### Module A: Trigger the Render (HTTP Request)

Use an **HTTP → Make a request** module:

| Field | Value |
|-------|-------|
| **URL** | `https://api.github.com/repos/YOUR_USERNAME/video-renderer/dispatches` |
| **Method** | `POST` |
| **Headers** | `Authorization: Bearer YOUR_GITHUB_PAT` |
| | `Accept: application/vnd.github+json` |
| | `X-GitHub-Api-Version: Authorizatio2022-11-28` |
| **Body type** | `Raw` → `JSON (application/json)` |

**Body:**
```json
{
  "event_type": "render-video",
  "client_payload": {
    "video_url": "{{VIDEO_URL_FROM_PREVIOUS_MODULE}}",
    "audio_url": "{{AUDIO_URL_FROM_TEXTCAST}}",
    "script": "{{SCRIPT_FROM_CHATGPT}}",
    "callback_url": "{{YOUR_MAKE_WEBHOOK_URL}}"
  }
}
```

---

#### Module B: Receive the Result (Webhook)

1. Create a **Webhooks → Custom webhook** module in Make.com
2. Copy the webhook URL (it looks like `https://hook.us1.make.com/abc123...`)
3. Use this URL as the `callback_url` in Module A above

The webhook will receive:
```json
{
  "status": "success",
  "video_url": "https://files.catbox.moe/abc123.mp4"
}
```

---

### Complete Make.com Flow

```
1. [ChatGPT] → generates script
2. [Router]  → selects 1 of 3 videos
3. [TextCast] → generates voiceover audio
4. [HTTP Request] → triggers GitHub Actions renderer
5. [Webhook] → receives rendered video URL
6. [Next steps...] → post to social media, save, etc.
```

## Testing

### Manual Test via GitHub UI

1. Go to your repo → **Actions** tab
2. Click **"Render Video"** workflow
3. Click **"Run workflow"**
4. Fill in the video URL, audio URL, and optionally script + callback URL
5. Watch the workflow run

### Test via cURL

```bash
curl -X POST \
  https://api.github.com/repos/YOUR_USERNAME/video-renderer/dispatches \
  -H "Authorization: Bearer YOUR_GITHUB_PAT" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d '{
    "event_type": "render-video",
    "client_payload": {
      "video_url": "https://example.com/video.mp4",
      "audio_url": "https://example.com/audio.mp3",
      "script": "Hello world. This is a test.",
      "callback_url": "https://hook.us1.make.com/your-webhook-url"
    }
  }'
```

## Limits & Notes

| Resource | Limit |
|----------|-------|
| GitHub Actions free minutes | **2,000 min/month** (public repo = unlimited!) |
| Max render time | 15 minutes per video |
| Output file upload | 200 MB max (catbox.moe) |
| Subtitle engine | faster-whisper (tiny model, word-level sync) |
| Output format | MP4 (H.264 + AAC) |

> **💡 Tip**: Public repositories get **unlimited** GitHub Actions minutes!
> Make the repo public to avoid hitting the 2,000 min/month limit.

## File Structure

```
.
├── .github/
│   └── workflows/
│       └── render.yml      # GitHub Actions workflow
├── render.py               # Main rendering script
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Customization

### Subtitle Style

Edit the `style` variable in `render.py` → `render_video()` function to change:
- Font, size, color
- Outline thickness
- Position (MarginV)
- Bold/italic

### Video Quality

Edit the FFmpeg parameters in `render_video()`:
- `-crf 23` → lower = better quality, larger file (18-28 recommended)
- `-preset fast` → options: ultrafast, superfast, veryfast, faster, fast, medium, slow
