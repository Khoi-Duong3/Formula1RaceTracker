import pygame
import os

compound_icons = {}

def get_compound_icon(compound_type):
    if compound_type in compound_icons:
        return compound_icons[compound_type]
    
    filenames = {
        "SOFT": "softs",
        "MEDIUM": "mediums",
        "HARD": "hards",
        "WET": "wets",
        "INTERMEDIATE": "intermediates",
        "UNKNOWN": None
    }

    fname = filenames.get(compound_type, None)
    if not fname:
        return None
    path = os.path.join("compounds", f"{fname}.png")

    try:
        if os.path.exists(path):
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.smoothscale(image, (30, 30))
            compound_icons[compound_type] = image
            return image
    except Exception as e:
        print(f"Failed to load icon for {compound_type}: {e}")
    
    return None

def draw_leaderboard(screen, font, title_font, race, current_time):
    panel_colour = (25, 25, 25)
    panel_rect = pygame.Rect(20, 100, 180, 580)

    pygame.draw.rect(screen, panel_colour, panel_rect, border_radius=16)
    pygame.draw.rect(screen, (180, 180, 180), panel_rect, 2, border_radius=16)

    standings = race.get_leaderboard(current_time)

    row_y = panel_rect.y + 30

    for entry in standings:
        text_color = (150, 150, 150) if entry['DNF'] else (255, 255, 255)
        text = font.render(f"{entry["Position"]:>2} {entry["Abbreviation"]}", True, text_color)
        screen.blit(text, (panel_rect.x + 10, row_y))
        compound_name = entry.get("Compound", "UNKNOWN")
        
        if entry["Pitting"]:
            pit_box_rect = pygame.Rect(220, row_y, 20, 20)
            pygame.draw.rect(screen, (255, 255, 255), pit_box_rect)
            p_text = font.render("P", True, (0, 0, 0))
            p_rect = p_text.get_rect(center=pit_box_rect.center)
            screen.blit(p_text, p_rect)

        if entry["DNF"]:
            dnf_text = font.render("DNF", True, text_color)
            screen.blit(dnf_text, (panel_rect.x + 125, row_y))
        else:
            compound_icon = get_compound_icon(compound_name)
            if compound_icon:
                icon_x = panel_rect.x + 145
                icon_y = row_y + (text.get_height() // 2) - (compound_icon.get_height() // 2)
                screen.blit(compound_icon, (icon_x, icon_y))
        row_y += 26
    
    