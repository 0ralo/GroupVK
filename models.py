from playhouse.migrate import SqliteDatabase, SqliteMigrator, Model, CharField, IntegerField, SmallIntegerField, BigIntegerField, ForeignKeyField, DeferredForeignKey, PrimaryKeyField, BooleanField, DateTimeField, migrate
from datetime import date
from sys import argv
import time


database = SqliteDatabase("database.db")
migrator = SqliteMigrator(database)


class Permissions(Model):
	name = CharField(max_length=40)

	class Meta:
		database = database


class House(Model):
	name = CharField(max_length=20)
	x = IntegerField()
	y = IntegerField()

	class Meta:
		database = database


class Work(Model):
	name = CharField(max_length=50)
	owner = DeferredForeignKey("User", on_delete="CASCADE")
	payment = IntegerField(default=0)

	class Meta:
		database = database


class User(Model):
	id = PrimaryKeyField()  # id - primary key and user id in vk
	bot_id = IntegerField(default=0)  # id in my bot - connected to passport
	money = BigIntegerField(default=0)  # money in bot system
	passport = BooleanField(default=False)  # boolean if has passport
	house = ForeignKeyField(House, on_delete="CASCADE", null=True)  # type of house (0 - empty, 1 - flat, 2 - house, 3 - private house)
	work = ForeignKeyField(Work, on_delete="CASCADE", null=True)  # type of work(0 - empty, i - i type of work)
	permissions = ForeignKeyField(Permissions, on_delete="CASCADE", default=Permissions.get(id=1))
	donate_status = SmallIntegerField(default=0)  # status shows hom much money user spent on this bot
	health = IntegerField(default=100)  # health of player 0 - 100 if 0 game restarts to default for player
	person_x = IntegerField(default=100)  # default spawn coords.x
	person_y = IntegerField(default=100)  # default spawn cords.y map has 1000x1000
	map_size = CharField(default="3x3", max_length=3)  # map size
	bonus_time = DateTimeField(default=date(2020, 8, 27))  # time when bonus was taken last time
	banned = BooleanField(default=False)  # is user banned
	ready_for_transactions = BooleanField(default=False)

	class Meta:
		database = database


class CellType(Model):
	name = CharField(max_length=20)

	class Meta:
		database = database


class Cell(Model):
	id = PrimaryKeyField()
	name = CharField(max_length=20)
	x = IntegerField(null=False)
	y = IntegerField(null=False)
	owner = ForeignKeyField(User, on_delete="CASCADE")
	type = ForeignKeyField(CellType, on_delete="CASCADE")  # type of cell (1 - user_house(everyone can make i t), 2 - shop(user can make it and admin), 3 - casino(allways user build it) TODO(WALL, more...)
	visits = SmallIntegerField(default=0)  # how many times people visited your building
	sum = BigIntegerField(default=0)  # sum of buisness

	class Meta:
		database = database


class Transaction(Model):
	id = PrimaryKeyField()
	from_id = IntegerField(null=True)
	peer_id = IntegerField(null=True)
	time = DateTimeField(null=False, default=time.time())
	amount = IntegerField(null=True)
	garant = ForeignKeyField(User, on_delete="CASCADE")
	comission = SmallIntegerField(default=50)
	hash = CharField(max_length=64)
	success = BooleanField(null=True, default=None)

	class Meta:
		database = database


if __name__ == '__main__':
	if argv[1] == "create":
		database.create_tables([Transaction])
		print("created")
	elif argv[1] == "migrate":
		migrate(
			migrator.drop_column("User", "already_for_transactions"),
			migrator.add_column("User", "ready_for_transactions", User.ready_for_transactions)
		)
		print("migrated")


database.bind(models=[Transaction])
