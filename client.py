import asyncio
import websockets
import json

class Player:
    def __init__(self):
        self.name = ""
        self.token = ""
        self.invie = False
        self.attempts = []

async def async_input(prompt=''):
    return await asyncio.to_thread(input, prompt)

player = Player()

async def websocket_handler(uri, send_queue):
    async with websockets.connect(uri) as websocket:
        send_task = asyncio.create_task(send_messages(websocket, send_queue))
        receive_task = asyncio.create_task(receive_messages(websocket))
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

async def send_messages(websocket, send_queue):
    while True:
        message = await send_queue.get()
        await websocket.send(message)

async def receive_messages(websocket):
    async for message in websocket:
        data = json.loads(message)
        if data["action"] == 'experiment_start':
            print("Получено приглашение. Эксперимент начался!")
            await send_confirmation(websocket, "experiment_start")
        elif data['action'] == 'result':
            print(data['message'])
            await send_confirmation(websocket, "guess_result")
        elif data['action'] == 'attempts':
            print("Ваши попытки:", data['attempts'])

async def send_confirmation(websocket, message_type):
    confirmation_message = json.dumps({
        "action": "confirm_receipt",
        "message_type": message_type
    })
    await websocket.send(confirmation_message)

async def input_handler(send_queue):
    player.name = await async_input("Введите имя:\n")
    data = {
        "action": "connect",
        "name": player.name
    }
    message = json.dumps(data)
    await send_queue.put(message)

    while True:
        print("Доступные действия:")
        print("1. Сделать предположение")
        print("2. Посмотреть все свои попытки")
        print("3. Выйти")
        
        user_input = await async_input("Введите номер действия: ")
        
        if user_input == "1":
            guess = await async_input("Введите ваше предположение (число от 1 до 100): ")
            player.attempts.append(guess)
            data = {
                "action": "guess",
                "guess": guess
            }
            await send_queue.put(json.dumps(data))
        elif user_input == "2":
            attempts_message = json.dumps({
                "action": "get_attempts"
            })
            await send_queue.put(attempts_message)
        elif user_input == "3":
            exit(1)

async def main():
    uri = "ws://localhost:8765"
    send_queue = asyncio.Queue()
    websocket_task = asyncio.create_task(websocket_handler(uri, send_queue))
    input_task = asyncio.create_task(input_handler(send_queue))
    done, pending = await asyncio.wait(
        [websocket_task, input_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

asyncio.run(main())
