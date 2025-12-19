import pygame
from track_data import TrackData

WIDTH, HEIGHT = 1920, 1080
GP_YEAR = 2025
GP_LOCATION = "United States"
SESSION_TYPE = "R"

track = TrackData(GP_YEAR, GP_LOCATION, SESSION_TYPE)
track_points = track.generate_screen_points(WIDTH, HEIGHT)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(f"F1 Replay: {GP_YEAR} {GP_LOCATION}")
clock = pygame.time.Clock()

running = True
current_point_index = 0

while (running):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    screen.fill((20, 20, 20))
    if len(track_points) > 1:
        pygame.draw.lines(screen, (200, 200, 200), True, track_points, 5)
        
        current_x, current_y = track_points[current_point_index]
        pygame.draw.circle(screen, (0, 255, 0), (int(current_x), int(current_y)), 8)

        current_point_index = (current_point_index + 1) % len(track_points)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
