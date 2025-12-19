import pygame
from track_data import TrackData

WIDTH, HEIGHT = 1920, 1080
GP_YEAR = 2025
GP_LOCATION = "Monaco"
SESSION_TYPE = "R"

track = TrackData(GP_YEAR, GP_LOCATION, SESSION_TYPE)
track_points = track.generate_screen_points(WIDTH, HEIGHT)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(f"F1 Replay: {GP_YEAR} {GP_LOCATION}")
clock = pygame.time.Clock()

running = True
while (running):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    screen.fill((20, 20, 20))
    if len(track_points) > 1:
        start_x, start_y = track_points[0]
        pygame.draw.aalines(screen, (200, 200, 200), True, track_points, 5)
        pygame.draw.circle(screen, (0, 255, 0), (int(start_x), int(start_y)), 8)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
