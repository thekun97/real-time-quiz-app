import json
import time
import random
import asyncio
import socketio
import threading
from redis_client import redis_client, pubsub
from aiohttp import web

from questions import quiz_questions

sio = socketio.AsyncServer(
    cors_allowed_origins=[
        'http://localhost:5173',
    ]
)
app = web.Application()
sio.attach(app)

connection = redis_client.ping()
print("Redis Connected !!!", connection)

loop = asyncio.get_event_loop()

async def index(request):
    return web.Response(text="Hello world !")

async def health(request):
    return web.Response(text="Health Ok !")

async def handle_message(message):
    data = json.loads(message['data'])
    if data['event'] == 'player_join':
        payload = data['payload']
        sid = payload['sid']
        room = payload['room']
        name = payload['name']

        room_data = await redis_client.get(room)
        if room_data:
            room_data = json.loads(room_data)

        await sio.enter_room(sid, room)
        await sio.emit('message', f'{name} has joined the game!', room=room)

        room_data['players'].append({'id': sid, 'name': name})
        await redis_client.set(room, json.dumps(room_data))

        if room_data['currentQuestion'] is None:
            await ask_new_question(room)

async def sub_room(room):
    await pubsub.subscribe(room)
    async for message in pubsub.listen():
        if message['type'] == 'message':
            await handle_message(message)

async def ask_new_question(room):

    room_data = await redis_client.get(room)
    if room_data:
        room_data = json.loads(room_data)
    else:
        return

    if len(room_data['players']) == 0:
        await redis_client.delete(room)
        return

    question = random.choice(quiz_questions)
    correct_answer_index = next(
        (index for (index, answer) in enumerate(question['answers']) if answer['correct']),
        None
    )

    room_data['currentQuestion'] = question
    room_data['correctAnswer'] = correct_answer_index
    room_data['shouldAskNewQuestion'] = True

    await redis_client.set(room, json.dumps(room_data))

    await sio.emit('newQuestion', {
        'question': question['question'],
        'answers': [answer['text'] for answer in question['answers']],
        'timer': 10
    }, room=room)

    async def timeout():
        update_score_room_data = await redis_client.get(room)
        if update_score_room_data:
            update_score_room_data = json.loads(update_score_room_data)
        else:
            return

        await sio.emit('answerResult', {
            'playerName': 'No one',
            'isCorrect': False,
            'correctAnswer': room_data['correctAnswer'],
            'scores': [{'name': player['name'], 'score': player.get('score', 0)} for player in update_score_room_data['players']]
        }, room=room)

        await ask_new_question(room)

    await asyncio.sleep(10)
    await timeout()


@sio.event
def connect(sid, environ):
    print(f"A user connected: {sid}")

@sio.event
async def join_room(sid, room, name):
    room_data = await redis_client.get(room)
    if room_data:
        room_data = json.loads(room_data)
        await redis_client.publish(room, json.dumps({
            'event': 'player_join',
            'payload': {
                'sid': sid,
                'room': room,
                'name': name
            }
        }))
    else:
        await sio.enter_room(sid, room)
        await sio.emit('message', f'{name} has joined the game!', room=room)
        room_data = {
            'players': [],
            'currentQuestion': None,
            'correctAnswer': None,
            'questionTimeout': None,
            'shouldAskNewQuestion': True,
        }
        asyncio.create_task(sub_room(room))

        room_data['players'].append({'id': sid, 'name': name})
        await redis_client.set(room, json.dumps(room_data))

        if room_data['currentQuestion'] is None:
            await ask_new_question(room)


@sio.event
async def submit_answer(sid, room, answer_index):
    room_data = await redis_client.get(room)
    if room_data:
        room_data = json.loads(room_data)
    else:
        return

    current_player = next((player for player in room_data['players'] if player['id'] == sid), None)

    if current_player:
        correct_answer = room_data['correctAnswer']
        is_correct = correct_answer is not None and correct_answer == answer_index
        current_player['score'] = (current_player.get('score', 0) + 1) if is_correct else (current_player.get('score', 0) - 1)
        
        await redis_client.set(room, json.dumps(room_data))

        new_score_room_data = await redis_client.get(room)
        if new_score_room_data:
            new_score_room_data = json.loads(new_score_room_data)

        await sio.emit('answerResult', {
            'playerName': current_player['name'],
            'isCorrect': is_correct,
            'correctAnswer': room_data['correctAnswer'],
            'scores': [{'name': player['name'], 'score': player.get('score', 0)} for player in new_score_room_data['players']]
        }, room=room)

        winning_threshold = 5
        winner = next((player for player in room_data['players'] if player.get('score', 0) >= winning_threshold), None)

        if winner:
            await sio.emit('gameOver', {'winner': winner['name']}, room=room)
            await redis_client.delete(room)


@sio.event
async def disconnect(sid):
    keys = await redis_client.keys('*')
    for key in keys:
        room = key
        room_data = await redis_client.get(room)
        if room_data:
            room_data = json.loads(room_data)
            room_data['players'] = [player for player in room_data['players'] if player['id'] != sid]
            if len(room_data['players']) == 0:
                await redis_client.delete(room)

    print(f"A user disconnected: {sid}")


app.router.add_get('/', index)
app.router.add_get('/health', index)

if __name__ == '__main__':
    web.run_app(app)