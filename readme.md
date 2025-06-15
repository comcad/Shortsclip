# Automated Social Video Agent

This is a Flask-based web application that automates the creation of short social media videos. It uses AI to generate scripts, adds voiceovers, subtitles, and background music, and renders the final video using FFmpeg.

## Features

- **AI Script Generation**: Connects to an Ollama instance to generate video scripts from a topic.
- **Manual Script Option**: Use your own custom titles and scripts.
- **Text-to-Speech**: Generates voiceovers using gTTS or ElevenLabs.
- **Auto-Subtitles**: Transcribes audio using a Whisper API to create word-level subtitles.
- **Custom Media**: Use your own library of background videos and music.
- **Docker Support**: Includes a Dockerfile for easy, cross-platform deployment.

## Prerequisites

- Python 3.9+
- FFmpeg
- Docker (recommended)
- An Ollama instance (for AI features)
- A Whisper API endpoint (for subtitle features)

## Running with Docker (Recommended)

1.  **Clone the repo and cd into its folder:**
    ```bash
    git clone https://github.com/comcad/Shortsclip.git
     ```
    ```bash
    cd Shortsclip 
     ```
    
2.  **Build the Docker image:**
    ```bash
    docker build -t video-agent .
    ```

3.  **Run the Docker container:**
    ```bash
    docker run -d \
      -p 5000:5000 \
      -v "$(pwd)"/static/videos:/app/static/videos \
      -v "$(pwd)"/static/backgrounds:/app/static/backgrounds \
      -v "$(pwd)"/music:/app/music \
      -v "$(pwd)"/fonts:/app/fonts \
      --name video-agent-container \
      video-agent
    ```

4.  Access the web UI at `http://localhost:5000`.
