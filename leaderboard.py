import pygame
import os

compound_icons = {}

def get_logo():
    img_path = os.path.join("leaderboard_assets", "f1logo.png")
    
    if os.path.exists(img_path):
        try:
            img = pygame.image.load(img_path).convert_alpha()
            LOGO_IMG = pygame.transform.smoothscale(img, (128, 96))
        except Exception as e:
            print(f"Logo load error: {e}")
            
    return LOGO_IMG


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

def draw_leaderboard(screen, race, header_view_mode, frame):
    panel_colour = (25, 25, 25)
    panel_rect = pygame.Rect(20, 20, 230, 750) 

    pygame.draw.rect(screen, panel_colour, panel_rect, border_radius=5)
    pygame.draw.rect(screen, (180, 180, 180), panel_rect, 2, border_radius=5)

    

    logo = get_logo()
    logo_h = 0
    if logo:
        logo_h = 96
        
        logo_x = panel_rect.x + (panel_rect.width - 128) // 2
        logo_y = panel_rect.y
        
        screen.blit(logo, (logo_x, logo_y))

    pygame.draw.line(screen, (100, 100, 100), (panel_rect.x, logo_h + 10), (panel_rect.right, logo_h + 10), 1)

    header_height = 40
    header_start_y = panel_rect.y + logo_h 
    
    # Separator Line (Below header text)
    line_y = header_start_y + header_height
    pygame.draw.line(screen, (100, 100, 100), (panel_rect.x, line_y), (panel_rect.right, line_y), 1)

    # --- 3. Data Calculation ---
    total_laps = race.session.total_laps if hasattr(race.session, "total_laps") else "?"
    leaderboard = race.get_leaderboard(frame["time"])
    
    # Robust Lap Calculation
    current_lap = 1
    for d in frame["drivers"].values():
        if d["active"]:
            current_lap = max(current_lap, d["lap"])
    if current_lap == 0: current_lap = 1

    # Text Content
    if header_view_mode == 0: # LAP MODE
        label_text = "LAP"
        main_text = f"{current_lap}"
        sub_text = f"/ {total_laps}"
    else: 
        label_text = ""
        hours = int(frame["time"] // 3600)
        minutes = int((frame["time"] % 3600) // 60)
        seconds = int(frame["time"] % 60)
        main_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        sub_text = ""

    # Fonts
    head_lbl_font = pygame.font.SysFont("Arial", 14, bold=True)
    head_val_font = pygame.font.SysFont("Arial", 18, bold=True)
    head_sub_font = pygame.font.SysFont("Arial", 16, bold=True)

    s_label = head_lbl_font.render(label_text, True, (150, 150, 150))
    s_main = head_val_font.render(main_text, True, (255, 255, 255))
    s_sub = head_sub_font.render(sub_text, True, (150, 150, 150))

    # --- 4. Render Header Text (Centered vertically in header area) ---
    # Center Y is relative to where the header starts
    center_y = header_start_y + (header_height // 2)

    gap = 8
    total_w = s_label.get_width() + gap + s_main.get_width() + gap + s_sub.get_width()
    start_x = panel_rect.x + (panel_rect.width - total_w) // 2
    
    screen.blit(s_label, (start_x, center_y - s_label.get_height()//2))
    screen.blit(s_main, (start_x + s_label.get_width() + gap, center_y - s_main.get_height()//2))
    screen.blit(s_sub, (start_x + s_label.get_width() + gap + s_main.get_width() + gap, center_y - s_sub.get_height()//2 + 2))

    # Arrow Button
    arrow_x = panel_rect.right - 20
    arrow_pts = [(arrow_x-5, center_y-5), (arrow_x-5, center_y+5), (arrow_x+5, center_y)]
    pygame.draw.polygon(screen, (200, 200, 200), arrow_pts)
    
    toggle_btn_rect = pygame.Rect(arrow_x - 15, center_y - 15, 30, 30)

    # --- 5. Render Rows (Below Header) ---
    row_y = line_y + 10 # Start 10px below the separator line
    
    name_font = pygame.font.SysFont("Arial", 24, bold=True)
    position_font = pygame.font.SysFont("Arial", 22, bold=False)
    pit_font = pygame.font.SysFont("Arial", 16, bold=True)

    for entry in leaderboard:
        # ... (Row rendering logic remains the same) ...
        # Just ensure you use row_y here
        text_color = (150, 150, 150) if entry['DNF'] else (255, 255, 255)
        
        position_text = position_font.render(f"{entry['Position']:>2}", True, text_color)
        screen.blit(position_text, (panel_rect.x + 10, row_y))

        name_text = name_font.render(f"{entry['Abbreviation']}", True, text_color)
        screen.blit(name_text, (panel_rect.x + 50, row_y)) 
        
        if entry["Pitting"]:
            pit_box_rect = pygame.Rect(panel_rect.right + 2, row_y, 24, 24)
            pygame.draw.rect(screen, (255, 255, 255), pit_box_rect)
            p_text = pit_font.render("P", True, (0, 0, 0))
            p_rect = p_text.get_rect(center=pit_box_rect.center)
            screen.blit(p_text, p_rect)

        if entry["DNF"]:
            dnf_text = position_font.render("DNF", True, text_color)
            screen.blit(dnf_text, (panel_rect.right - 60, row_y))
        else:
            compound_name = entry.get("Compound", "UNKNOWN")
            compound_icon = get_compound_icon(compound_name)
            if compound_icon:
                icon_x = panel_rect.right - 40
                icon_y = row_y + (name_text.get_height() // 2) - (compound_icon.get_height() // 2)
                screen.blit(compound_icon, (icon_x, icon_y))
        
        row_y += 30

    return toggle_btn_rect
    
    