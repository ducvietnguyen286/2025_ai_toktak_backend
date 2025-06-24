# coding: utf8
import datetime
import os
import time
from flask_restx import Namespace, Resource
from flask import render_template_string, make_response
from gevent import util

from app.services.shotstack_services import (
    ShotStackService,
    get_korean_typecast_voice,
    text_to_speech_kr,
    get_typecast_voices,
)

ns = Namespace(name="debug", description="User API")
from gevent import sleep

# HTML template for the voice test page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Voice Test</title>
    <style>
        body {
            font-family: 'Noto Sans KR', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .voice-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .voice-card img {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            margin-bottom: 10px;
            object-fit: cover;
        }
        .voice-name {
            font-weight: bold;
            margin-bottom: 5px;
            word-break: break-word;
        }
        .voice-name-en {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .voice-info {
            margin: 5px 0;
            color: #444;
        }
        .voice-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin: 10px 0;
        }
        .tag {
            background: #e9ecef;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            color: #495057;
        }
        .controls {
            margin: 15px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .control-group {
            margin: 10px 0;
        }
        .control-group label {
            display: block;
            margin-bottom: 5px;
            font-size: 0.9em;
            color: #495057;
        }
        .control-row {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .control-row input[type="range"] {
            flex: 1;
        }
        .control-value {
            min-width: 40px;
            text-align: right;
            font-size: 0.9em;
            color: #495057;
        }
        .test-button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 10px;
            width: 100%;
            position: relative;
        }
        .test-button:hover {
            background-color: #45a049;
        }
        .test-button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .test-button.processing {
            background-color: #2196F3;
            pointer-events: none;
        }
        .test-button.processing::after {
            content: '';
            position: absolute;
            width: 20px;
            height: 20px;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            border: 3px solid #ffffff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to {
                transform: translateY(-50%) rotate(360deg);
            }
        }
        .audio-section {
            margin-top: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            display: none;
        }
        .audio-section h4 {
            margin: 10px 0;
            color: #333;
            font-size: 0.9em;
        }
        .audio-file {
            margin: 10px 0;
            padding: 8px;
            background: white;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .audio-file label {
            display: block;
            margin-bottom: 5px;
            color: #666;
            font-size: 0.9em;
        }
        .audio-player {
            width: 100%;
            margin-top: 5px;
        }
        #loading {
            display: none;
            text-align: center;
            margin: 20px;
            padding: 20px;
            background: #e3f2fd;
            border-radius: 4px;
            color: #1976d2;
        }
        input[type="range"] {
            -webkit-appearance: none;
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: #ddd;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
    <h1>Voice Test Interface</h1>
    <div class="grid">
        {% for voice in voices %}
        <div class="voice-card" id="card-{{ voice.get('actor_id', '') }}">
            <img src="{{ voice.get('img_url', 'https://via.placeholder.com/100') }}" alt="{{ voice.get('name', {}).get('ko', 'Unknown') }}">
            <div class="voice-name">{{ voice.get('name', {}).get('ko', 'Unknown') }}</div>
            <div class="voice-name-en">{{ voice.get('name', {}).get('en', '') }}</div>
            
            <div class="voice-info">
                <div>성별: {{ voice.get('sex', ['Unknown'])[0] }}</div>
                <div>나이: {{ voice.get('age', 'Unknown') }}</div>
                <div>언어: {{ voice.get('language', 'Unknown') }}</div>
                <div>음질: {{ voice.get('audio_quality', 'Unknown') }}</div>
            </div>

            {% if voice.get('tag_v2', {}).get('mood') %}
            <div class="voice-tags">
                {% for mood in voice.get('tag_v2', {}).get('mood', []) %}
                    <span class="tag">{{ mood.get('title', '') }}</span>
                    {% for detail in mood.get('detail', []) %}
                        <span class="tag">{{ detail }}</span>
                    {% endfor %}
                {% endfor %}
            </div>
            {% endif %}

            <div class="controls">
                <div class="control-group">
                    <label>볼륨 (Volume)</label>
                    <div class="control-row">
                        <input type="range" min="0" max="200" value="100" 
                               class="volume-control" 
                               id="volume-{{ voice.get('actor_id', '') }}"
                               oninput="updateControlValue(this)">
                        <span class="control-value">100</span>
                    </div>
                </div>
                
                <div class="control-group">
                    <label>속도 (Speed) - 높을수록 느림</label>
                    <div class="control-row">
                        <input type="range" min="0" max="2" value="1" step="0.1"
                               class="speed-control"
                               id="speed-{{ voice.get('actor_id', '') }}"
                               oninput="updateControlValue(this)">
                        <span class="control-value">1.0</span>
                    </div>
                </div>

                <div class="control-group">
                    <label>템포 (Tempo) - 높을수록 빠름</label>
                    <div class="control-row">
                        <input type="range" min="0" max="2" value="1" step="0.1"
                               class="tempo-control"
                               id="tempo-{{ voice.get('actor_id', '') }}"
                               oninput="updateControlValue(this)">
                        <span class="control-value">1.0</span>
                    </div>
                </div>
            </div>

            <button class="test-button" onclick="testVoice('{{ voice.get('actor_id', '') }}')" id="btn-{{ voice.get('actor_id', '') }}">음성 테스트</button>
            
            <div class="audio-section" id="audio-section-{{ voice.get('actor_id', '') }}">
                <h4>생성된 파일 (Generated Files)</h4>
                <div id="audio-files-{{ voice.get('actor_id', '') }}">
                    <!-- Audio files will be inserted here -->
                </div>
                
                <h4>최종 파일 (Final Merged File)</h4>
                <div class="audio-file">
                    <label>Main File:</label>
                    <audio id="audio-main-{{ voice.get('actor_id', '') }}" class="audio-player" controls>
                        <source src="" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    <div id="loading">음성을 생성하는 중... 잠시만 기다려주세요...</div>

    <script>
        function updateControlValue(input) {
            const value = parseFloat(input.value).toFixed(1);
            input.nextElementSibling.textContent = value;
        }

        function disableAllButtons(disable = true) {
            document.querySelectorAll('.test-button').forEach(button => {
                button.disabled = disable;
            });
        }

        function testVoice(voiceId) {
            const audioSection = document.getElementById(`audio-section-${voiceId}`);
            const audioFiles = document.getElementById(`audio-files-${voiceId}`);
            const audioMain = document.getElementById(`audio-main-${voiceId}`);
            const button = document.getElementById(`btn-${voiceId}`);
            const loadingElement = document.getElementById('loading');
            
            // Get control values
            const volume = document.getElementById(`volume-${voiceId}`).value;
            const speed = document.getElementById(`speed-${voiceId}`).value;
            const tempo = document.getElementById(`tempo-${voiceId}`).value;
            
            // Show loading and disable all buttons
            loadingElement.style.display = 'block';
            disableAllButtons(true);
            button.classList.add('processing');
            button.textContent = '처리 중...';
            
            // Clear previous audio files
            audioFiles.innerHTML = '';
            audioMain.src = '';
            
            // Make API call
            fetch('/api/v1/debug/test-typecast', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    voice_id: voiceId,
                    volumn: parseFloat(volume),
                    speed_x: parseFloat(speed),
                    tempo: parseFloat(tempo)
                })
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading
                loadingElement.style.display = 'none';
                audioSection.style.display = 'block';
                
                // Add individual audio files
                data.audio_files.forEach((file, index) => {
                    const audioFileHtml = `
                        <div class="audio-file">
                            <label>File ${index + 1}:</label>
                            <audio class="audio-player" controls>
                                <source src="${file}" type="audio/mpeg">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                    `;
                    audioFiles.innerHTML += audioFileHtml;
                });
                
                // Update main audio file
                audioMain.src = data.main_file;
                audioMain.load();
                
                // Re-enable buttons and reset state
                disableAllButtons(false);
                button.classList.remove('processing');
                button.textContent = '음성 테스트';
            })
            .catch(error => {
                console.error('Error:', error);
                loadingElement.style.display = 'none';
                disableAllButtons(false);
                button.classList.remove('processing');
                button.textContent = '음성 테스트';
                alert('음성 생성 중 오류가 발생했습니다. 다시 시도해주세요.');
            });
        }
    </script>
</body>
</html>
"""


@ns.route("/gurnicorn")
class DebugGunicorn(Resource):
    def get(self):
        start = time.time()
        sleep(0.1)
        end = time.time()

        util.print_run_info()

        return {"elapsed": end - start}


@ns.route("/voice-test")
class VoiceTestPage(Resource):
    def get(self):
        voices = get_typecast_voices()
        html = render_template_string(HTML_TEMPLATE, voices=voices)
        response = make_response(html)
        response.headers["Content-Type"] = "text/html"
        return response


@ns.route("/test-typecast")
class DebugTestTypecast(Resource):
    def post(self):
        from flask import request

        data = request.get_json()
        voice_typecast = data.get("voice_id", "65e96ab52564d1136ecb1d67")
        volumn = data.get("volumn", 100)
        speed_x = data.get("speed_x", 1)
        tempo = data.get("tempo", 1)

        batch_id = 1
        date_create = datetime.datetime.now().strftime("%Y_%m_%d")
        dir_path = f"static/voice/gtts_voice/{date_create}/{batch_id}"
        config = ShotStackService.get_settings()
        origin_caption = "주방의 청소 도구가 항상 어지럽혀져 있다면, 누구나 한번쯤 고민해보셨을 거예요. 행주와 스폰지, 수세미까지 다양한 물건들이 자주 뒤섞이면서 찾아도 없고, 사용할 때마다 불편함이 커지기 마련입니다. 이런 일들이 자주 반복되면 집중력도 떨어지고, 주방을 사용할 때마다 스트레스를 받게 되죠.\\n이제 그 스트레스를 날려줄 수 있는 솔루션이 있습니다. 스테인레스 스틸로 만들어져 내구성이 뛰어난 주방 청소 도구 스토리지 랙을 사용해보세요. 이 랙은 다용도로 사용이 가능해 스폰지, 행주, 수세미 등 다양한 도구를 깔끔하게 정리해 줍니다. 특히, 구성품이 다공성 바닥으로 되어 있어 물이 쉽게 빠져나가면서 항상 건조한 상태를 유지할 수 있습니다. 이렇게 공간 효율이 높아지면, 주방에서 느끼는 불편함이 훨씬 줄어들겠죠. 매일 사용하는 도구가 정리되어 있으면 주방도 깔끔해져요.\\n이미 많은 분들이 만족하고 계십니다. 제품에 대한 후기가 수백 개 달리며 높은 평점을 기록하고 있어요. 일상생활에서 소소한 변화가 큰 차이를 만들어낼 수 있다는 점에서, 많은 사람들이 인정한 제품입니다.\\n주방에서의 불편함을 해소하고 싶으신 분이라면, 이 제품을 한 번 사용해보세요. 깔끔한 정리가 주는 편안함을 직접 느껴보시길 바랍니다."

        korean_voice = get_korean_typecast_voice(voice_typecast)
        if not korean_voice:
            return {"error": "Voice not found"}, 404

        config["volumn"] = volumn
        config["speed_x"] = speed_x
        config["tempo"] = tempo

        mp3_file, audio_duration, audio_files = text_to_speech_kr(
            korean_voice, origin_caption, dir_path, config, get_audios=True
        )

        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

        main_file_url = f"{current_domain}/{mp3_file.replace('/static', '/')}"
        audio_files_url = [
            f"{current_domain}/{audio_file.replace('/static', '/')}"
            for audio_file in audio_files
        ]

        return {
            "main_file": main_file_url,
            "audio_duration": audio_duration,
            "audio_files": audio_files_url,
        }
