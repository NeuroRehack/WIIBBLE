#WIBBLE - Wii Balance Board Live Environment
import hid
import pygame
import numpy as np
import time
import pygame_gui
import subprocess
import time
import os
import sys
from board_connection import try_connection
DLL_RELATIVE_PATH = r'.\WiiBalanceBoardLibrary\bin\Debug\net48\WiiBalanceBoardLibrary.dll'

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores the path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Then use resource_path function to access images
icon_path = resource_path("images/logo.png")
person_image_path = resource_path("images/logoPerson.png")
image_paths = [resource_path(f"images/wii{i}.png") for i in range(3)]
connection_path = resource_path("images/connection.png")

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
    try:
        data = device.read(32)
        return data
    except IOError as e:
        print(f"Failed to read data: {e}")
        return None

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
    while i < 10:
        data = device.read(32)
        if data:
            data = np.array(data)
            for val in data_struct.values():
                val["tare"] += data[val["rawIndex"]] + data[val["rawIndex"] + 1] / 255
            i += 1
        print("*" * i)
    for val in data_struct.values():
        val["tare"] /= 10
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
    # print(f"Measured weight: {total_weight}")
    return total_weight

def wait_for_key():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return
            if event.type == pygame.QUIT:
                pygame.quit()
                return -1
def display_message(screen, font, message, color, position):
    text = font.render(message, True, color)
    screen.blit(text, position)
    

def show_step_on_board(screen,image):
    mid_screen = SCREEN_WIDTH / 1.8
    mid_height = SCREEN_HEIGHT / 2.9
    font = pygame.font.Font(None, 82)
    screen.fill((110, 159, 168))
    # display an image
    imgsize = image.get_size()
    w, h = imgsize
    # scale the image to the screen size
    image = pygame.transform.scale(image, (0.8*SCREEN_HEIGHT*w//h, 0.8*SCREEN_HEIGHT))
    screen.blit(image, (SCREEN_WIDTH//2.2-w//2, SCREEN_HEIGHT//1.5-h//2))
    display_message(screen, font, "         Step", (250, 250, 250), (mid_screen, mid_height))
    display_message(screen,font ,"\n          ON", (0, 250, 0), (mid_screen, mid_height))
    display_message(screen, font, "\n\n     the board", (250, 250, 250), (mid_screen, mid_height))
    display_message(screen,font ,"\n\n\n\n\n\n and stand still", (250, 250, 250), (mid_screen, mid_height))
    pygame.display.flip()

def show_step_off_board(screen,image):
    mid_screen = SCREEN_WIDTH / 1.8
    mid_height = SCREEN_HEIGHT / 2.9
    
    
    font = pygame.font.Font(None, 82)
    screen.fill((110, 159, 168))
    # display an image
    imgsize = image.get_size()
    w, h = imgsize
    # scale the image to the screen size
    image = pygame.transform.scale(image, (0.8*SCREEN_HEIGHT*w//h, 0.8*SCREEN_HEIGHT))
    screen.blit(image, (SCREEN_WIDTH//2.2-w//2, SCREEN_HEIGHT//1.5-h//2))
    display_message(screen, font, "         Step", (250, 250, 250), (mid_screen, mid_height))
    display_message(screen, font, "\n         OFF", (250, 0, 0), (mid_screen, mid_height))
    display_message(screen, font, "\n\n     the board", (250, 250, 250), (mid_screen, mid_height))
    pygame.display.flip()
    

def sensitivity_calibration(device, screen):
    tare_weight = measure_weight(device)

  
    images = [pygame.image.load(img_path) for img_path in image_paths]
    
    last_weight = tare_weight
    counter = 0
    #fill the screen with black
    maxCounter = 20
    i=0
    k = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                device.close()
                return -1
        weight = measure_weight(device)
        if counter == maxCounter:
            break
        if (abs(weight - last_weight) < 1) and (weight - tare_weight > 20):
            counter += 1
        
        else:
            # i +=1
            # if i%10 == 0:
            #     k = (k+1)%3
            #     show_step_on_board(screen,images[k])
            #     i = 0
            counter = 0
            last_weight = weight
        # draw a circle the gets completed as the counter increases
        
    
        show_step_on_board(screen,images[2])
        pygame.draw.arc(screen, (0, 250, 0), (SCREEN_WIDTH*0.54, SCREEN_HEIGHT*0.2, SCREEN_HEIGHT//2, SCREEN_HEIGHT//2), 0, 2 * np.pi *counter / maxCounter, 10)# 
        pygame.display.flip()
    return weight

def wait_for_tare(device, screen):
    tare_weight = measure_weight(device)
  
    images = [pygame.image.load(img_path) for img_path in image_paths]


    
    last_weight = tare_weight
    counter = 0
    #fill the screen with black
    maxCounter = 20
    i=0
    k = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                device.close()
                return -1
        weight = measure_weight(device)
        if counter == maxCounter:
            break
        if (abs(weight - last_weight) < 1) and (weight < 530):
            counter += 1
        
        else:
            # i +=1
            # if i%10 == 0:
            #     k = (k+1)%3
            #     show_step_off_board(screen,images[k])
            #     i = 0
            counter = 0
            last_weight = weight
        # draw a circle the gets completed as the counter increases
        
    
        show_step_off_board(screen,images[2])
        pygame.draw.arc(screen, (250, 0, 0), (SCREEN_WIDTH*0.54, SCREEN_HEIGHT*0.2, SCREEN_HEIGHT//2, SCREEN_HEIGHT//2), 0, 2 * np.pi *counter / maxCounter, 10)# 
        pygame.display.flip()
    return weight
                
    
def button_pressed():
    print("Button pressed")
    
    
def try_connection_loop(screen):
    # a function that tries to connect to the balance board
    font = pygame.font.Font(None, 82)
    mid_screen = SCREEN_WIDTH / 2.5
    mid_height = SCREEN_HEIGHT / 2.9
    
    
    while True:
        screen.fill((110, 159, 168))
        display_message(screen, font, "Trying to connect", (250, 250, 250), (mid_screen, mid_height))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
        state = try_connection(resource_path(DLL_RELATIVE_PATH))
        if state == 0:
            break
        elif state == 1:
            screen.fill((110, 159, 168))
            # load the image
            image = pygame.image.load(connection_path)
            imgsize = image.get_size()
            w, h = imgsize
            # scale the image to the screen size
            image = pygame.transform.scale(image, (0.8*SCREEN_HEIGHT*w//h, 0.8*SCREEN_HEIGHT))
            w,h = image.get_size()
            screen.blit(image, (SCREEN_WIDTH//2-w//2, SCREEN_HEIGHT//2-h//2))
            display_message(screen, font, "Failed to connect", (250, 0, 0), (mid_screen*0.6, mid_height))
            display_message(screen, font, "\nCheck the following: ", (250, 250, 250), (mid_screen*0.6, mid_height))
            display_message(screen, font, "\n\n    1. bluetooth is enabled on your computer", (250, 250, 250), (mid_screen*0.6, mid_height))
            display_message(screen, font, "\n\n\n    2. the board is paired to your computer", (250, 250, 250), (mid_screen*0.6, mid_height))
            display_message(screen, font, "\n\n\n\n    3. the board is on and blinking blue", (250, 250, 250), (mid_screen*0.6, mid_height))
            display_message(screen, font, "\n\n\n\n\nand press enter", (250, 250, 250), (mid_screen*0.6, mid_height))
            pygame.display.flip()
            wait_for_key()

        
def main():
    global weight, SCREEN_WIDTH, SCREEN_HEIGHT, data_struct, historical_coords
    data_struct = {
        "top_right": {"rawIndex": 3, "tare": 0},
        "bottom_right": {"rawIndex": 5, "tare": 0},
        "top_left": {"rawIndex": 7, "tare": 0},
        "bottom_left": {"rawIndex": 9, "tare": 0}
    }
    clickedLocations = []

    screen = pygame.display.set_mode((int(SCREEN_WIDTH), int(SCREEN_HEIGHT)), pygame.RESIZABLE)
    pygame.display.set_caption("WIBBLE - Wii Balance Board Live Environment")
    # set icon
    icon = pygame.image.load(icon_path)
    pygame.display.set_icon(icon)
    
    manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Create a button
    button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, 0), (150, 50)),
                                            text='RESTART',
                                            manager=manager,
                                            object_id="#settings_button",

                                            )
    reset_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((150, 0), (150, 50)),
                                            text='RESET SCREEN',
                                            manager=manager,
                                            object_id="#reset_button",
                                            
                                            )
    clock = pygame.time.Clock()
    
    try:
        try_connection_loop(screen)
    except:
        print("Failed to connect")
        return 1
    # Connect to the Wii Balance Board
    device = connect_wii_board()
    if device:
        
     
        weight = measure_weight(device)
        wait_for_tare(device, screen)
        # print(f"Weight: {weight}")
        # status = wait_for_key()
        # if status == -1:
        #     return 1
        try:    
            tare(device)
        except:
            print("Failed to tare")
            device.close()
            return 1    
        weight = sensitivity_calibration(device, screen)
        if weight == -1:
            return 1
        
        max_x, max_y, min_x, min_y = 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT
        run = True
        personImage = pygame.image.load(person_image_path)

        try:
            while run:
                time_delta = clock.tick(1000)/1000.0 #

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        device.close()
                        return 1
                    elif event.type == pygame.VIDEORESIZE:
                        SCREEN_WIDTH, SCREEN_HEIGHT = event.w, event.h
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                    elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == button:
                            run = False
                        if event.ui_element == reset_button:
                            clickedLocations = []
                            historical_coords = [(0, 0) for _ in range(100)]
                            max_x, max_y, min_x, min_y = 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT
                            
                    # if the person click the left mouse button
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        x,y = event.pos
                        clickedLocations.append((x,y))
                        
                    manager.process_events(event)
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
                    # add circle to the center
                    pygame.draw.circle(screen, (0, 0, 0), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), int(SCREEN_WIDTH / 50))
                    pygame.draw.circle(screen, (255,255,255), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), int(SCREEN_WIDTH / 20))
                    
                    for loc in clickedLocations:
                        pygame.draw.circle(screen, (255, 0, 0), loc,50 )
                        # if the distance between the current location and the ball is less than 20 pixels
                        #create sparkles
                        if np.linalg.norm(np.array(loc) - np.array([ball_x, ball_y])) < 50:
                            pygame.draw.circle(screen, (0, 255, 0), loc, 50)
                                
                    
                    
                    # Draw historical coordinates and current ball position
                    trail_color = (110, 159, 168)
                    for i in range(1, len(historical_coords)):
                        pygame.draw.circle(screen, (i * 255 / len(historical_coords), 0, 0), historical_coords[i], i * 20 / len(historical_coords))
                        pygame.draw.circle(screen, (i * trail_color[0] / len(historical_coords), 
                                                    i * trail_color[1] / len(historical_coords), 
                                                    i * trail_color[2] / len(historical_coords)), 
                                           historical_coords[i], i * 20 / len(historical_coords))
                    pygame.draw.circle(screen, (110, 159, 168), (ball_x, ball_y), 20)
                    


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
                    screen.blit(text, (SCREEN_WIDTH / 2.4, SCREEN_HEIGHT * 0.9))
                    pygame.draw.rect(screen, (0, 0, 0), (min_x + SCREEN_WIDTH // 2, min_y + SCREEN_HEIGHT // 2, max_x - min_x, max_y - min_y), int(SCREEN_WIDTH / 200))
                    
                    imgsize = personImage.get_size()
                    w, h = imgsize
                    personImageScaled = pygame.transform.scale(personImage, (0.1*SCREEN_HEIGHT*w//h, 0.1*SCREEN_HEIGHT))
                    w,h = personImageScaled.get_size()
                    screen.blit(personImageScaled, (ball_x-w//2, ball_y-h))
                    
                manager.update(time_delta)
                manager.draw_ui(screen)
                pygame.display.flip()
            device.close()
            return 0
            
                

        except KeyboardInterrupt:
            print("Disconnected")
            device.close()

if __name__ == "__main__":
    # call an exe function
    
    while True:
        out = main()
        if out == 1:
            break

