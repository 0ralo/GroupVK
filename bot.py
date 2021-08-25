#  Copyright (c) 2020. This bot made by 0ralo (https://vk.com/0ralo)
import logging
import random
import sys

from vkwave.bots import SimpleLongPollBot, PayloadFilter, TextFilter, Keyboard, ButtonColor, EventTypeFilter, \
	CallbackAnswer, VBMLFilter
from vkwave.types.bot_events import BotEventType
from vkwave.bots.core.dispatching.filters.builtin import PayloadContainsFilter

from models import User, Cell, Transaction, CellType, Permissions
from map import get_map
import time
import datetime
from loguru import logger
from random import randint
import json
import asyncio
import environ
import math
from string import ascii_letters

env = environ.Env()
env.read_env(".env")

logging.basicConfig(level=logging.DEBUG)

Token = env("token")
group_id = env("id")
my_id: int = 245946753
timer: int = 0
teams: dict = {"red": {"bank": randint(1, 10)}, "blue": {"bank": randint(1, 10)}}
taken = None
loop = asyncio.get_event_loop()

bot = SimpleLongPollBot(tokens=Token, group_id=group_id)


async def game():
	global teams, timer, taken, bot
	timer = time.time()
	await asyncio.sleep(10 * 60)
	bank = teams["red"]["bank"] + teams["blue"]["bank"]
	number = taken or randint(0, 1)  # 0 - blue team, 1 - red team
	taken = None
	if number == 0:
		blue_bank = teams["blue"]["bank"]
		koef = bank / blue_bank
		for i in teams["blue"]:
			if i == "bank":
				continue
			else:
				try:
					await bot.api_context.messages.send(peer_id=i, random_id=0,
					                                    message=f"Поздравляю! Синие выиграли с коэффицентом {koef}!")
				except Exception as f:
					logger.error(f)
				user = User.get(i)
				user.money += int(teams["blue"][i] * koef)
				user.save()
	else:
		red_bank = teams["red"]["bank"]
		koef = bank / red_bank
		for i in teams["red"]:
			if i == "bank":
				continue
			else:
				try:
					await bot.api_context.messages.send(peer_id=i, random_id=0,
					                                    message=f"Поздравляю! Красные выиграли с коэффицентом {koef}!")
				except Exception as f:
					logger.error(f)
				user = User.get(i)
				user.money += int(teams["red"][i] * koef)
				user.save()
	timer = 0
	teams = {"red": {"bank": randint(1, 10)}, "blue": {"bank": randint(1, 10)}}
	logger.info("Creating new task_asyncio game")
	loop.create_task(game(), name="game")


async def automatics():
	await asyncio.sleep(60 * 60)
	# TODO some mech
	for i in Cell.select():
		v = i.visit


async def moving_to_cell(event, x, y, permanent=False, another_user=None):
	if another_user:
		user1 = User.get(id=another_user)
	else:
		user1 = User.get(id=event.object.object.message.peer_id)
	start_x, start_y = user1.person_x, user1.person_y
	distance = math.sqrt((x - start_x) ** 2 + (y - start_y) ** 2)
	if permanent and User.get(id=event.object.object.message.peer_id).permissions.id > 1:
		user1.person_x = x
		user1.person_y = y
		user1.save()
		await event.answer(f"Перенесено на {x}:{y}")
		return
	await event.answer(f"Путешествие займет {int(distance)} сек, вы в пути")
	await asyncio.sleep(int(distance))
	user2 = User.get(id=event.object.object.message.peer_id)
	if user1.person_x == user2.person_x and user1.person_y == user2.person_y:
		user2.person_x = x
		user2.person_y = y
		user2.save()
		await event.answer("Путешествие прошло упешно")


@bot.message_handler(VBMLFilter("путешествие <x:int> <y:int>") | VBMLFilter("перенос <x:int> <y:int>") | VBMLFilter(
	"перенос <x:int> <y:int> <id:int>"))
async def walking(event: bot.SimpleBotEvent):
	data = event["vmbl_data"]
	x, y = data["x"], data["y"]
	another_user = None
	if data.get("id", False):
		another_user = data.get("id")
	await event.answer(f"Вы начинаете поход в [{x}:{y}]")
	await moving_to_cell(event, x, y, "перенос" in event.object.object.message.text, another_user)


async def signing_transaction(tran):
	user_to_pay = User.get_or_none(id=tran.peer_id)
	user_from_pay = User.get(id=tran.from_id)
	garant = User.get(id=tran.garant.id)
	comission = tran.comission
	sum = tran.amount
	user_from_pay.money -= int(sum * (1 + (comission / 100)))
	user_from_pay.save()
	user_to_pay.money += sum
	user_to_pay.save()
	garant.money += int(sum * comission / 100)
	garant.save()
	await bot.api_context.messages.send(user_ids=[user_to_pay.id, user_from_pay.id],
	                                    message="Транзакция выполнена успешно",
	                                    random_id=0)


async def hasher(length):
	hash = ""
	for i in range(length):
		hash += ascii_letters[random.randint(0, len(ascii_letters) - 1)]
	return hash


@bot.message_handler(PayloadContainsFilter("sign_transaction"))
async def person_ready(event: bot.SimpleBotEvent):
	payload = json.loads(event.object.object.message.payload)
	trans, created = Transaction.get_or_create(hash=payload["hash"], amount=payload["sum"],
	                                           garant_id=payload["sign_transaction"])
	if created:
		trans.time = time.time()
		trans.comission = payload["comission"]
		trans.save()
	else:
		logger.error("Something went wrong")
		return
	keyboard = Keyboard(inline=True)
	success = randint(0, 3)
	for i in range(4):
		small_hash = await hasher(8)
		keyboard.add_text_button(small_hash,
		                         payload={"hash": payload["hash"], "success": i == success, "from": payload["from"],
		                                  "to": payload["to"]})
		if i == success:
			correct = small_hash
		keyboard.add_row()
	keyboard.add_text_button("Отменить",color=ButtonColor.NEGATIVE, payload={"hash": payload["hash"], "success": "canceled", "from": payload["from"],
		                                  "to": payload["to"]})
	await event.api_ctx.messages.send(message="Выберите вариант который совпадает с получателем",
	                                  keyboard=keyboard.get_keyboard(),
	                                  random_id=0,
	                                  peer_id=payload["from"])
	logger.info(correct)
	keyboard = Keyboard(inline=True)
	success = randint(0, 3)
	for i in range(4):
		small_hash = await hasher(8)
		keyboard.add_text_button(small_hash if i != success else correct,
		                         payload={"hash": payload["hash"], "success": i == success, "from": payload["from"],
		                                  "to": payload["to"]})
		keyboard.add_row()
	keyboard.add_text_button("Отменить",color=ButtonColor.NEGATIVE, payload={"hash": payload["hash"], "success": "canceled", "from": payload["from"],
		                                  "to": payload["to"]})
	await event.api_ctx.messages.send(message="Выберите вариант который совпадает с отправителем",
	                                  keyboard=keyboard.get_keyboard(),
	                                  random_id=0,
	                                  peer_id=payload["to"])


@bot.message_handler(PayloadContainsFilter("hash"))
async def hash_signing(event: bot.SimpleBotEvent):
	payload = json.loads(event.object.object.message.payload)
	tran = Transaction.get(hash=payload["hash"])
	if tran.success is False:
		await event.answer("Транзакция устарела или не удалась")
		return
	if isinstance(payload["success"], bool):
		if payload["success"]:
			...
		else:
			tran.success = False
			tran.peer_id = payload["to"]
			tran.from_id = payload["from"]
			tran.save()
			await event.api_ctx.messages.send(user_ids=[tran.peer_id, tran.from_id],
			                                  message="Транзакция не выполнена",
			                                  random_id=0)
			return
	elif isinstance(payload["success"], str):
		tran.success = False
		tran.peer_id = payload["to"]
		tran.from_id = payload["from"]
		tran.save()
		await event.api_ctx.messages.send(user_ids=[tran.peer_id, tran.from_id],
		                                  message="Транзакция отменена",
		                                  random_id=0)
		return
	else:
		logger.error("error here")

	if event.object.object.message.peer_id == payload["to"]:
		tran.peer_id = event.object.object.message.peer_id
		tran.save()
	if event.object.object.message.peer_id == payload["from"]:
		tran.from_id = event.object.object.message.peer_id
		tran.save()
	if tran.peer_id == payload["to"] and tran.from_id == payload["from"]:
		tran.success = True
		tran.save()
		await signing_transaction(tran)


async def get_garants(data):
	garants = (
		Transaction
			.select(Transaction.garant, Transaction.comission)
			.order_by(Transaction.comission)
			.limit(5)
			.distinct()
	)
	keyboard = Keyboard(inline=True)
	for num, garant in enumerate(garants):
		data["sign_transaction"] = garant.garant.id
		data["comission"] = garant.comission
		data["hash"] = await hasher(64)
		user = await bot.api_context.users.get(user_ids=garant.garant.id)
		keyboard.add_text_button(f"[{num + 1}] {user.response[0].first_name} комиссия:{garant.comission}%",
		                         payload=data)
		keyboard.add_row()
	keyboard.add_text_button("Зачем?", payload={"why": "transaction"})
	return keyboard.get_keyboard()


@bot.message_handler(PayloadFilter({"why": "transaction"}))
async def why_transaction(event: bot.SimpleBotEvent):
	await event.answer("При передаче денег вам обязательно нужно указать довренное лицо, которое подпишет перевод("
	                   "автоматически) и заберет себе комиссию.")


@bot.message_handler(VBMLFilter("передать <id:int> <sum:int>"))
async def transfer_request(event: bot.SimpleBotEvent):
	user = User.get(id=event.object.object.message.peer_id)
	data = event["vmbl_data"]
	if user.money < data["sum"] * 2:
		await event.answer("Ваш баланс должен быть как минимум в два раза больше перевода")
		return
	if data["sum"] < 0:
		await event.answer("Сумма должна быть положительным числом")
		return
	if User.get_or_none(id=data["id"]) is None:
		await event.answer("Пользователя не существует")
		return
	if not User.get(id=data["id"]).ready_for_transactions:
		await event.answer("У пользователя отключены переводы")
		return
	if not user.ready_for_transactions:
		await event.answer("У вас отключены переводы")
		return
	if data["id"] == user.id:
		await event.answer("Нельзя отправить перевод себе")
		return
	data = {"to": data["id"], "from": event.object.object.message.peer_id, "sum": data["sum"]}
	keyboard = await get_garants(data)
	await event.answer("Выберите гаранта транзакции (обязательно)", keyboard=keyboard)


@bot.message_handler(PayloadFilter({"menu": "bonus"}))
async def bonus(event: bot.SimpleBotEvent):
	user = User.get(id=event.object.object.message.peer_id)
	if (datetime.datetime.now() - user.bonus_time).days > 0:
		mn = randint(100, 1000)
		user.money += mn
		user.bonus_time = datetime.datetime.now()
		user.save()
		await event.answer(f"Вы получили {mn} денег, приходите через 24 часа")
		await menu(event)


@bot.message_handler(TextFilter("меню") | TextFilter("menu") | PayloadFilter({"city": "back"}))
async def menu(event: bot.SimpleBotEvent):
	user, _ = User.get_or_create(id=event.object.object.message.peer_id)
	keyboard = Keyboard()
	keyboard.add_text_button("Идти в город", payload={"menu": "city"})
	keyboard.add_row()
	keyboard.add_text_button("Профиль", payload={"profile": "profile"}, color=ButtonColor.POSITIVE)
	if (datetime.datetime.now() - user.bonus_time).days > 0:
		keyboard.add_text_button("Бонус", payload={"menu": "bonus"}, color=ButtonColor.POSITIVE)
	keyboard.add_text_button("Игра \"Команды\"", payload={"menu": "game"}, color=ButtonColor.POSITIVE)
	keyboard.add_row()
	keyboard.add_text_button("Настройки", payload={"menu": "settings"}, color=ButtonColor.SECONDARY)
	if user.permissions.name in ["admin", "owner"]:
		keyboard.add_row()
		keyboard.add_text_button("Админ панель", payload={"admin": "panel"}, color=ButtonColor.NEGATIVE)
	await event.answer("Вы в меню", keyboard=keyboard.get_keyboard())


@bot.message_handler(
	PayloadContainsFilter("profile") | (PayloadContainsFilter("profile") & PayloadContainsFilter("page")))
async def profile(event: bot.SimpleBotEvent):
	user = User.get(id=event.object.object.message.peer_id)
	keyboard = Keyboard(inline=True)
	payload = json.loads(event.object.object.message.payload)
	page = payload.get("page", 1)
	if page < 1:
		page = 1
	cells = (Cell
	         .select()
	         .where(Cell.owner == user)
	         .limit(4)
	         .offset((page - 1) * 4))
	for j in cells:
		keyboard.add_text_button(f"[{j.x}:{j.y}] type={j.type.name}")
		keyboard.add_row()
	keyboard.add_text_button("<-", payload={"profile": 1, "page": page - 1})
	keyboard.add_text_button(page)
	keyboard.add_text_button("->", payload={"profile": 1, "page": page + 1})
	await event.answer(f"__PROFILE__\n"
	                   f"ID: {user.id}\n"
	                   f"Деньги: {user.money}\n",
	                   keyboard=keyboard.get_keyboard())


@bot.message_handler(TextFilter("тра"))
async def tra(event: bot.SimpleBotEvent):
	fl = Transaction.select()
	for i in fl:
		await event.answer(f"{i.from_id}->{i.peer_id}[{i.amount}] | success [{i.success}] | hash={i.hash}")


@bot.message_handler(PayloadFilter({"admin": "panel"}))
async def admin_panel(event: bot.SimpleBotEvent):
	user = User.get(id=event.object.object.message.peer_id)
	if user.permissions.name in ["admin", "owner"]:
		keyboard = Keyboard()
		keyboard.add_text_button("ADMIN PANEL 3.0", color=ButtonColor.POSITIVE)
		keyboard.add_row()
		keyboard.add_text_button("Игроки", payload={"admin": "get_user_list", "page": "1"})
		keyboard.add_text_button("Эвенты", payload={"admin": "get_event_list"})
		keyboard.add_row()
		keyboard.add_text_button("...", payload={"0": "0"})
		keyboard.add_text_button("...", payload={"0": "0"})
		keyboard.add_row()
		keyboard.add_text_button("Назад", color=ButtonColor.POSITIVE, payload={"city": "back"})
		await event.answer("Вы в админ панеле", keyboard=keyboard.get_keyboard())


@bot.message_handler(PayloadContainsFilter("admin") & PayloadContainsFilter("page") & ~PayloadContainsFilter("new"))
async def get_users_admin_panel(event: bot.SimpleBotEvent):
	page = int(json.loads(event.object.object.message.payload)["page"])
	users = (User
	         .select()
	         .limit(6)
	         .offset((page - 1) * 6))
	keyboard = Keyboard()
	message = "Страница {0}\n".format(page)
	for num, usr in enumerate(users):
		user = await event.api_ctx.users.get(user_ids=usr.id)
		message += f"[{num + 1}] [id{user.response[0].id}|{user.response[0].first_name} {user.response[0].last_name}]\n"
		keyboard.add_text_button(f"[{num + 1}] {user.response[0].id}",
		                         payload={"admin": "manipulate", "used_page_to_exit": page, "id": usr.id})
		keyboard.add_row()
	keyboard.add_text_button("<--", payload={"admin": "", "page": page - 1})
	keyboard.add_text_button(str(page))
	keyboard.add_text_button("-->", payload={"admin": "", "page": page + 1})
	keyboard.add_row()
	keyboard.add_text_button("Назад", color=ButtonColor.NEGATIVE, payload={"admin": "panel"})
	await event.answer(message, keyboard=keyboard.get_keyboard())


@bot.message_handler(
	PayloadContainsFilter("admin") & PayloadContainsFilter("used_page_to_exit") & PayloadContainsFilter("id"))
async def admin_panel_manipulate_user(event: bot.SimpleBotEvent, payload=None):
	payload = payload or json.loads(event.object.object.message.payload)
	user_data = (await event.api_ctx.users.get(user_ids=payload["id"])).response[0]
	user = User.get(id=int(payload["id"]))
	permissions = list(Permissions.select())
	permissions = list(map(lambda x: x.name, permissions))
	keyboard = Keyboard()
	keyboard.add_text_button(f"{user_data.first_name} | {payload['id']}",
	                         color=ButtonColor.NEGATIVE if user.banned else ButtonColor.POSITIVE,
	                         payload={"admin": "action", "banorpardon": int(payload["id"])})
	keyboard.add_row()
	i = permissions.index(user.permissions.name)
	if i - 1 < 0:
		keyboard.add_text_button("###", color=ButtonColor.NEGATIVE)
	else:
		keyboard.add_text_button(permissions[i - 1], color=ButtonColor.NEGATIVE,
		                         payload={"admin": "action", "downgrade": int(payload["id"]), "new": permissions[i - 1],
		                                  "page": payload["used_page_to_exit"]})

	if i + 1 >= len(permissions):
		keyboard.add_text_button("###", color=ButtonColor.POSITIVE)
	else:
		keyboard.add_text_button(permissions[i + 1], color=ButtonColor.POSITIVE,
		                         payload={"admin": "action", "upgrade": int(payload["id"]), "new": permissions[i + 1],
		                                  "page": payload["used_page_to_exit"]})
	keyboard.add_row()
	keyboard.add_text_button("Назад", color=ButtonColor.NEGATIVE,
	                         payload={"admin": "action", "page": payload["used_page_to_exit"]})
	await event.answer("1", keyboard=keyboard.get_keyboard())


@bot.message_handler(
	PayloadContainsFilter("admin") & (PayloadContainsFilter("downgrade") | PayloadContainsFilter("upgrade")))
async def user_grade(event: bot.SimpleBotEvent):
	payload = json.loads(event.object.object.message.payload)
	user = User.get(id=payload.get("downgrade", None) or payload.get("upgrade", None))
	user.permissions = Permissions.get(name=payload["new"])
	user.save()
	await event.answer(f"Пользователь изменен на " + user.permissions.name)
	await admin_panel_manipulate_user(event, {"id": payload.get("downgrade", None) or payload.get("upgrade", None),
	                                          "used_page_to_exit": payload["page"]})


@bot.message_handler(PayloadFilter({"menu": "city"}) | PayloadFilter({"go": "back"}))
async def city(event: bot.SimpleBotEvent, child: bool = False):
	keyboard = Keyboard()
	user = User.get(id=event.object.object.message.peer_id) if not child else User.get(id=event.object.object.peer_id)
	map = await get_map(user)
	for i in range(len(map)):
		for j in range(len(map[i])):
			cell, color = "#", ButtonColor.PRIMARY
			if map[i][j] == -1:
				cell = "X"
				color = ButtonColor.NEGATIVE
			elif map[i][j] != -1:
				cell, color = map[i][j], ButtonColor.PRIMARY
			keyboard.add_text_button(cell, color=color)
		keyboard.add_row()
	if Cell.get_or_none(x=user.person_x, y=user.person_y):
		map = Cell.get(x=user.person_x, y=user.person_y)
		if map.type.name == "Дом" and user.id == map.owner_id:
			keyboard.add_text_button(f"Войти в {map.name}", ButtonColor.POSITIVE,
			                         {"enter": "1", "x": map.x, "y": map.y})
		elif map.type.name == "Дом" and user.id != map.owner_id:
			...
		else:
			keyboard.add_text_button(f"Войти в {map.name}", ButtonColor.POSITIVE,
			                         {"enter": "1", "x": map.x, "y": map.y})
		keyboard.add_row()

	if user.permissions.name in ["admin", "builder", "moder", "owner"]:
		keyboard.add_callback_button("1", payload={"build": "1"})
		keyboard.add_callback_button("2", payload={"build": "2"})
		keyboard.add_callback_button("3", payload={"build": "3"})
		keyboard.add_callback_button("4", payload={"build": "4"})
		keyboard.add_row()
		keyboard.add_text_button("Информация", payload={"admin": "info"})
		keyboard.add_callback_button("X", payload={"build": "-1"})
		keyboard.add_row()
	keyboard.add_callback_button("⬅", payload={"move": "left"})
	keyboard.add_callback_button("⬆", payload={"move": "up"})
	keyboard.add_callback_button("⬇", payload={"move": "down"})
	keyboard.add_callback_button("➡", payload={"move": "right"})
	keyboard.add_row()
	keyboard.add_text_button("Выйти", payload={"city": "back"})
	await (event.answer("_", keyboard=keyboard.get_keyboard())
	       if not child else
	       event.api_ctx.messages.send(
		       peer_id=event.object.object.peer_id,
		       random_id=0, message=f"Ваши координаты: [{user.person_x}:{user.person_y}]",
		       keyboard=keyboard.get_keyboard()))


@bot.handler(EventTypeFilter(BotEventType.MESSAGE_EVENT), PayloadContainsFilter("move"))
async def move(event: bot.SimpleBotEvent):
	move = event.object.object.payload["move"]
	user = User.get(id=event.object.object.peer_id)
	if move == "right":
		if user.person_y + 1 > 1000:
			await event.callback_answer(event_data=CallbackAnswer.show_snackbar("Вы не можете покинуть карту"))
		else:
			user.person_y += 1
	elif move == "left":
		if user.person_y - 1 < 0:
			await event.callback_answer(event_data=CallbackAnswer.show_snackbar("Вы не можете покинуть карту"))
		else:
			user.person_y -= 1
	elif move == "up":
		if user.person_x - 1 < 0:
			await event.callback_answer(event_data=CallbackAnswer.show_snackbar("Вы не можете покинуть карту"))
		else:
			user.person_x -= 1
	else:
		if user.person_x + 1 > 1000:
			await event.callback_answer(event_data=CallbackAnswer.show_snackbar("Вы не можете покинуть карту"))
		else:
			user.person_x += 1
	user.save()
	await city(event, True)


@bot.handler(bot.event_type_filter(BotEventType.MESSAGE_EVENT), PayloadContainsFilter("build"))
async def build(event: bot.SimpleBotEvent):
	build = CellType(id=int(event.object.object.payload["build"]))
	user = User.get(id=event.object.object.peer_id)
	if build.id in range(0, 5):
		name = {1: "Дом",
		        2: "Продуктовый",
		        3: "Услуги и я",
		        4: "Бизнес",
		        5: ""}[build.id]
		if not Cell.get_or_none(x=user.person_x, y=user.person_y):
			Cell.create(x=user.person_x, y=user.person_y, type=build, owner_id=user, name=name)
			await event.api_ctx.messages.send(message=f"id = {Cell.get(x=user.person_x, y=user.person_y).id}",
			                                  peer_id=event.object.object.peer_id, random_id=0)
		else:
			await event.api_ctx.messages.send(message=f"already exist",
			                                  peer_id=event.object.object.peer_id, random_id=0)
	else:
		Cell.get(x=user.person_x, y=user.person_y).delete_instance()
	await city(event, True)


@bot.message_handler(VBMLFilter("ставка <bet> <amount:int>"))
async def betting(event: bot.SimpleBotEvent):
	vmbl_data = event["vmbl_data"]
	bet: str = vmbl_data["bet"]
	amount = vmbl_data["amount"]
	user = User.get(id=event.object.object.message.peer_id)

	if bet.lower() == "красное":
		if event.object.object.message.peer_id in teams["blue"]:
			await event.answer("Вы не можете ставить на 2 команды одновременно")
		elif event.object.object.message.peer_id in teams["red"]:
			if user.money >= amount:
				user.money -= amount
				teams["red"]["bank"] += amount
				teams["red"][event.object.object.message.peer_id] += amount
				user.save()
				await event.answer(f"Вы поставили {amount} на красное")
			else:
				await event.answer("У вас не хватает денег")
		else:
			if user.money >= amount:
				user.money -= amount
				teams["red"]["bank"] += amount
				teams["red"][event.object.object.message.peer_id] = amount
				user.save()
				await event.answer(f"Вы поставили {amount} на красное")
			else:
				await event.answer("У вас не хватает денег")
	elif bet.lower() == "синее":
		if event.object.object.message.peer_id in teams["red"]:
			await event.answer("Вы не можете ставить на 2 команды одновременно")
		elif event.object.object.message.peer_id in teams["blue"]:
			if user.money >= amount:
				user.money -= amount
				teams["blue"]["bank"] += amount
				teams["blue"][event.object.object.message.peer_id] += amount
				user.save()
				await event.answer(f"Вы поставили {amount} на синее")
			else:
				await event.answer("У вас не хватает денег")
		else:
			if user.money >= amount:
				user.money -= amount
				teams["blue"]["bank"] += amount
				teams["blue"][event.object.object.message.peer_id] = amount
				user.save()
				await event.answer(f"Вы поставили {amount} на синее")
			else:
				await event.answer("У вас не хватает денег")
	else:
		await event.answer(f"Неопределенная команда : {bet} доступные команды: красное или синее")


@bot.message_handler(VBMLFilter("название <n:int> <name>"))
async def name_building(event: bot.SimpleBotEvent):
	vmbl_data = event["vmbl_data"]
	name = vmbl_data["name"]
	num = vmbl_data["n"]
	if Cell.get_or_none(id=num):
		if Cell.get(id=num).owner_id == event.object.object.message.peer_id:
			cell = Cell.get(id=num)
			cell.name = name
			cell.save()
			await event.answer("Вы изменили название своей компании")
		else:
			await event.answer("Это не ваша собственность")
	else:
		await event.answer("Такой недвижимости не зарегестрированно")


@bot.message_handler(PayloadFilter({"menu": "game"}))
async def game_menu(event: bot.SimpleBotEvent):
	bank = teams["red"]["bank"] + teams["blue"]["bank"]
	await event.answer(
		f"Красные[{round(bank / teams['red']['bank'], 2)}] : Синие[{round(bank / teams['blue']['bank'], 2)}]\n"
		f"Осталось времени : {int((10 * 60) - (time.time() - timer))} сек")


@bot.message_handler(PayloadContainsFilter("enter"))
async def enter_building(event: bot.SimpleBotEvent):
	x = json.loads(event.object.object.message.payload)["x"]
	y = json.loads(event.object.object.message.payload)["y"]
	map = Cell.get(x=x, y=y)
	user = User.get(id=event.object.object.message.peer_id)
	if map.type.name == "Дом":
		keyboard = Keyboard()
		keyboard.add_text_button("Отдохнуть", color=ButtonColor.POSITIVE, payload={"home": "relax"})
		keyboard.add_row()
		keyboard.add_text_button("Список друзей", color=ButtonColor.SECONDARY, payload={"home": "friends"})
		keyboard.add_row()
		keyboard.add_text_button("Выйти", color=ButtonColor.NEGATIVE, payload={"go": "back"})
		await event.answer(f"Вы вошли в {map.name}", keyboard=keyboard.get_keyboard())
	elif map.type.name == "Продуктовый":
		keyboard = Keyboard()
		if user.work != map.id:
			keyboard.add_text_button("Устроиться на работу", color=ButtonColor.POSITIVE,
			                         payload={"shop_food": "work_here"})
		else:
			keyboard.add_text_button("Уволиться", color=ButtonColor.NEGATIVE, payload={"shop_food": "go_away"})
		keyboard.add_row()
		keyboard.add_text_button("Выйти", color=ButtonColor.NEGATIVE, payload={"go": "back"})
		await event.answer(f"Вы вошли в {map.name}", keyboard=keyboard.get_keyboard())
	elif map.type.name == "Услуги и я":
		keyboard = Keyboard()
		keyboard.add_text_button("Недвижимость", color=ButtonColor.SECONDARY, payload={"mfc": "buildings"})
		keyboard.add_row()
		keyboard.add_text_button("Транспорт", color=ButtonColor.SECONDARY, payload={"mfc": "cars"})
		keyboard.add_row()
		keyboard.add_text_button("Документы персоны", color=ButtonColor.SECONDARY, payload={"mfc": "docs"})
		keyboard.add_row()
		keyboard.add_text_button("Выйти", color=ButtonColor.NEGATIVE, payload={"go": "back"})
		await event.answer(f"Вы вошли в {map.name}", keyboard=keyboard.get_keyboard())
	elif map.type.name == "Бизнес":
		keyboard = Keyboard()
		keyboard.add_text_button(f"Работать на бизнес {map.name}", color=ButtonColor.SECONDARY,
		                         payload={"business": "work"})
		keyboard.add_row()
		keyboard.add_text_button("Перекупить бизнес", color=ButtonColor.SECONDARY, payload={"business": "rebuy"})
		keyboard.add_row()
		keyboard.add_text_button("Купить акции бизнеса", color=ButtonColor.SECONDARY, payload={"mfc": "docs"})
		keyboard.add_row()
		keyboard.add_text_button("Выйти", color=ButtonColor.NEGATIVE, payload={"go": "back"})
		await event.answer(f"Вы вошли в {map.name}", keyboard=keyboard.get_keyboard())
	else:
		...


# smt went wrong


@bot.message_handler(PayloadFilter({"admin": "info"}))
async def get_info(event: bot.SimpleBotEvent):
	user = User.get_or_none(id=event.object.object.message.peer_id)
	map = Cell.get_or_none(x=user.person_x, y=user.person_y)
	if map:
		await event.answer(f"___{map.name}___\nid: {map.id}\nowner: {map.owner.id}")
	else:
		await event.answer("Эта клетка пуста")


@bot.message_handler(VBMLFilter("выиграют <team>"))
async def makeWin(event: bot.SimpleBotEvent):
	if event.object.object.message.peer_id == my_id:
		if event["vmbl_data"]["team"].lower() in "красноекрасныйкрасныекраснаякрасн":
			taken = 1
			await event.answer("Выиграет красная команда")
		elif event["vmbl_data"]["team"].lower() in "синеесинийсиниесиняясин":
			taken = 0
			await event.answer("Выиграет синяя команда")


@bot.message_handler(PayloadFilter({"menu": "settings"}))
async def settings(event: bot.SimpleBotEvent):
	user = User.get(id=event.object.object.message.from_id)
	kb = Keyboard()
	kb.add_text_button("3x3", color=(ButtonColor.POSITIVE if user.map_size == "3x3" else ButtonColor.NEGATIVE),
	                   payload={"settings": "1", "map": "3x3"})
	kb.add_text_button("5x5", color=(ButtonColor.POSITIVE if user.map_size == "5x5" else ButtonColor.NEGATIVE),
	                   payload={"settings": "1", "map": "5x5"})
	kb.add_row()
	kb.add_text_button(f"Переводы {'разрешены' if user.ready_for_transactions else 'запрещены'}",
	                   color=ButtonColor.POSITIVE if user.ready_for_transactions else ButtonColor.NEGATIVE,
	                   payload={"settings": "2", "change_transaction_status": "1"})
	kb.add_row()
	kb.add_text_button("Назад", color=ButtonColor.NEGATIVE, payload={"city": "back"})
	await event.answer("Меню настроек:\n1)Размер карты\n2)Отображаемый идентификатор", keyboard=kb.get_keyboard())


@bot.message_handler(PayloadContainsFilter("settings") & PayloadContainsFilter("change_transaction_status"))
async def settings_transaction(event: bot.SimpleBotEvent):
	user = User.get(id=event.object.object.message.peer_id)
	if user.ready_for_transactions:
		user.ready_for_transactions = False
	else:
		user.ready_for_transactions = True
	user.save()
	await settings(event)


@bot.message_handler(PayloadContainsFilter("settings") & PayloadContainsFilter("map"))
async def field(event: bot.SimpleBotEvent):
	user = User.get(id=event.object.object.message.from_id)
	user.map_size = json.loads(event.object.object.message.payload)["map"]
	user.save()
	await settings(event)


loop.create_task(game())
if __name__ == '__main__':
	bot.run_forever(loop=loop)
