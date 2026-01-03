import pygame

class InputBox:
    def __init__(self, x, y, w, h, text="", label = ""):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color('lightskyblue3')
        self.color_active = pygame.Color('dodgerblue2')
        self.color = self.color_inactive
        self.text = text
        self.label = label
        self.font = pygame.font.Font(None, 32)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False


    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            
            self.color = self.color_active if self.active else self.color_inactive
    
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.active = False
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                
                self.txt_surface = self.font.render(self.text, True, self.color)
        
    def draw(self, screen):
        if self.label:
            label_surf = self.font.render(self.label, True, (200, 200, 200))
            screen.blit(label_surf, (self.rect.x - 120, self.rect.y + 5))
        
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        pygame.draw.rect(screen, self.color, self.rect, 2)
    
class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.font = pygame.font.Font(None, 32)

        centre_x = self.width // 2 - 100
        centre_y = self.height // 2 - 100

        self.inputs = {
            "location": InputBox(centre_x, centre_y, 200, 32, "Monza", "Location: "),
            "year": InputBox(centre_x, centre_y + 50, 200, 32, "2025", "Year: "),
            "session_type": InputBox(centre_x, centre_y + 100, 200, 32, "R", "Session: ")
        }

        self.start_button = pygame.Rect(centre_x, centre_y + 160, 200, 50)
        self.error_message = ""
    
    def run(self):
        clock = pygame.time.Clock()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None

                for box in self.inputs.values():
                    box.handle_event(event)
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.start_button.collidepoint(event.pos):
                        try:
                            loc = self.inputs["location"].text
                            year = int(self.inputs["year"].text)
                            session = self.inputs["session_type"].text

                            return (loc, year, session)
                        except ValueError:
                            self.error_message = "Year must be a number!"

            self.screen.fill((30, 30, 30))
            title = pygame.font.Font(None, 50).render("F1 Replay Setup", True, (255, 255, 255))
            title_rect = title.get_rect(center=(self.width//2, self.height//2 - 180))
            self.screen.blit(title, title_rect)

            for box in self.inputs.values():
                box.draw(self.screen)
            
            pygame.draw.rect(self.screen, (0, 180, 0), self.start_button)
            btn_text = self.font.render("LOAD SESSION", True, (255, 255, 255))
            btn_rect = btn_text.get_rect(center=self.start_button.center)
            self.screen.blit(btn_text, btn_rect)

            if self.error_message:
                err = self.font.render(self.error_msg, True, (255, 100, 100))
                self.screen.blit(err, (self.width//2 - 100, self.height//2 + 220))

            pygame.display.flip()
            clock.tick(60)

