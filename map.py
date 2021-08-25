from models import Cell, User


async def get_map(user: User):
	if user.map_size == "3x3":
		kb_map = [[None, None, None], [None, None, None], [None, None, None]]
		for i, x in enumerate(range(-1, 2, 1)):
			for j, y in enumerate(range(-1, 2, 1)):
				cell = Cell.get_or_none(x=user.person_x + x, y=user.person_y + y)
				kb_map[i][j] = cell.type.cellemoji if cell else "#"
				if user.person_x+x < 0 or user.person_y+y < 0 or user.person_x+x > 1000 or user.person_y+y > 1000:
					kb_map[i][j] = -1

				if i == 1 and j == 1 and kb_map[i][j] == "#":
					kb_map[i][j] = "🚶"
		return kb_map
	else:
		kb_map = [[None, None, None, None, None], [None, None, None, None, None], [None, None, None, None, None], [None, None, None, None, None], [None, None, None, None, None]]
		for i, x in enumerate(range(-2, 3, 1)):
			for j, y in enumerate(range(-2, 3, 1)):
				cell = Cell.get_or_none(x=user.person_x + x, y=user.person_y + y)
				kb_map[i][j] = cell.type.cellemoji if cell else "#"
				if user.person_x+x < 0 or user.person_y+y < 0 or user.person_x+x > 1000 or user.person_y+y > 1000:
					kb_map[i][j] = -1
				if i == 2 and j == 2 and kb_map[i][j] == "#":
					kb_map[i][j] = "🚶"
		return kb_map
