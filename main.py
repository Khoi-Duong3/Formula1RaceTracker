import pygame
from race_data import RaceData
from leaderboard import draw_leaderboard
from menu import Menu 

WIDTH, HEIGHT = 1600, 900

def world_to_screen(race, x, y):
    min_x, max_x = race.track_x.min(), race.track_x.max()
    min_y, max_y = race.track_y.min(), race.track_y.max()
    
    track_w = max_x - min_x
    track_h = max_y - min_y
    
    scale = min(WIDTH / track_w, HEIGHT / track_h) * 0.7
    x_offset = (WIDTH - track_w * scale) / 2 + 100
    y_offset = (HEIGHT - track_h * scale) / 2
    
    screen_x = (x - min_x) * scale + x_offset
    screen_y = HEIGHT - ((y - min_y) * scale + y_offset)
    
    return int(screen_x), int(screen_y)

def draw_loading(screen, text):
    screen.fill((20, 20, 20))
    font = pygame.font.Font(None, 48)
    surf = font.render(text, True, (255, 255, 255))
    rect = surf.get_rect(center=(WIDTH//2, HEIGHT//2))
    screen.blit(surf, rect)
    pygame.display.flip()

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("F1 Race Replay - Configuration")
    
    menu = Menu(screen)
    user_settings = menu.run()

    if user_settings is None:
        pygame.quit()
        return

    gp_location, gp_year, session_type = user_settings
    
    draw_loading(screen, f"Loading {gp_location} {gp_year}...")
    
    try:
        race = RaceData(gp_year, gp_location, session_type)
    except Exception as e:
        print(f"Error loading session: {e}")
        pygame.quit()
        return

    pygame.display.set_caption(f"F1 Race Replay: {gp_location} {gp_year}")
    clock = pygame.time.Clock()

    track_points = []
    if race.track_x is not None:
        for i in range(len(race.track_x)):
            sx, sy = world_to_screen(race, race.track_x[i], race.track_y[i])
            track_points.append((sx, sy))

    playback_speed = 1.0
    current_frame = 0.0
    paused = False
    running = True
    
    font = pygame.font.Font(None, 22)
    title_font = pygame.font.Font(None, 28)
    driver_font = pygame.font.Font(None, 28)
    
    header_view_mode = 0
    toggle_btn_rect = pygame.Rect(0, 0, 0, 0)
    last_toggle_time = 0

    print(f"\nStarting replay with {len(race.frames)} frames...")
    
    while running:
        dt_ms = clock.tick(60)
        dt = dt_ms / 1000.0
        current_ticks = pygame.time.get_ticks()

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
                    playback_speed = min(64.0, playback_speed * 2)
                elif event.key == pygame.K_DOWN:
                    playback_speed = max(0.25, playback_speed / 2)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if current_ticks - last_toggle_time > 200:
                        if toggle_btn_rect.collidepoint(event.pos):
                            header_view_mode = 1 - header_view_mode
                            last_toggle_time = current_ticks

        if not paused:
            simulated_dt = dt * playback_speed
            current_frame += simulated_dt / race.frame_interval
            
            if current_frame >= len(race.frames):
                current_frame = len(race.frames) - 1
                paused = True

        screen.fill((20, 20, 20))
        
        frame_idx = int(current_frame)
        frame = race.frames[frame_idx]
        
        if len(track_points) > 2:
            pygame.draw.aalines(screen, (80, 80, 80), True, track_points, 3)
            
        for driver_num, driver in frame['drivers'].items():
            sx, sy = world_to_screen(race, driver['x'], driver['y'])
            color = driver['colour'] if driver['active'] else (100, 100, 100)
            
            pygame.draw.circle(screen, color, (sx, sy), 8)
            pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 8, 2)
            
            name_text = driver_font.render(driver['abbreviation'], True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(sx, sy - 20))
            screen.blit(name_text, name_rect)

        toggle_btn_rect = draw_leaderboard(screen, race, header_view_mode, frame)
        
        speed_text = font.render(f"Speed: {playback_speed}x", True, (255, 255, 255))
        screen.blit(speed_text, (20, 800))
        
        if paused:
            pause_text = title_font.render("PAUSED", True, (255, 50, 50))
            pause_rect = pause_text.get_rect(center=(WIDTH // 2, 50))
            screen.blit(pause_text, pause_rect)

        pygame.display.flip()

    pygame.quit()
    print("Replay finished!")

if __name__ == "__main__":
    main()
