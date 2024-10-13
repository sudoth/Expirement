import asyncio
import websockets
import json
import random

async def async_input(prompt=''):
    return await asyncio.to_thread(input, prompt)

class ExperimentServer:
    def __init__(self):
        self.clients = {}
        self.attempts = {}
        self.leaders = {}
        self.experiment_started = False
        self.correct_number = None
        self.delivery_confirmations = {}

    async def handle_client(self, websocket, path):
        client_id = f"client_{len(self.clients) + 1}"
        self.clients[client_id] = websocket
        self.attempts[client_id] = {"guessed": False, "attempts": [], "correct_guesses": 0}
        self.delivery_confirmations[client_id] = {"experiment_start": False, "guess_result": False}
        print(f"Клиент {client_id} подключен.")

        try:
            async for message in websocket:
                data = json.loads(message)

                if data['action'] == 'guess':
                    await self.process_guess(client_id, data['guess'])
                elif data['action'] == 'start_experiment':
                    await self.start_experiment()
                elif data['action'] == 'confirm_receipt':
                    await self.process_confirmation(client_id, data['message_type'])
                elif data['action'] == 'get_attempts':
                    await self.send_attempts(client_id)
        except websockets.ConnectionClosed:
            print(f"Клиент {client_id} отключен.")
        finally:
            del self.clients[client_id]
            del self.attempts[client_id]

    async def process_guess(self, client_id, guess):
        guess = int(guess)
        self.attempts[client_id]["attempts"].append(guess)

        print(f"\nКлиент {client_id} угадал: {guess}, загаданное число: {self.correct_number}")

        if guess == self.correct_number:
            response = {"action": "result", "message": "\nУгадано!"}
            self.attempts[client_id]["guessed"] = True
            self.attempts[client_id]["correct_guesses"] += 1
            self.leaders[client_id] = len(self.attempts[client_id]["attempts"])
        elif guess < self.correct_number:
            response = {"action": "result", "message": "\nЧисло меньше загаданного"}
        else:
            response = {"action": "result", "message": "\nЧисло больше загаданного"}

        await self.clients[client_id].send(json.dumps(response))

    async def send_attempts(self, client_id):
        attempts = self.attempts[client_id]["attempts"]
        response = {
            "action": "attempts",
            "attempts": attempts
        }
        await self.clients[client_id].send(json.dumps(response))

    async def process_confirmation(self, client_id, message_type):
        if message_type in self.delivery_confirmations[client_id]:
            self.delivery_confirmations[client_id][message_type] = True
            print(f"Клиент {client_id} подтвердил получение сообщения: {message_type}")

    async def start_experiment(self):
        self.experiment_started = True
        self.correct_number = random.randint(1, 100)
        print(f"Эксперимент начался! Загадано число: {self.correct_number}")

        for client in self.clients.values():
            await client.send(json.dumps({"action": "experiment_start", "message": "Эксперимент начался!"}))

    async def list_clients(self):
        return list(self.clients.keys())

    async def leaderboard(self):
        leaderboard_info = {}
        for client_id, data in self.attempts.items():
            guessed_status = "угадано" if data["guessed"] else "не угадано"
            leaderboard_info[client_id] = {
                "Попытки": len(data["attempts"]),
                "Статус": guessed_status,
                "Угаданные числа": data["correct_guesses"]
            }
        return leaderboard_info

    async def confirm_delivery_status(self):
        for client_id, status in self.delivery_confirmations.items():
            print(f"Клиент {client_id}: Получение эксперимента - {status['experiment_start']}, Получение ответа на угаданное число - {status['guess_result']}")

async def start_experiment(server):
    print("Начать эксперимент? (yes/no)")
    start = await async_input()
    if start == "yes":
        await server.start_experiment()

async def server_interface(server):
    while True:
        print("\n1. Начать эксперимент")
        print("2. Посмотреть список участников")
        print("3. Посмотреть таблицу лидеров")
        print("4. Проверить подтверждение получения сообщений")
        print("5. Выйти\n")

        choice = await async_input("Введите номер действия: ")

        if choice == "1":
            await start_experiment(server)
        elif choice == "2":
            print("Список участников:", await server.list_clients())
        elif choice == "3":
            leaderboard = await server.leaderboard()
            for client, info in leaderboard.items():
                print(f"{client}: {info['Попытки']} попыток, Статус: {info['Статус']}, Угаданные числа: {info['Угаданные числа']}")
        elif choice == "4":
            await server.confirm_delivery_status()
        elif choice == "5":
            print("Выход из сервера...")
            break
        else:
            print("Неверный выбор. Пожалуйста, попробуйте снова.")

async def main():
    server = ExperimentServer()
    start_server = websockets.serve(server.handle_client, "localhost", 8765)

    async with start_server:
        print("Сервер запущен. Ожидание подключения клиентов...")
        await server_interface(server)

asyncio.run(main())

