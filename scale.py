import hid
import pygame
import numpy as np
import time

# Constants
VENDOR_ID = 0x057e  # Nintendo Co., Ltd
PRODUCT_ID = 0x0306  # Balance Board
SCALE_FACTOR = 2.6441910428028423

# Initialize pygame and get screen size
pygame.init()
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w * 1
SCREEN_HEIGHT = info.current_h * 0.9

# Data structure for balance board
data_struct = {
    "top_right": {"rawIndex": 3, "tare": 0},
    "bottom_right": {"rawIndex": 5, "tare": 0},
    "top_left": {"rawIndex": 7, "tare": 0},
    "bottom_left": {"rawIndex": 9, "tare": 0}
}

historical_coords = [(0, 0) for _ in range(100)]
weight = 0.1

def connect_wii_board():
    try:
        print("Connecting to Wii Balance Board...")
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        print("Connected successfully!")
        return device
    except IOError as e:
        print(f"Failed to connect: {e}")
        return None

def read_data(device):
    return device.read(32)

def parse_data(data):
    corners = {}
    for key, val in data_struct.items():
        raw_index = val["rawIndex"]
        tare = val["tare"]
        corners[key] = round((data[raw_index] + data[raw_index + 1] / 255 - tare) * SCALE_FACTOR, 2)
    return corners

def tare(device):
    print("Taring...")
    i = 0
    while i < 100:
        data = device.read(32)
        if data:
            data = np.array(data)
            for val in data_struct.values():
                val["tare"] += data[val["rawIndex"]] + data[val["rawIndex"] + 1] / 255
            i += 1
        print("*" * i)
    for val in data_struct.values():
        val["tare"] /= 100
    print(f"Tare: {data_struct}")

def calculate_coordinates(top_left, top_right, bottom_left, bottom_right):
    top_left /= -weight
    top_right /= -weight
    bottom_left /= -weight
    bottom_right /= -weight
    x = (top_left + bottom_left) / 2 - (top_right + bottom_right) / 2
    y = (top_left + top_right) / 2 - (bottom_left + bottom_right) / 2
    x *= SCREEN_WIDTH * 0.9
    y *= SCREEN_HEIGHT * 0.9
    return x, y

def measure_weight(device):
    weight_vals = [0, 0, 0, 0]
    for _ in range(10):
        data = read_data(device)
        if data:
            corners = parse_data(data)
            for i, key in enumerate(corners.keys()):
                weight_vals[i] += corners[key]
    weight_vals = [val / 10 for val in weight_vals]
    total_weight = sum(weight_vals)
    print(f"Measured weight: {total_weight}")
    return total_weight

def wait_for_key():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return
def display_message(screen, font, message, color, position):
    text = font.render(message, True, color)
    screen.blit(text, position)
    

def sensitivity_calibration(device, screen):
    font = pygame.font.Font(None, 82)
    mid_screen = SCREEN_WIDTH / 2.5
    mid_height = SCREEN_HEIGHT / 2.9

    tare_weight = measure_weight(device)
    screen.fill((0, 0, 0))
    display_message(screen, font, "        Step", (250, 250, 250), (mid_screen, mid_height))
    display_message(screen,font ,"\n         ON", (0, 250, 0), (mid_screen, mid_height))
    display_message(screen, font, "\n\n    the board", (250, 250, 250), (mid_screen, mid_height))
    display_message(screen,font ,"\n\n\n\nand stand still", (250, 250, 250), (mid_screen, mid_height))
    pygame.display.flip()
    
    while True:
        weight = measure_weight(device)
        if weight - tare_weight > 20:
            break
        else:
            time.sleep(1)
    last_weight = weight
    counter = 0
    #fill the screen with black
    maxCounter = 50
    while True:
        weight = measure_weight(device)
        if counter == maxCounter:
            break
        if (abs(weight - last_weight) < 1) and (weight - tare_weight > 20):
            counter += 1
            screen.fill((0, 0, 0))
            display_message(screen, font, "        Step", (250, 250, 250), (mid_screen, mid_height))
            display_message(screen,font ,"\n         ON", (0, 250, 0), (mid_screen, mid_height))
            display_message(screen, font, "\n\n    the board", (250, 250, 250), (mid_screen, mid_height))
            display_message(screen,font ,"\n\n\n\nand stand still", (250, 250, 250), (mid_screen, mid_height))
            # draw a circle the gets completed as the counter increases
            pygame.display.flip()
        
        else:
            counter = 0
            last_weight = weight
        # draw a circle the gets completed as the counter increases
        pygame.draw.arc(screen, (0, 250, 0), (SCREEN_WIDTH//2-SCREEN_HEIGHT//1.5//2, SCREEN_HEIGHT//2-SCREEN_HEIGHT//1.5//2, SCREEN_HEIGHT//1.5, SCREEN_HEIGHT//1.5), 0, 2 * np.pi *counter / maxCounter, 10)
        pygame.display.flip()
        time.sleep(0.1)
    return weight
                
    
    
def main():
    global weight, SCREEN_WIDTH, SCREEN_HEIGHT

    screen = pygame.display.set_mode((int(SCREEN_WIDTH), int(SCREEN_HEIGHT)), pygame.RESIZABLE)
    pygame.display.set_caption("Wii Balance Board Ball")

    device = connect_wii_board()
    if device:
        mid_screen = SCREEN_WIDTH / 2.5
        mid_height = SCREEN_HEIGHT / 2.9
        
        
        font = pygame.font.Font(None, 82)
        display_message(screen, font, "        Step", (250, 250, 250), (mid_screen, mid_height))
        display_message(screen, font, "\n        OFF", (250, 0, 0), (mid_screen, mid_height))
        display_message(screen, font, "\n\n    the board", (250, 250, 250), (mid_screen, mid_height))
        display_message(screen, font, "\n\n\n\nand press enter", (250, 250, 250), (mid_screen, mid_height))
        pygame.display.flip()
        wait_for_key()
        
        tare(device)
        
        weight = sensitivity_calibration(device, screen)
        
        sensitivity = weight

        max_x, max_y, min_x, min_y = 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT

        try:
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        device.close()
                        return
                    elif event.type == pygame.VIDEORESIZE:
                        SCREEN_WIDTH, SCREEN_HEIGHT = event.w, event.h
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                
                data = read_data(device)
                if data:
                    corners = parse_data(data)
                    top_right, bottom_right, top_left, bottom_left = corners.values()
                    x, y = calculate_coordinates(top_left, top_right, bottom_left, bottom_right)
                    
                    # Update min and max values for x and y
                    max_x, max_y = max(max_x, x), max(max_y, y)
                    min_x, min_y = min(min_x, x), min(min_y, y)

                    # Update historical coordinates
                    curr_weight = sum(corners.values())
                    screen.fill((255, 255, 255))
                    ball_x = SCREEN_WIDTH // 2 + int(x)
                    ball_y = SCREEN_HEIGHT // 2 + int(y)
                    historical_coords.pop(0)
                    historical_coords.append((ball_x, ball_y))
                    
                    # Draw Center Lines
                    pygame.draw.line(screen, (0, 0, 0), (0, SCREEN_HEIGHT // 2), (SCREEN_WIDTH, SCREEN_HEIGHT // 2), int(SCREEN_WIDTH / 200))
                    pygame.draw.line(screen, (0, 0, 0), (SCREEN_WIDTH // 2, 0), (SCREEN_WIDTH // 2, SCREEN_HEIGHT), int(SCREEN_WIDTH / 200))
                    
                    # Draw historical coordinates and current ball position
                    for i in range(1, len(historical_coords)):
                        pygame.draw.circle(screen, (i * 255 / len(historical_coords), 0, 0), historical_coords[i], i * 20 / len(historical_coords))
                    pygame.draw.circle(screen, (255, 0, 0), (ball_x, ball_y), 20)


                    # Draw weight distribution bar at the bottom of the screen
                    perc_left = (top_left + bottom_left) / weight # compute the percentage of weight on the left side
                    perc_right = (top_right + bottom_right) / weight # compute the percentage of weight on the right side
                    pygame.draw.rect(screen, (255, 0, 0), (0, SCREEN_HEIGHT - 20, int(SCREEN_WIDTH * weight / weight), 20)) # draw a red rectangle at the bottom of the screen
                    x0 = SCREEN_WIDTH // 2 - perc_left * SCREEN_WIDTH // 2 # compute the x coordinate of the left weight distribution
                    x1 = SCREEN_WIDTH // 2 - x0                             # compute the width of the left weight distribution
                    pygame.draw.rect(screen, (0, 255, 0), (x0, SCREEN_HEIGHT - 20, x1, 20)) # draw the left weight distribution
                    x0 = SCREEN_WIDTH // 2  # compute the x coordinate of the right weight distribution
                    x1 = perc_right * SCREEN_WIDTH // 2 # compute the width of the right weight distribution
                    pygame.draw.rect(screen, (0, 255, 0), (x0, SCREEN_HEIGHT - 20, x1, 20)) # draw the right weight distribution
                    
                    # Display the percentage of weight on each side and the total weight
                    font = pygame.font.Font(None, 64)
                    text = font.render(f"{int(perc_left * 100)}%", True, (0, 0, 0))
                    screen.blit(text, (50, SCREEN_HEIGHT - 100))
                    text = font.render(f"{int(perc_right * 100)}%", True, (0, 0, 0))
                    screen.blit(text, (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100))
                    text = font.render(f"{int(curr_weight)} kg", True, (0, 0, 0))
                    screen.blit(text, (SCREEN_WIDTH / 2.1, SCREEN_HEIGHT * 0.9))
                    pygame.draw.rect(screen, (0, 0, 0), (min_x + SCREEN_WIDTH // 2, min_y + SCREEN_HEIGHT // 2, max_x - min_x, max_y - min_y), int(SCREEN_WIDTH / 200))
                    
                pygame.display.flip()
        except KeyboardInterrupt:
            print("Disconnected")
            device.close()

if __name__ == "__main__":
    main()

