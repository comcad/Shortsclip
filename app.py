import os
import json
import requests
import uuid
import threading
import subprocess
import random
import shutil
import textwrap
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import platform
import sys

# --- Flask App Setup ---
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Configuration & State Management ---
HISTORY_DIR = 'history'
VIDEO_DIR = os.path.join('static', 'videos')
BACKGROUNDS_DIR = os.path.join('static', 'backgrounds')
MUSIC_DIR = 'music'
FONT_DIR = 'fonts'
TASKS = {}

# --- Helper Functions ---

def get_font_path():
    """Finds the first .ttf font file in the fonts directory."""
    if not os.path.exists(FONT_DIR): return None
    for file in os.listdir(FONT_DIR):
        if file.lower().endswith('.ttf'):
            return os.path.join(os.getcwd(), FONT_DIR, file)
    return None

def get_media_duration(media_path):
    """Gets the duration of a video or audio file using ffprobe."""
    if not os.path.exists(media_path) or os.path.getsize(media_path) == 0:
        return 0.0
    command = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', media_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0.0

def sanitize_ffmpeg_text(text):
    """A more robust function to REMOVE all special characters that can break ffmpeg's filters."""
    bad_chars = ["'", "\"", "\\", ":", "%"]
    for char in bad_chars:
        text = text.replace(char, "")
    return text

def wrap_text(text, line_length=25):
    """Wraps text to a specified line length for ffmpeg."""
    return '\n'.join(textwrap.wrap(text, width=line_length))

def create_prompt(topic, duration):
    """Creates a detailed prompt for the Ollama model."""
    return f"""
    You are an expert scriptwriter for viral social media videos. Your task is to generate a script that is approximately {duration} seconds long when spoken.
    **Topic:** {topic}
    **Instructions:**
    1.  **Title:** Create a short, catchy title. The title itself should not be part of the spoken script.
    2.  **Spoken Script:** Write the full script that will be spoken. The total speaking time should be about {duration} seconds. Start with a hook and end with a call to action. Do not include labels like 'Hook:' or 'Body:'.
    3.  **Keywords:** Provide 5 relevant keywords as a comma-separated list.
    **Output Format:**
    Return the response as a valid JSON object only. The JSON must have keys: "title", "spoken_script", "keywords".
    """

def generate_audio_gtts(text, output_path):
    """Generates audio using the gTTS library."""
    from gtts import gTTS
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(output_path)

def generate_audio_elevenlabs(api_key, text, output_path):
    """Generates audio using the ElevenLabs API."""
    if not api_key: raise ValueError("ElevenLabs API key is missing.")
    
    # A popular default voice ID. This could be made configurable in the future.
    voice_id = '21m00Tcm4TlvDq8ikWAM' 
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = { "Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": api_key }
    data = { "text": text, "model_id": "eleven_monolingual_v1", "voice_settings": { "stability": 0.5, "similarity_boost": 0.5 } }

    response = requests.post(url, json=data, headers=headers, timeout=60)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        f.write(response.content)

def generate_subtitles_api(audio_path, api_url):
    """Generates word-level timestamps by calling the Whisper Docker API."""
    if not api_url: raise ValueError("Whisper API Endpoint is not configured in Settings.")
    endpoint = f"{api_url}/asr"
    params = {'task': 'transcribe', 'language': 'en', 'word_timestamps': 'true', 'output': 'json'}
    with open(audio_path, 'rb') as f:
        files = {'audio_file': (os.path.basename(audio_path), f, 'audio/mpeg')}
        response = requests.post(endpoint, files=files, params=params, timeout=300)
        response.raise_for_status()
    data = response.json()
    all_words = []
    for segment in data.get('segments', []):
        for word_info in segment.get('words', []):
            all_words.append({"word": word_info['word'], "start": word_info['start'], "end": word_info['end']})
    if not all_words: raise Exception("Whisper API returned no words.")
    return all_words

def process_video_task(task_id, config):
    """Main background thread function to create a video."""
    voiceover_path = None
    temp_files = []
    try:
        TASKS[task_id]['status'] = 'Verifying setup...'
        if shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None: 
            raise FileNotFoundError("ffmpeg/ffprobe not found. Please ensure ffmpeg is installed and its 'bin' directory is in your system's PATH.")
        font_path = get_font_path()
        if font_path is None: raise FileNotFoundError(f"No .ttf font file found in the '{FONT_DIR}' directory.")
        
        script_data = {}
        if config['script_source'] == 'ai':
            TASKS[task_id]['status'] = 'Generating script...'
            prompt = create_prompt(config['topic'], config['duration'])
            response = requests.post(f"{config['ollama']['url']}/api/generate", json={"model": config['ollama']['model'], "prompt": prompt, "stream": False, "format": "json"}, timeout=60)
            response.raise_for_status()
            script_data = json.loads(response.json().get('response', '{}'))
            if not script_data: raise Exception("Failed to parse script from Ollama.")
        else:
            TASKS[task_id]['status'] = 'Using manual script...'
            script_data['title'] = config.get('manual_title', 'My Video')
            script_data['spoken_script'] = config.get('manual_script', 'This is my custom video script.')
        
        script_data.setdefault('spoken_script', 'The AI did not provide a script.')
        
        voiceover_generated = False
        if config['enable_voiceover']:
            TASKS[task_id]['status'] = 'Generating voiceover...'
            voiceover_path = os.path.join(HISTORY_DIR, f"{task_id}_voiceover.mp3")
            temp_files.append(voiceover_path)
            
            if config.get('audio_source') == 'elevenlabs':
                generate_audio_elevenlabs(config['elevenlabs_api_key'], script_data['spoken_script'], voiceover_path)
            else: # Default to gTTS
                generate_audio_gtts(script_data['spoken_script'], voiceover_path)

            voiceover_generated = True

        final_duration = get_media_duration(voiceover_path) if voiceover_generated else config['duration']
        if final_duration == 0:
            final_duration = config['duration']

        subtitles = []
        if config['enable_subtitles'] and voiceover_generated:
            TASKS[task_id]['status'] = 'Transcribing audio for subtitles...'
            subtitles = generate_subtitles_api(voiceover_path, config['whisper_api_url'])
        
        TASKS[task_id]['status'] = 'Rendering video...'
        output_filename = f"{task_id}.mp4"
        output_path = os.path.join(VIDEO_DIR, output_filename)
        
        font_path_escaped = font_path.replace('\\', '/')
        if platform.system() == 'Windows': font_path_escaped = font_path_escaped.replace(':', '\\:')
        
        video_filters = []
        if config['show_title']:
            wrapped_title = wrap_text(script_data.get("title", " "))
            title_text = sanitize_ffmpeg_text(wrapped_title)
            video_filters.append(f"drawtext=fontfile='{font_path_escaped}':text='{title_text}':fontcolor=white:fontsize=72:box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=200")

        if config['enable_subtitles'] and subtitles:
            for word_info in subtitles:
                word_text = sanitize_ffmpeg_text(word_info['word'].strip().upper())
                if not word_text.strip() or 'start' not in word_info or 'end' not in word_info: continue
                start, end = word_info['start'], word_info['end']
                video_filters.append(f"drawtext=fontfile='{font_path_escaped}':text='{word_text}':fontcolor=white:fontsize=80:box=1:boxcolor=black@0.6:boxborderw=15:x=(w-text_w)/2:y=h-300:enable='between(t,{start},{end})':fix_bounds=true")
        
        # --- DEFINITIVE FIX: Convert web path to local file system path ---
        local_video_path = os.path.join(os.getcwd(), config['selected_video'][1:])
        if not os.path.exists(local_video_path):
             raise FileNotFoundError(f"Selected video not found on server at: {local_video_path}")

        ffmpeg_cmd = ['ffmpeg', '-stream_loop', '-1', '-i', local_video_path]

        audio_inputs = []
        if voiceover_generated: audio_inputs.append(voiceover_path)
        if config['enable_music'] and config['selected_music']:
            music_path = os.path.join(MUSIC_DIR, config['selected_music'])
            if os.path.exists(music_path):
                audio_inputs.append(music_path)
        
        filter_complex_parts = []
        map_outputs = ["[v]"]
        
        if len(audio_inputs) == 2:
            ffmpeg_cmd.extend(['-i', audio_inputs[0], '-i', audio_inputs[1]])
            filter_complex_parts.append(f"[1:a]volume={config['voice_volume']}[a1];[2:a]volume={config['music_volume']}[a2];[a1][a2]amix=inputs=2:duration=first[aout]")
            map_outputs.append("[aout]")
        elif len(audio_inputs) == 1:
            ffmpeg_cmd.extend(['-i', audio_inputs[0]])
            volume = config['voice_volume'] if voiceover_generated else config['music_volume']
            filter_complex_parts.append(f"[1:a]volume={volume}[aout]")
            map_outputs.append("[aout]")
        else:
            ffmpeg_cmd.extend(['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100'])
            map_outputs.append("1:a")

        if video_filters:
            filter_complex_parts.insert(0, "[0:v]" + ",".join(video_filters) + "[v]")

        if filter_complex_parts:
             ffmpeg_cmd.extend(['-filter_complex', ";".join(filter_complex_parts)])
       
        for map_arg in map_outputs:
             ffmpeg_cmd.extend(['-map', map_arg])

        ffmpeg_cmd.extend(['-c:v', 'libx264', '-c:a', 'aac', '-t', str(final_duration), '-y', output_path])
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0: raise Exception(f"FFmpeg failed: {result.stderr}")

        TASKS[task_id]['status'] = 'complete'
        TASKS[task_id]['video_url'] = f'/static/videos/{output_filename}'

    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        TASKS[task_id]['error'] = str(e)
    finally:
        for p in temp_files:
            if os.path.exists(p): os.remove(p)

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/list-videos')
def list_videos():
    videos = {}
    if not os.path.exists(BACKGROUNDS_DIR): return jsonify({})
    category_order = ['minecraft', 'fortnite', 'custom']
    found_categories = [d for d in os.listdir(BACKGROUNDS_DIR) if os.path.isdir(os.path.join(BACKGROUNDS_DIR, d))]
    sorted_categories = [cat for cat in category_order if cat in found_categories]
    for cat in found_categories:
        if cat not in sorted_categories:
            sorted_categories.append(cat)
    for category in sorted_categories:
        category_path = os.path.join(BACKGROUNDS_DIR, category)
        if os.path.isdir(category_path):
            videos[category] = [f"/static/backgrounds/{category}/{f}" for f in os.listdir(category_path) if f.lower().endswith(('.mp4', '.mov'))]
    return jsonify(videos)

@app.route('/list-music')
def list_music():
    if not os.path.exists(MUSIC_DIR): return jsonify([])
    return jsonify([f for f in os.listdir(MUSIC_DIR) if f.lower().endswith('.mp3')])

@app.route('/generate', methods=['POST'])
def start_generation_task():
    task_id = str(uuid.uuid4())
    post_data = request.get_json()
    TASKS[task_id] = {'status': 'queued'}
    
    config = {
        'topic': post_data.get('topic'),
        'duration': int(post_data.get('duration', 30)),
        'selected_video': post_data.get('selectedVideo'),
        'script_source': post_data.get('scriptSource'),
        'manual_title': post_data.get('manualTitle'),
        'manual_script': post_data.get('manualScript'),
        'enable_voiceover': post_data.get('enableVoiceover'),
        'audio_source': post_data.get('audioSource'),
        'enable_music': post_data.get('enableMusic'),
        'selected_music': post_data.get('selectedMusic'),
        'voice_volume': post_data.get('voiceVolume', 1.0),
        'music_volume': post_data.get('musicVolume', 0.2),
        'show_title': post_data.get('showTitle'),
        'enable_subtitles': post_data.get('enableSubtitles'),
        'ollama': { 'url': post_data.get('ollamaUrl'), 'model': post_data.get('ollamaModel') },
        'whisper_api_url': post_data.get('whisperApiUrl'),
        'elevenlabs_api_key': post_data.get('elevenlabsApiKey')
    }
    
    thread = threading.Thread(target=process_video_task, args=(task_id, config))
    thread.start()
    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def get_task_status(task_id):
    return jsonify(TASKS.get(task_id, {}))

@app.route('/history')
def get_video_history():
    if not os.path.exists(VIDEO_DIR): return jsonify([])
    files = sorted([f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')], key=lambda x: os.path.getmtime(os.path.join(VIDEO_DIR, x)), reverse=True)
    history = [{'file': f, 'title': os.path.splitext(f)[0], 'date': datetime.fromtimestamp(os.path.getmtime(os.path.join(VIDEO_DIR, f))).strftime('%B %d, %Y, %I:%M %p')} for f in files]
    return jsonify(history)

# --- Main Execution ---
if __name__ == '__main__':
    for directory in [HISTORY_DIR, VIDEO_DIR, FONT_DIR, BACKGROUNDS_DIR, os.path.join(BACKGROUNDS_DIR, 'minecraft'), os.path.join(BACKGROUNDS_DIR, 'fortnite'), os.path.join(BACKGROUNDS_DIR, 'custom'), MUSIC_DIR]:
        if not os.path.exists(directory): os.makedirs(directory)
        
    print("--- Video Agent Server ---")
    app.run(host='0.0.0.0', port=5000, debug=False)