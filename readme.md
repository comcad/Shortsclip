#                 Shortsclip 
### An Automated Social Media Video Creaton Agent

This is a Flask-based web application that automates the creation of short social media videos. It uses AI to generate scripts, adds voiceovers, subtitles, and background music, and renders the final video using FFmpeg.

![application](https://github.com/user-attachments/assets/5313e315-d2fa-4525-99d2-46f31904a506)

![2025-06-15 10_47_40-Automated Social Video Agent - Control Panel — Mozilla Firefox](https://github.com/user-attachments/assets/50655f61-1211-47fe-b834-276daf138b53)


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

## Running Locally with Python (Recomended Setup)

Follow these steps to run the application locally without Docker.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/comcad/Shortsclip.git
    cd Shortsclip
    ```

2.  **Install Python Dependencies:**
    Open your terminal or command prompt and run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create Media Folders and Add Content:**
    * Place music in the `music` folder and add any `.mp3`.
    * place background videos in `static/backgrounds` folder and add any `.mp4`.

4.  **Run the Application:**
    Start the Flask server:
    ```bash
    py app.py
    ```

5.  **Access the Web UI:**
    Open your web browser and navigate to `http://localhost:5000`.
    

## Running with Docker (CPU Only!!! working on nvenc support)

1.  **Clone the repo and cd into its folder:**
    ```bash
    git clone [https://github.com/comcad/Shortsclip.git](https://github.com/comcad/Shortsclip.git)
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

