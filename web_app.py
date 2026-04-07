import os
from flask import Flask, render_template, request, session, jsonify
from random import choice
import json
import requests
import base64
import time
import uuid

app = Flask(__name__)
app.secret_key = 'secret-key-for-sessions-12345'

# Отключаем предупреждения SSL
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ЗАГРУЗКА ТЕРМИНО

db_programming = []
db_db_admin = []
db_english = []

current_dir = os.path.dirname(os.path.abspath(__file__))

try:
    with open(os.path.join(current_dir, 'db.json'), 'r', encoding='utf-8') as f:
        db_programming = json.load(f)
        print(f"✅ Загружено {len(db_programming)} терминов по программированию")
except Exception as e:
    print(f"❌ Ошибка загрузки db.json: {e}")

try:
    with open(os.path.join(current_dir, 'ABD.json'), 'r', encoding='utf-8') as f:
        db_db_admin = json.load(f)
        print(f"✅ Загружено {len(db_db_admin)} терминов по БД")
except Exception as e:
    print(f"❌ Ошибка загрузки ABD.json: {e}")

try:
    with open(os.path.join(current_dir, 'eng.json'), 'r', encoding='utf-8') as f:
        db_english = json.load(f)
        print(f"✅ Загружено {len(db_english)} терминов по английскому")
except Exception as e:
    print(f"❌ Ошибка загрузки eng.json: {e}")


# КЛАСС GIGACHAT

class RealGigaChat:
    def __init__(self):
        self.client_id = "019c2347-28be-7aab-99d3-b35a8b5f6d98"
        self.client_secret = "MDE5YzI2NDctMjhiZS03YWFiLTk5ZDMtYjM1YThiNWY2ZDk40mJLNTTIzNWVmLTBjOWUtNGrJMS1iNjY0LWFjNzcyZmM0ZWU1Zg=="
        self.access_token = None
        self.token_expires = 0

    def _get_token(self):
        if self.access_token and time.time() < self.token_expires:
            return self.access_token

        try:
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4())
            }

            response = requests.post(
                auth_url,
                headers=headers,
                data={"scope": "GIGACHAT_API_PERS"},
                verify=False,
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 1800)
                self.token_expires = time.time() + expires_in - 60
                print("✅ Токен GigaChat получен")
                return self.access_token
            else:
                print(f"❌ Ошибка: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def ask_question(self, question: str) -> str:
        token = self._get_token()
        if not token:
            return "🤖 GigaChat временно недоступен. Попробуйте позже."

        try:
            url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "GigaChat",
                "messages": [{"role": "user", "content": question}],
                "temperature": 0.7,
                "max_tokens": 1000
            }

            response = requests.post(url, headers=headers, json=data, verify=False, timeout=45)

            if response.status_code == 200:
                result = response.json()
                return f"🤖 *Ответ GigaChat:*\n\n{result['choices'][0]['message']['content']}"
            else:
                return "🤖 GigaChat временно недоступен."
        except Exception as e:
            return f"🤖 Ошибка: {str(e)}"

    def explain_term(self, term: str) -> str:
        token = self._get_token()
        if not token:
            return f"📚 *{term}*\n\nGigaChat временно недоступен. Попробуйте позже."

        try:
            url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            prompt = f"""Объясни термин "{term}" простыми словами для студента.
Структура: определение, как работает, пример, вопрос."""

            data = {
                "model": "GigaChat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 800
            }

            response = requests.post(url, headers=headers, json=data, verify=False, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return f"📚 *{term.upper()}*\n\n{result['choices'][0]['message']['content']}"
            else:
                return f"📚 *{term}*\n\nОбъяснение временно недоступно."
        except Exception as e:
            return f"📚 *{term}*\n\nОшибка: {str(e)}"


gigachat = RealGigaChat()

# ХРАНИЛИЩЕ СЕССИЙ

user_sessions = {}


def get_session():
    session_id = session.get('user_id')
    if not session_id:
        session['user_id'] = str(uuid.uuid4())
        session_id = session['user_id']

    if session_id not in user_sessions:
        user_sessions[session_id] = {
            'topic': None,
            'amount': 0,
            'right': 0,
            'variants': [],
            'correct': None
        }
    return user_sessions[session_id]


# ГЕНЕРАЦИЯ ВОПРОСОВ

def generate_question(topic):
    if topic == 'programming':
        data = db_programming
    elif topic == 'db_admin':
        data = db_db_admin
    elif topic == 'english':
        data = db_english
    else:
        return None

    if not data or len(data) == 0:
        return None

    variants = [choice(data) for _ in range(min(4, len(data)))]
    correct = choice(variants)

    return {
        'prof': correct['prof'],
        'variants': [v['plain'] for v in variants],
        'correct': correct['plain']
    }


# ВЕБ-МАРШРУТЫ
@app.route('/')
def index():
    return render_template('chat.html')


@app.route('/api/action', methods=['GET', 'POST'])
def action():
    if request.method == 'GET':
        return jsonify({'response': 'Сервер работает!', 'menu': 'main'})

    try:
        data = request.json
        if not data:
            return jsonify({'response': 'Ошибка: данные не получены', 'menu': 'main'})

        action_type = data.get('action')
        user_input = data.get('message', '')
        session_data = get_session()

        # START
        if action_type == 'start':
            return jsonify({
                'response': '👋 Привет! Я помогу тебе изучить профессиональные термины!',
                'menu': 'main'
            })

        # LEARN
        elif action_type == 'learn':
            return jsonify({
                'response': '📚 Выберите направление:',
                'menu': 'learn'
            })

        # ВЫБОР ТЕМЫ
        elif action_type == 'topic':
            topic = data.get('topic')
            session_data['topic'] = topic
            session_data['amount'] = 0
            session_data['right'] = 0

            topic_names = {
                'programming': 'Программирование',
                'db_admin': 'Базы данных',
                'english': 'Английский язык'
            }

            question = generate_question(topic)
            if question:
                session_data['variants'] = question['variants']
                session_data['correct'] = question['correct']
                return jsonify({
                    'response': f'✅ Тема: {topic_names.get(topic, topic)}',
                    'question': question,
                    'menu': 'quiz'
                })
            else:
                return jsonify({
                    'response': '❌ В этой теме пока нет терминов!',
                    'menu': 'main'
                })

        # ОТВЕТ НА ВОПРОС
        elif action_type == 'answer':
            answer = data.get('answer')
            is_correct = (answer == session_data['correct'])

            if is_correct:
                session_data['right'] += 1
                response = '✅ Верно!'
            else:
                response = f'❌ Неверно! Правильный ответ: {session_data["correct"]}'

            session_data['amount'] += 1
            percent = (session_data['right'] / session_data['amount']) * 100 if session_data['amount'] > 0 else 0

            next_question = generate_question(session_data['topic'])
            if next_question:
                session_data['variants'] = next_question['variants']
                session_data['correct'] = next_question['correct']
                stats = f'\n\n📊 Статистика: {session_data["right"]}/{session_data["amount"]} ({percent:.0f}%)'
                return jsonify({
                    'response': response + stats,
                    'next_question': next_question,
                    'menu': 'quiz'
                })
            else:
                return jsonify({
                    'response': f'{response}\n\n🏆 Итог: {session_data["right"]}/{session_data["amount"]} ({percent:.0f}%)',
                    'menu': 'main'
                })

        # AI МЕНЮ
        elif action_type == 'ai_menu':
            return jsonify({
                'response': '🤖 Режим AI-помощника\n\nВыберите действие:',
                'menu': 'ai'
            })

        # ОБЪЯСНИТЬ ТЕРМИН
        elif action_type == 'explain_term':
            if not user_input:
                return jsonify({
                    'response': '📝 Введите термин для объяснения:',
                    'awaiting': 'term'
                })
            explanation = gigachat.explain_term(user_input)
            return jsonify({
                'response': explanation,
                'menu': 'ai'
            })

        # СПРОСИТЬ AI
        elif action_type == 'ask_ai':
            if not user_input:
                return jsonify({
                    'response': '💭 Задайте ваш вопрос:',
                    'awaiting': 'question'
                })
            answer = gigachat.ask_question(user_input)
            return jsonify({
                'response': answer,
                'menu': 'ai'
            })

        # EXIT
        elif action_type == 'exit':
            percent = (session_data['right'] / session_data['amount']) * 100 if session_data['amount'] > 0 else 0
            stats = f'📊 Сессия завершена. Результаты: {session_data["right"]}/{session_data["amount"]} ({percent:.0f}%)'
            session_data['topic'] = None
            session_data['amount'] = 0
            session_data['right'] = 0
            return jsonify({
                'response': stats,
                'menu': 'main'
            })

        # BACK
        elif action_type == 'back':
            return jsonify({
                'response': '🔙 Главное меню',
                'menu': 'main'
            })

        return jsonify({'response': 'Используйте кнопки меню', 'menu': 'main'})

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'response': f'Ошибка: {str(e)}', 'menu': 'main'})


if __name__ == '__main__':
    print('=' * 50)
    print('🌐 ВЕБ-БОТ ЗАПУЩЕН')
    print('📍 Откройте: http://localhost:5000')
    print('=' * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)