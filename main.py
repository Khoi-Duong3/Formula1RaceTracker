import pygame
import sys
from race_data import RaceData

WIDTH, HEIGHT = 1920, 1080
GP_YEAR = 2025
GP_LOCATION = "Monza"
SESSION_TYPE = "R"
PLAYBACK_SPEED = 1.0

print("="*60)
race = RaceData(GP_YEAR, GP_LOCATION, SESSION_TYPE)
print("="*60)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(f"F1 Race Replay: {GP_LOCATION} {GP_YEAR}")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 32)
title_font = pygame.font.Font(None, 48)


def world_to_screen(x, y):
    min_x, max_x = race.track_x.min(), race.track_x.max()
    min_y, max_y = race.track_y.min(), race.track_y.max()

    track_w = max_x - min_x
    track_h = max_y - min_y

    scale = min(WIDTH / track_w, HEIGHT / track_h) * 0.8

    x_offset = (WIDTH - track_w * scale) / 2
    y_offset = (HEIGHT - track_h * scale) / 2

    screen_x = (x - min_x) * scale + x_offset
    screen_y = HEIGHT - ((y - min_y) * scale + y_offset)
    
    return int(screen_x), int(screen_y)

track_points = []
for i in range(len(race.track_x)):
    sx, sy = world_to_screen(race.track_x[i], race.track_y[i])
    track_points.append((sx, sy))

current_frame = 0
paused = False
running = True

print(f"\nStarting replay with {len(race.frames)} frames...")
print("Controls: SPACE=pause, LEFT/RIGHT=skip, UP/DOWN=speed, ESC=quit\n")

while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_LEFT:
                current_frame = max(0, current_frame - 10)
            elif event.key == pygame.K_RIGHT:
                current_frame = min(len(race.frames) - 1, current_frame + 10)
            elif event.key == pygame.K_UP:
                PLAYBACK_SPEED = min(4.0, PLAYBACK_SPEED * 2)
                print(f"Playback speed: {PLAYBACK_SPEED}x")
            elif event.key == pygame.K_DOWN:
                PLAYBACK_SPEED = max(0.25, PLAYBACK_SPEED / 2)
                print(f"Playback speed: {PLAYBACK_SPEED}x")
    
    # Update frame
    if not paused:
        current_frame += PLAYBACK_SPEED
        if current_frame >= len(race.frames):
            current_frame = len(race.frames) - 1
            paused = True
    
    frame_idx = int(current_frame)
    frame = race.frames[frame_idx]
    
    # Clear screen
    screen.fill((20, 20, 20))
    
    # Draw track
    if len(track_points) > 2:
        pygame.draw.lines(screen, (80, 80, 80), True, track_points, 3)
    
    # Draw drivers
    for driver_num, driver in frame['drivers'].items():
        sx, sy = world_to_screen(driver['x'], driver['y'])
        
        # Draw driver circle
        color = driver['colour'] if driver['active'] else (100, 100, 100)
        pygame.draw.circle(screen, color, (sx, sy), 8)
        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 8, 2)
        
        # Draw driver abbreviation
        name_text = font.render(driver['abbreviation'], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(sx, sy - 20))
        screen.blit(name_text, name_rect)
    
    # Draw UI
    time_text = title_font.render(f"Time: {frame['time']:.1f}s", True, (255, 255, 255))
    screen.blit(time_text, (20, 20))
    
    speed_text = font.render(f"Speed: {PLAYBACK_SPEED}x", True, (255, 255, 255))
    screen.blit(speed_text, (20, 70))
    
    if paused:
        pause_text = title_font.render("PAUSED", True, (255, 50, 50))
        pause_rect = pause_text.get_rect(center=(WIDTH // 2, 50))
        screen.blit(pause_text, pause_rect)
    
    # Update display
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print("Replay finished!")