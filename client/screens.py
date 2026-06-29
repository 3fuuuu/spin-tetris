from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pygame

ScreenState = Literal["start", "playing", "win", "lose"]


@dataclass(frozen=True)
class EndScreenData:
	winner_index: int
	loser_index: int
	message: str


def draw_centered_text(surface: pygame.Surface, text: str, y: int, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
	text_surface = font.render(text, True, color)
	rect = text_surface.get_rect(center=(surface.get_width() // 2, y))
	surface.blit(text_surface, rect)


def draw_start_screen(surface: pygame.Surface) -> None:
	surface.fill((12, 14, 24))
	width = surface.get_width()
	height = surface.get_height()
	big_font = pygame.font.SysFont(None, 72)
	mid_font = pygame.font.SysFont(None, 28)
	small_font = pygame.font.SysFont(None, 22)

	pygame.draw.circle(surface, (40, 70, 110), (width // 2 - 180, height // 2 - 60), 90)
	pygame.draw.circle(surface, (90, 40, 120), (width // 2 + 180, height // 2 + 20), 70)

	draw_centered_text(surface, "Spin Tetris", height // 2 - 150, big_font, (240, 240, 255))
	draw_centered_text(surface, "Press Enter to Start", height // 2 + 10, mid_font, (255, 230, 120))
	draw_centered_text(surface, "P1: A/D move  S soft  W hard  Q/E rotate  Z hold", height // 2 + 70, small_font, (210, 210, 220))
	draw_centered_text(surface, "P2: ←/→ move  ↓ soft  ↑ hard  ,/. rotate  RightShift hold", height // 2 + 102, small_font, (210, 210, 220))


def draw_end_screen(surface: pygame.Surface, data: EndScreenData, is_win: bool) -> None:
	surface.fill((18, 10, 16) if is_win else (8, 16, 22))
	width = surface.get_width()
	height = surface.get_height()
	big_font = pygame.font.SysFont(None, 72)
	mid_font = pygame.font.SysFont(None, 30)
	small_font = pygame.font.SysFont(None, 22)

	accent = (255, 190, 80) if is_win else (120, 220, 255)
	glow = (80, 40, 20) if is_win else (20, 50, 70)
	pygame.draw.rect(surface, glow, surface.get_rect().inflate(-120, -160), border_radius=24)
	pygame.draw.rect(surface, accent, surface.get_rect().inflate(-120, -160), width=3, border_radius=24)

	title = "Victory" if is_win else "Defeat"
	draw_centered_text(surface, title, height // 2 - 140, big_font, accent)
	draw_centered_text(surface, data.message, height // 2 - 70, mid_font, (240, 240, 240))
	draw_centered_text(surface, f"Winner: Player {data.winner_index + 1}", height // 2 - 10, mid_font, (240, 240, 240))
	draw_centered_text(surface, "Press Enter to return to title", height // 2 + 70, small_font, (220, 220, 220))
