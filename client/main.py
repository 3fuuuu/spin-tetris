import random

import pygame

if False:
	from typing import TypeAlias

from screens import EndScreenData, ScreenState, draw_end_screen, draw_start_screen

COLS, ROWS = 10, 20
CELL = 24
WIDTH = COLS * CELL * 2 + 280
HEIGHT = ROWS * CELL + 60

FPS = 60
LOCK_DELAY_FRAMES = int(FPS * 0.5)
MAX_LOCK_RESETS = 10

COMBO_BONUS: dict[int, int] = {
	1: 0,
	2: 1,
	3: 1,
	4: 1,
	5: 2,
	6: 2,
	7: 3,
	8: 3,
	9: 4,
	10: 4,
	11: 5,
	12: 5,
	13: 5,
	14: 5,
	15: 5,
	16: 5,
	17: 5,
	18: 5,
	19: 5,
	20: 5,

}

PIECES: dict[str, list[list[tuple[int, int]]]] = {
	'I': [ [(0,1),(1,1),(2,1),(3,1)], [(2,0),(2,1),(2,2),(2,3)] ],
	'O': [ [(1,0),(2,0),(1,1),(2,1)] ],
	'T': [ [(1,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(2,1),(1,2)], [(0,1),(1,1),(2,1),(1,2)], [(1,0),(0,1),(1,1),(1,2)] ],
	'S': [ [(1,0),(2,0),(0,1),(1,1)], [(1,0),(1,1),(2,1),(2,2)] ],
	'Z': [ [(0,0),(1,0),(1,1),(2,1)], [(2,0),(1,1),(2,1),(1,2)] ],
	'J': [ [(0,0),(0,1),(1,1),(2,1)], [(1,0),(2,0),(1,1),(1,2)], [(0,1),(1,1),(2,1),(2,2)], [(1,0),(1,1),(0,2),(1,2)] ],
	'L': [ [(2,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(1,2),(2,2)], [(0,1),(1,1),(2,1),(0,2)], [(0,0),(1,0),(1,1),(1,2)] ],
}

COLORS: dict[str, tuple[int, int, int]] = {
	'I': (80,200,240), 'O': (240,200,80), 'T': (160,80,240),
	'S': (80,240,120), 'Z': (240,80,80), 'J': (80,120,240), 'L': (240,160,80)
}


class Piece:
	def __init__(self, kind: str, x: int, y: int) -> None:
		self.kind = kind
		self.states = PIECES[kind]
		self.rot = 0
		self.x = x
		self.y = y
		self.last_action_was_rotation = False
		self.rotation_used_kick = False

	@property
	def blocks(self) -> list[tuple[int, int]]:
		return [(self.x + bx, self.y + by) for bx, by in self.states[self.rot]]

	def rotate(self, direction: int, board: "Board") -> bool:
		old = self.rot
		self.rot = (self.rot + direction) % len(self.states)
		if self._fits(board):
			self.last_action_was_rotation = True
			self.rotation_used_kick = False
			return True
		for dx in (-1,1,-2,2):
			self.x += dx
			if self._fits(board):
				self.last_action_was_rotation = True
				self.rotation_used_kick = True
				return True
			self.x -= dx
		self.rot = old
		self.last_action_was_rotation = False
		self.rotation_used_kick = False
		return False

	def _fits(self, board: "Board") -> bool:
		for x, y in self.blocks:
			if x < 0 or x >= COLS or y < 0 or y >= ROWS:
				return False
			if board.grid[y][x] is not None: return False
		return True

	def move(self, dx: int, dy: int, board: "Board") -> bool:
		self.x += dx
		self.y += dy
		ok = self._fits(board)
		if not ok:
			self.x -= dx
			self.y -= dy
		else:
			if dx != 0 or dy != 0:
				self.last_action_was_rotation = False
				self.rotation_used_kick = False
		return ok
	

	def set_position(self, x: int, y: int) -> None:
		self.x = x
		self.y = y


class Board:
	def __init__(self) -> None:
		self.grid: list[list[str | None]] = [[None] * COLS for _ in range(ROWS)]
		self.piece: Piece | None = None
		self.bag: list[str] = []
		self.next_queue: list[str] = []
		self.hold_kind: str | None = None
		self.hold_used: bool = False
		self.pending_garbage: int = 0
		self.combo_chain: int = 0
		self.back_to_back: bool = False
		self.lock_timer: int = 0
		self.lock_resets: int = 0
		self.grounded: bool = False
		self.alive: bool = True
		self._fill_next_queue()
		self.spawn()
		self.spin_gauge = 0    
		self.spin_boost_timer = 0  

	def _refill_bag(self) -> None:
		types = list(PIECES.keys())
		random.shuffle(types)
		self.bag.extend(types)

	def _fill_next_queue(self) -> None:
		while len(self.next_queue) < 6:
			if not self.bag:
				self._refill_bag()
			self.next_queue.append(self.bag.pop(0))

	def spawn(self) -> None:
		if not self.alive:
			return
		k = self.next_queue.pop(0)
		self._fill_next_queue()
		self.piece = Piece(k, 3, 0)
		self.hold_used = False
		self.lock_timer = 0
		self.lock_resets = 0
		self.grounded = False
		if not self.piece._fits(self):
			self.alive = False
			self.piece = None

	def lock_piece_and_clear(self) -> tuple[int, bool]:
		assert self.piece is not None
		p = self.piece
		for x, y in p.blocks:
			if 0 <= y < ROWS and 0 <= x < COLS:
				self.grid[y][x] = p.kind
		was_spin = self._is_spin(p)
		lines = self._clear_lines()
		self.spawn()
		return lines, was_spin

	def _update_attack_state(self, lines: int, spin: bool) -> None:
		if lines <= 0:
			self.combo_chain = 0
		else:
			self.combo_chain += 1
		if spin or lines == 4:
			self.back_to_back = True
		else: 
			self.back_to_back = False

	def _is_spin(self, piece: Piece) -> bool:
		if not piece.last_action_was_rotation:
			return False
		
		if piece.kind == 'T':
			corners = [
				(piece.x, piece.y),
				(piece.x + 2, piece.y),
				(piece.x, piece.y + 2),
				(piece.x + 2, piece.y + 2),
			]
			filled = 0
			for cx, cy in corners:
				if cx < 0 or cx >= COLS or cy < 0 or cy >= ROWS:
					filled += 1
				elif self.grid[cy][cx] is not None:
					filled += 1

			return filled >= 3
		
		#S,Z,L,J,I spin
		if piece.kind in ("S", "Z", "L", "J", "I"):
			if not piece.rotation_used_kick:
				return False
			blocked = 0
			own = set(piece.blocks)
		    
			for x,y in piece.blocks:
				for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
					nx, ny = x+dx, y+dy
				   
					if (nx,ny) in own:
						continue
					if nx < 0 or nx >= COLS or ny >= ROWS:
						blocked += 1
					elif ny >= 0 and self.grid[ny][nx] is not None:
						blocked += 1
					   
			return blocked >= 6
		return False

		

	def hold(self) -> None:
	
		if self.hold_used or not self.alive:
			return
		assert self.piece is not None
		current = self.piece.kind
		if self.hold_kind is None:
			self.hold_kind = current
			self.spawn()
		else:
		
			self.piece = Piece(self.hold_kind, 3, 0)
			if not self.piece._fits(self):
				self.grid = [[None]*COLS for _ in range(ROWS)]
			self.hold_kind = current
		self.hold_used = True
		self.lock_timer = 0
		self.lock_resets = 0
		self.grounded = False

	def _clear_lines(self) -> int:
		new: list[list[str | None]] = [row for row in self.grid if any(cell is None for cell in row)]
		cleared = ROWS - len(new)
		for _ in range(cleared):
			new.insert(0, [None] * COLS)
		self.grid = new
		return cleared

	def add_garbage(self, n: int) -> None:
		for _ in range(n):
			hole = random.randrange(COLS)
		
			self.grid.pop(0)
			row: list[str | None] = ["X"] * COLS
			row[hole] = None
			self.grid.append(row)

	def queue_garbage(self, n: int) -> None:
		self.pending_garbage += n

	def apply_pending_garbage(self) -> None:
		if self.pending_garbage <= 0:
			return
		self.add_garbage(self.pending_garbage)
		self.pending_garbage = 0

	def update_spin_gauge(self, spin: bool) -> None:

		if self.spin_boost_timer > 0:
			return

		if spin:
			self.spin_gauge += 25

			if self.spin_gauge >= 100:
				self.spin_gauge = 0
				self.spin_boost_timer = FPS * 5

	def try_rotate(self, direction: int) -> bool:
		if not self.alive:
			return False
		assert self.piece is not None
		old_x, old_y, old_rot = self.piece.x, self.piece.y, self.piece.rot
		rotated = self.piece.rotate(direction, self)
		if rotated:
			self._note_ground_contact(after_action=True)
		else:
			self.piece.x, self.piece.y, self.piece.rot = old_x, old_y, old_rot
		return rotated

	def try_move(self, dx: int, dy: int) -> bool:
		if not self.alive:
			return False
		assert self.piece is not None
		moved = self.piece.move(dx, dy, self)
		if moved:
			self.piece.last_action_was_rotation = False
			self.piece.rotation_used_kick = False
			self._note_ground_contact(after_action=True)
		return moved

	def soft_drop_step(self) -> bool:
		if not self.alive:
			return False
		if self.try_move(0, 1):
			assert self.piece is not None
			self.piece.last_action_was_rotation = False
			self.piece.rotation_used_kick = False
			return True
		self._note_ground_contact(after_action=False)
		return False

	def hard_drop(self) -> None:
		if not self.alive:
			return
		while self.try_move(0, 1):
			pass
		self.grounded = True
		self.lock_timer = 0
		self.lock_resets = MAX_LOCK_RESETS

	def commit_lock(self) -> tuple[int, bool, int]:
		if not self.alive:
			return 0, False, 0
		lines, spin = self.lock_piece_and_clear()

		old_combo = self.combo_chain
		old_b2b = self.back_to_back

		if lines == 0:
			combo = 0
		else:
			combo = old_combo +1
		atk = calc_attack(lines, spin, combo, old_b2b)
		self.update_spin_gauge(spin)
		self._update_attack_state(lines, spin)
		return lines, spin, atk

	def _can_fall(self) -> bool:
		if not self.alive or self.piece is None:
			return False
		
		p=self.piece
		p.y += 1
		can = p._fits(self)
		p.y -= 1

		return can

	def _note_ground_contact(self, after_action: bool) -> None:
		if not self.alive:
			return
		assert self.piece is not None
		if self._can_fall():
			self.grounded = False
			self.lock_timer = 0
			self.lock_resets = 0
			return
		if not self.grounded:
			self.grounded = True
			self.lock_timer = LOCK_DELAY_FRAMES
			self.lock_resets = 0
		elif after_action and self.lock_resets < MAX_LOCK_RESETS:
			self.lock_timer = LOCK_DELAY_FRAMES
			self.lock_resets += 1

	def tick_lock(self) -> tuple[int, bool, int] | None:
		if not self.alive:
			return None
		assert self.piece is not None
		if not self.grounded:
			if not self._can_fall():
				self.grounded = True
				self.lock_timer = LOCK_DELAY_FRAMES
				self.lock_resets = 0
			return None
		if self._can_fall():
			self.grounded = False
			self.lock_timer = 0
			self.lock_resets = 0
			return None
		self.lock_timer -= 1
		if self.lock_timer <= 0:
			return self.commit_lock()
		return None


def calc_attack(lines: int, spin: bool, combo_chain: int, back_to_back: bool) -> int:
	if lines <= 0:
		return 0
	LINE_ATTACK = {
    	1:0,
    	2:1,
    	3:2,
    	4:4,
	}

	SPIN_ATTACK = {
    	1:2,
    	2:4,
    	3:6,
	}
	if spin:
		attack = SPIN_ATTACK.get(lines, 0)
	else:
		attack = LINE_ATTACK.get(lines, 0)
	attack+=COMBO_BONUS.get(combo_chain, 5)
	if back_to_back and(spin or lines == 4):
		attack += 1
	return attack



def send_attack(from_idx: int, atk: int, boards: list[Board]) -> None:
	if atk <= 0:
		return
	opponent = boards[1-from_idx]
	if opponent.pending_garbage > 0:
		cancel = min(opponent.pending_garbage, atk)
		opponent.pending_garbage -= cancel
		atk -= cancel
	if atk > 0:
		opponent.queue_garbage(atk)


def draw_board(surf: pygame.Surface, board: Board, xoff: int, yoff: int) -> None:

	pygame.draw.rect(surf, (30,30,30), (xoff-4,yoff-4,COLS*CELL+8,ROWS*CELL+8))
	for y in range(ROWS):
		for x in range(COLS):
			cell = board.grid[y][x]
			if cell is not None:
				color = COLORS.get(cell, (200,200,200))
				pygame.draw.rect(surf, color, (xoff + x*CELL, yoff + y*CELL, CELL-1, CELL-1))

	if board.piece is not None:
		for x, y in board.piece.blocks:
			if y>=0:
				c = COLORS.get(board.piece.kind, (200, 200, 200))
				pygame.draw.rect(surf, c, (xoff + x*CELL, yoff + y*CELL, CELL-1, CELL-1))
	
		ghost = Piece(board.piece.kind, board.piece.x, board.piece.y)
		ghost.rot = board.piece.rot
		while ghost._fits(board):
			ghost.y += 1
		ghost.y -= 1
		for x, y in ghost.blocks:
			if y>=0:
				pygame.draw.rect(surf, (120, 120, 120), (xoff + x*CELL, yoff + y*CELL, CELL-1, CELL-1), 1)
	
	font = pygame.font.SysFont(None, 20)
	hold_x = xoff + COLS*CELL + 6
	surf.blit(font.render('HOLD', True, (200,200,200)), (hold_x, yoff))
	if board.hold_kind:
		surf.blit(font.render(board.hold_kind, True, (255,255,255)), (hold_x, yoff+20))
	
	surf.blit(font.render('NEXT', True, (200,200,200)), (hold_x, yoff+60))
	for i, k in enumerate(board.next_queue[:5]):
		surf.blit(font.render(k, True, (220, 220, 220)), (hold_x, yoff+80 + i*18))

	if board.pending_garbage>0:
		surf.blit(font.render(f'G:{board.pending_garbage}', True, (255,120,120)), (hold_x, yoff+220))


def main() -> None:
	pygame.init()
	screen = pygame.display.set_mode((WIDTH, HEIGHT))
	clock = pygame.time.Clock()
	state: ScreenState = "start"
	end_data: EndScreenData | None = None

	boards = [Board(), Board()]

	gravity_timer = 0
	gravity_interval = 30 


	controls = [
		{'left':pygame.K_a,'right':pygame.K_d,'down':pygame.K_s,'drop':pygame.K_w,'rot_l':pygame.K_q,'rot_r':pygame.K_e},
		{'left':pygame.K_LEFT,'right':pygame.K_RIGHT,'down':pygame.K_DOWN,'drop':pygame.K_UP,'rot_l':pygame.K_COMMA,'rot_r':pygame.K_PERIOD},
	]

	controls[0]['hold'] = pygame.K_z
	controls[1]['hold'] = pygame.K_RSHIFT
	

	running = True
	while running:
		dt = clock.tick(FPS)
		gravity_timer += 1

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			if event.type == pygame.KEYDOWN and state == "start":
				if event.key == pygame.K_RETURN:
					boards = [Board(), Board()]
					gravity_timer = 0
					state = "playing"
			elif event.type == pygame.KEYDOWN and state in ("win", "lose"):
				if event.key == pygame.K_RETURN:
					boards = [Board(), Board()]
					gravity_timer = 0
					end_data = None
					state = "playing"
			elif event.type == pygame.KEYDOWN and state == "playing":
				for i, b in enumerate(boards):
					c = controls[i]
					if event.key == c['left']:
						b.try_move(-1,0)
					if event.key == c['right']:
						b.try_move(1,0)
					if event.key == c['down']:
						if not b.soft_drop_step():
							pass
					if event.key == c['rot_l']:
						b.try_rotate(-1)
					if event.key == c['rot_r']:
						b.try_rotate(1)
					if event.key == c['drop']:
						b.hard_drop()
						lines, spin, atk = b.commit_lock()
						if atk > 0:
							send_attack(i, atk, boards)
					if event.key == c.get('hold'):
						b.hold()

		if state == "playing":
			for b in boards:
				if b.spin_boost_timer > 0:
					b.spin_boost_timer -= 1

			if gravity_timer >= gravity_interval:
				gravity_timer = 0
				for i, b in enumerate(boards):
					if b.piece is None:
						continue
					moved = b.piece.move(0, 1, b)
					if not moved:
						b._note_ground_contact(after_action=False)
						result = b.tick_lock()
						if result is not None:
							lines, spin, atk = result
							if atk > 0:
								send_attack(i, atk, boards)
					else:
						b.grounded = False
						b.lock_timer = 0
						b.lock_resets = 0

			for b in boards:
				b.apply_pending_garbage()

			if not boards[0].alive or not boards[1].alive:
				if not boards[0].alive and not boards[1].alive:
					state = "lose"
					end_data = EndScreenData(winner_index=0, loser_index=1, message="Double KO")
				elif not boards[0].alive:
					state = "lose"
					end_data = EndScreenData(winner_index=1, loser_index=0, message="Player 1 topped out")
				else:
					state = "win"
					end_data = EndScreenData(winner_index=0, loser_index=1, message="Player 2 topped out")

		if state == "start":
			draw_start_screen(screen)
		elif state in ("win", "lose") and end_data is not None:
			draw_end_screen(screen, end_data, is_win=state == "win")
		else:
			screen.fill((10,10,10))
			draw_board(screen, boards[0], 40, 30)
			draw_board(screen, boards[1], 40 + COLS*CELL + 120, 30)

		

		pygame.display.flip()

	pygame.quit()


if __name__ == '__main__':
	main()
