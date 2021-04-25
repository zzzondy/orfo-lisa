# импортируем библиотеки
from flask import Flask, request
import logging
import sqlite3
# библиотека, которая нам понадобится для работы с JSON
import json

# создаём приложение
# мы передаём __name__, в нем содержится информация,
# в каком модуле мы находимся.
# В данном случае там содержится '__main__',
# так как мы обращаемся к переменной из запущенного модуля.
# если бы такое обращение, например,
# произошло внутри модуля logging, то мы бы получили 'logging'
app = Flask(__name__)
STARTED_GAME = False
WAITING_FOR_ANSWER = False
GAME_WORDS = []
GAME_WORD1 = ''
GAME_WORD2 = ''
WORD_INDEX = 0
COUNT = 0

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Создадим словарь, чтобы для каждой сессии общения
# с навыком хранились подсказки, которые видел пользователь.
# Это поможет нам немного разнообразить подсказки ответов
# (buttons в JSON ответа).
# Когда новый пользователь напишет нашему навыку,
# то мы сохраним в этот словарь запись формата
# sessionStorage[user_id] = {'suggests': ["Не хочу.", "Не буду.", "Отстань!" ]}
# Такая запись говорит, что мы показали пользователю эти три подсказки.
# Когда он откажется купить слона,
# то мы уберем одну подсказку. Как будто что-то меняется :)
sessionStorage = {}


@app.route('/post', methods=['POST'])
# Функция получает тело запроса и возвращает ответ.
# Внутри функции доступен request.json - это JSON,
# который отправила нам Алиса в запросе POST
def main():
    logging.info(f'Request: {request.json!r}')

    # Начинаем формировать ответ, согласно документации
    # мы собираем словарь, который потом при помощи
    # библиотеки json преобразуем в JSON и отдадим Алисе
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    # Отправляем request.json и response в функцию handle_dialog.
    # Она сформирует оставшиеся поля JSON, которые отвечают
    # непосредственно за ведение диалога
    handle_dialog(request.json, response)

    logging.info(f'Response:  {response!r}')

    # Преобразовываем в JSON и возвращаем
    return json.dumps(response)


def start_game(user_id):
    global GAME_WORDS
    connection = sqlite3.connect('data/words.db')
    cursor = connection.cursor()
    words = cursor.execute("""SELECT * FROM words ORDER BY RANDOM() LIMIT 10""").fetchall()
    GAME_WORDS = [word for word in words]
    sessionStorage[user_id] = {
        'suggests': [
            "Первый вариант правильный.",
            'Второй вариант правильный.'
        ]
    }


def change_buttons(words, user_id, index):
    sessionStorage[user_id] = {
        'suggests': [
            "Первый вариант правильный.",
            'Второй вариант правильный.'
        ]
    }


def handle_dialog(req, res):
    global STARTED_GAME, WAITING_FOR_ANSWER, WORD_INDEX, COUNT
    user_id = req['session']['user_id']

    if req['session']['new']:
        # Это новый пользователь.
        # Инициализируем сессию и поприветствуем его.
        # Запишем подсказки, которые мы ему покажем в первый раз
        # Заполняем текст ответа
        res['response'][
            'text'] = 'Привет! Ты попал на орфоэпическую игру и твоя задача как можно' \
                      ' больше раз угадать правильное произношение слов. Ты готов?'
        sessionStorage[user_id] = {
            'suggests': [
                'Да.',
                'Нет'
            ]
        }
        res['response']['buttons'] = get_suggests(user_id)
        return

    # Сюда дойдем только, если пользователь не новый,
    # и разговор с Алисой уже был начат
    # Обрабатываем ответ пользователя.
    # В req['request']['original_utterance'] лежит весь текст,
    # что нам прислал пользователь
    # Если он написал 'ладно', 'куплю', 'покупаю', 'хорошо',
    # то мы считаем, что пользователь согласился.
    # Подумайте, всё ли в этом фрагменте написано "красиво"?
    if not STARTED_GAME:
        if req['request']['original_utterance'].lower() == 'да.':
            # Пользователь согласился, прощаемся.
            start_game(user_id)
            
            res['response'][
                'text'] = f"Отлично! Тогда начнем. И первой парой у нас будет: {GAME_WORDS[0][1]} и {GAME_WORDS[0][2]}"
            res['response']['buttons'] = get_suggests(user_id)
            STARTED_GAME = True
            WAITING_FOR_ANSWER = True
            return
        else:
            res['response'][
                'text'] = f"Ну и пошел ты!"
            res['response']['end_session'] = True
            return
    if STARTED_GAME:
        if WAITING_FOR_ANSWER:
            if req['request']['original_utterance'].lower() in [
                'первый вариант правильный.'
            ]:
                WORD_INDEX += 1
                COUNT += 1
                try:
                    print(WORD_INDEX)
                    res['response'][
                        'text'] = f"Ты отгадал! Твой счет: {COUNT}. Идем дальше: {GAME_WORDS[WORD_INDEX][1]} и" \
                                  f" {GAME_WORDS[WORD_INDEX][2]}"
                except IndexError:
                    res['response'][
                        'text'] = f"Ты отгадал все слова и победил!!! Мои поздравления."
                    STARTED_GAME = False
                    res['response']['end_session'] = True
            else:
                WORD_INDEX += 1
                try:
                    res['response'][
                        'text'] = f"Увы! Ты не удагал. Твой счет: {COUNT}. Идем дальше: {GAME_WORDS[WORD_INDEX][1]} и" \
                                  f" {GAME_WORDS[WORD_INDEX][2]}"
                except IndexError:
                    res['response'][
                        'text'] = f"Ты отгадал все слова и победил!!! Мои поздравления."
                    STARTED_GAME = False
                    res['response']['end_session'] = True
    return


# Функция возвращает две подсказки для ответа.
def get_suggests(user_id):
    session = sessionStorage[user_id]

    # Выбираем две первые подсказки из массива.
    suggests = [
        {'title': suggest, 'hide': True}
        for suggest in session['suggests'][:2]
    ]
    return suggests


if __name__ == '__main__':
    app.run()
