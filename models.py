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
	id = PrimaryKeyField()
	bot_id = IntegerField(default=0)
	money = BigIntegerField(default=0)
	passport = BooleanField(default=False)
	house = ForeignKeyField(House, on_delete="CASCADE", null=True)
	work = ForeignKeyField(Work, on_delete="CASCADE", null=True)
	permissions = ForeignKeyField(Permissions, on_delete="CASCADE", default=Permissions.get(id=1))
	donate_status = SmallIntegerField(default=0)
	health = IntegerField(default=100)
	person_x = IntegerField(default=100)
	person_y = IntegerField(default=100)
	map_size = CharField(default="3x3", max_length=3)
	bonus_time = DateTimeField(default=date(2020, 8, 27))
	banned = BooleanField(default=False)
	ready_for_transactions = BooleanField(default=False)

	class Meta:
		database = database


class CellType(Model):
	name = CharField(max_length=20)
	cellemoji = CharField(max_length=1, default="#")

	class Meta:
		database = database


class Cell(Model):
	id = PrimaryKeyField()
	name = CharField(max_length=20)
	x = IntegerField(null=False)
	y = IntegerField(null=False)
	owner = ForeignKeyField(User, on_delete="CASCADE")
	type = ForeignKeyField(CellType, on_delete="CASCADE")
	visits = SmallIntegerField(default=0)
	sum = BigIntegerField(default=0)

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
		database.create_tables([CellType])
		print("created")
	elif argv[1] == "migrate":
		migrate(
			# migrator.drop_column("User", "already_for_transactions"),
			migrator.add_column("CellType", "cellemoji", CellType.cellemoji)
		)
		print("migrated")


database.bind(models=[Transaction])
