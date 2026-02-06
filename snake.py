import pygame
import random
import sys
import json
import os
import array
import math

# Constants
CELL_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 20
SCREEN_WIDTH = CELL_SIZE * GRID_WIDTH
SCREEN_HEIGHT = CELL_SIZE * GRID_HEIGHT
BASE_FPS = 10
SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
BLUE = (50, 120, 220)
DARK_BLUE = (30, 80, 170)
RED = (220, 50, 50)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)
GOLD = (255, 215, 0)
DARK_GOLD = (200, 170, 0)

# Directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# Game states
STATE_START = "start"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"


def generate_tone(frequency, duration_ms, volume=0.3, sample_rate=44100):
    """Generate a simple sine wave tone as a pygame Sound."""
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h", [0] * n_samples)
    max_val = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        buf[i] = int(max_val * math.sin(2 * math.pi * frequency * t))
    sound = pygame.mixer.Sound(buffer=buf)
    return sound


def load_high_scores():
    try:
        with open(SCORE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_high_scores(scores):
    with open(SCORE_FILE, "w") as f:
        json.dump(scores, f)


class Snake:
    def __init__(self, start_pos, start_direction):
        self.start_pos = start_pos
        self.start_direction = start_direction
        self.alive = True
        self.reset()

    def reset(self):
        self.body = [self.start_pos]
        self.direction = self.start_direction
        self.grow = False
        self.alive = True

    def move(self):
        if not self.alive:
            return
        head_x, head_y = self.body[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        self.body.insert(0, new_head)
        if not self.grow:
            self.body.pop()
        self.grow = False

    def set_direction(self, direction):
        dx, dy = direction
        curr_dx, curr_dy = self.direction
        if (dx + curr_dx, dy + curr_dy) != (0, 0):
            self.direction = direction

    def check_wall_collision(self):
        head = self.body[0]
        return head[0] < 0 or head[0] >= GRID_WIDTH or head[1] < 0 or head[1] >= GRID_HEIGHT

    def check_self_collision(self):
        return self.body[0] in self.body[1:]

    def check_collision_with(self, other_snake):
        """Check if this snake's head collides with another snake's body."""
        return self.body[0] in other_snake.body


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(44100, -16, 1, 512)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Snake - 2 Player")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 24)
        self.big_font = pygame.font.SysFont("consolas", 48)
        self.small_font = pygame.font.SysFont("consolas", 18)

        # Player 1 (green, WASD, spawns left)
        self.snake1 = Snake((GRID_WIDTH // 4, GRID_HEIGHT // 2), RIGHT)
        self.score1 = 0

        # Player 2 (blue, arrows, spawns right)
        self.snake2 = Snake((3 * GRID_WIDTH // 4, GRID_HEIGHT // 2), LEFT)
        self.score2 = 0

        self.winner = None
        self.food = None
        self.bonus_food = None
        self.bonus_timer = 0
        self.bonus_spawn_timer = 0
        self.level = 1
        self.state = STATE_START
        self.high_scores = load_high_scores()
        self.spawn_food()

        # Generate sounds
        self.eat_sound = generate_tone(600, 80, 0.2)
        self.bonus_sound = generate_tone(800, 150, 0.25)
        self.game_over_sound = generate_tone(200, 400, 0.3)

    def all_snake_cells(self):
        """Return all cells occupied by both snakes."""
        return set(self.snake1.body) | set(self.snake2.body)

    def spawn_food(self):
        occupied = self.all_snake_cells()
        if self.bonus_food:
            occupied.add(self.bonus_food)
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in occupied:
                self.food = pos
                break

    def spawn_bonus(self):
        occupied = self.all_snake_cells()
        occupied.add(self.food)
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in occupied:
                self.bonus_food = pos
                self.bonus_timer = 5 * self.get_fps()
                break

    def get_fps(self):
        return BASE_FPS + (self.level - 1) * 2

    def update_level(self):
        max_score = max(self.score1, self.score2)
        self.level = 1 + max_score // 50

    def add_high_score(self, score):
        self.high_scores.append(score)
        self.high_scores.sort(reverse=True)
        self.high_scores = self.high_scores[:5]
        save_high_scores(self.high_scores)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state == STATE_START:
                    if event.key == pygame.K_SPACE:
                        self.state = STATE_PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                elif self.state == STATE_GAME_OVER:
                    if event.key == pygame.K_SPACE:
                        self.restart()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                elif self.state == STATE_PLAYING:
                    # Player 1: WASD
                    if event.key == pygame.K_w:
                        self.snake1.set_direction(UP)
                    elif event.key == pygame.K_s:
                        self.snake1.set_direction(DOWN)
                    elif event.key == pygame.K_a:
                        self.snake1.set_direction(LEFT)
                    elif event.key == pygame.K_d:
                        self.snake1.set_direction(RIGHT)
                    # Player 2: Arrow keys
                    elif event.key == pygame.K_UP:
                        self.snake2.set_direction(UP)
                    elif event.key == pygame.K_DOWN:
                        self.snake2.set_direction(DOWN)
                    elif event.key == pygame.K_LEFT:
                        self.snake2.set_direction(LEFT)
                    elif event.key == pygame.K_RIGHT:
                        self.snake2.set_direction(RIGHT)
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

    def update(self):
        if self.state != STATE_PLAYING:
            return

        # Move both snakes
        self.snake1.move()
        self.snake2.move()

        # Check collisions for both players
        p1_dead = False
        p2_dead = False

        # Wall collisions
        if self.snake1.check_wall_collision():
            p1_dead = True
        if self.snake2.check_wall_collision():
            p2_dead = True

        # Self collisions
        if self.snake1.check_self_collision():
            p1_dead = True
        if self.snake2.check_self_collision():
            p2_dead = True

        # Cross-snake collisions
        if self.snake1.check_collision_with(self.snake2):
            p1_dead = True
        if self.snake2.check_collision_with(self.snake1):
            p2_dead = True

        # Head-on collision (both heads in same cell)
        if self.snake1.body[0] == self.snake2.body[0]:
            p1_dead = True
            p2_dead = True

        if p1_dead or p2_dead:
            self.snake1.alive = not p1_dead
            self.snake2.alive = not p2_dead
            if p1_dead and p2_dead:
                self.winner = "Draw"
            elif p1_dead:
                self.winner = "Player 2"
            else:
                self.winner = "Player 1"
            self.state = STATE_GAME_OVER
            self.game_over_sound.play()
            self.add_high_score(self.score1)
            self.add_high_score(self.score2)
            return

        # Food collision for player 1
        if self.snake1.body[0] == self.food:
            self.snake1.grow = True
            self.score1 += 10
            self.update_level()
            self.eat_sound.play()
            self.spawn_food()

        # Food collision for player 2
        if self.snake2.body[0] == self.food:
            self.snake2.grow = True
            self.score2 += 10
            self.update_level()
            self.eat_sound.play()
            self.spawn_food()

        # Bonus food for player 1
        if self.bonus_food and self.snake1.body[0] == self.bonus_food:
            self.snake1.grow = True
            self.score1 += 50
            self.update_level()
            self.bonus_sound.play()
            self.bonus_food = None
            self.bonus_timer = 0

        # Bonus food for player 2
        if self.bonus_food and self.snake2.body[0] == self.bonus_food:
            self.snake2.grow = True
            self.score2 += 50
            self.update_level()
            self.bonus_sound.play()
            self.bonus_food = None
            self.bonus_timer = 0

        # Bonus food timer
        if self.bonus_food:
            self.bonus_timer -= 1
            if self.bonus_timer <= 0:
                self.bonus_food = None

        # Spawn bonus food periodically
        self.bonus_spawn_timer += 1
        if self.bonus_spawn_timer >= 15 * self.get_fps() and not self.bonus_food:
            self.spawn_bonus()
            self.bonus_spawn_timer = 0

    def draw_grid(self):
        for x in range(0, SCREEN_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRAY, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, GRAY, (0, y), (SCREEN_WIDTH, y))

    def draw_snake(self, snake, head_color, body_color):
        for i, (x, y) in enumerate(snake.body):
            color = head_color if i == 0 else body_color
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 1)

    def draw_food(self):
        food_rect = pygame.Rect(self.food[0] * CELL_SIZE, self.food[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, RED, food_rect)
        pygame.draw.rect(self.screen, BLACK, food_rect, 1)

        if self.bonus_food:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.4 + 0.6
            color = (int(255 * pulse), int(215 * pulse), 0)
            bonus_rect = pygame.Rect(
                self.bonus_food[0] * CELL_SIZE, self.bonus_food[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE
            )
            pygame.draw.rect(self.screen, color, bonus_rect)
            pygame.draw.rect(self.screen, DARK_GOLD, bonus_rect, 1)

    def draw_hud(self):
        # Player 1 score (left, green)
        p1_text = self.font.render(f"P1: {self.score1}", True, GREEN)
        self.screen.blit(p1_text, (10, 5))

        # Level (center)
        level_text = self.font.render(f"Level: {self.level}", True, WHITE)
        level_rect = level_text.get_rect(center=(SCREEN_WIDTH // 2, 17))
        self.screen.blit(level_text, level_rect)

        # Player 2 score (right, blue)
        p2_text = self.font.render(f"P2: {self.score2}", True, BLUE)
        p2_rect = p2_text.get_rect(topright=(SCREEN_WIDTH - 10, 5))
        self.screen.blit(p2_text, p2_rect)

    def draw_high_scores(self, y_start):
        title = self.font.render("High Scores", True, GOLD)
        rect = title.get_rect(center=(SCREEN_WIDTH // 2, y_start))
        self.screen.blit(title, rect)

        if not self.high_scores:
            no_scores = self.small_font.render("No scores yet", True, GRAY)
            rect = no_scores.get_rect(center=(SCREEN_WIDTH // 2, y_start + 30))
            self.screen.blit(no_scores, rect)
        else:
            for i, hs in enumerate(self.high_scores[:5]):
                text = self.small_font.render(f"{i + 1}. {hs}", True, WHITE)
                rect = text.get_rect(center=(SCREEN_WIDTH // 2, y_start + 30 + i * 25))
                self.screen.blit(text, rect)

    def draw_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

    def draw_start_screen(self):
        self.screen.fill(BLACK)
        self.draw_grid()
        self.draw_overlay()

        title = self.big_font.render("SNAKE", True, GREEN)
        rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, rect)

        subtitle = self.font.render("2 Player", True, BLUE)
        rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 105))
        self.screen.blit(subtitle, rect)

        controls = [
            "Player 1 (Green): WASD",
            "Player 2 (Blue):  Arrow Keys",
            "ESC - Quit",
        ]
        for i, line in enumerate(controls):
            text = self.small_font.render(line, True, WHITE)
            rect = text.get_rect(center=(SCREEN_WIDTH // 2, 155 + i * 25))
            self.screen.blit(text, rect)

        self.draw_high_scores(245)

        start_text = self.font.render("Press SPACE to start", True, WHITE)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        start_text.set_alpha(int(128 + 127 * pulse))
        rect = start_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        self.screen.blit(start_text, rect)

    def draw_game_over_screen(self):
        self.draw_overlay()

        game_over_text = self.big_font.render("GAME OVER", True, RED)
        rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        self.screen.blit(game_over_text, rect)

        # Winner announcement
        if self.winner == "Draw":
            winner_color = WHITE
            winner_msg = "It's a Draw!"
        elif self.winner == "Player 1":
            winner_color = GREEN
            winner_msg = "Player 1 Wins!"
        else:
            winner_color = BLUE
            winner_msg = "Player 2 Wins!"

        winner_text = self.font.render(winner_msg, True, winner_color)
        rect = winner_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 55))
        self.screen.blit(winner_text, rect)

        # Both scores
        scores_text = self.font.render(f"P1: {self.score1}  |  P2: {self.score2}", True, WHITE)
        rect = scores_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        self.screen.blit(scores_text, rect)

        self.draw_high_scores(SCREEN_HEIGHT // 2 + 20)

        restart_text = self.font.render("SPACE to restart | ESC to quit", True, WHITE)
        rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
        self.screen.blit(restart_text, rect)

    def draw(self):
        if self.state == STATE_START:
            self.draw_start_screen()
        else:
            self.screen.fill(BLACK)
            self.draw_grid()
            self.draw_snake(self.snake1, GREEN, DARK_GREEN)
            self.draw_snake(self.snake2, BLUE, DARK_BLUE)
            self.draw_food()
            self.draw_hud()
            if self.state == STATE_GAME_OVER:
                self.draw_game_over_screen()

        pygame.display.flip()

    def restart(self):
        self.snake1.reset()
        self.snake2.reset()
        self.score1 = 0
        self.score2 = 0
        self.winner = None
        self.level = 1
        self.bonus_food = None
        self.bonus_timer = 0
        self.bonus_spawn_timer = 0
        self.state = STATE_PLAYING
        self.spawn_food()

    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(self.get_fps() if self.state == STATE_PLAYING else 30)


if __name__ == "__main__":
    game = Game()
    game.run()
