import hid
import pygame
#pyinstaller with import hid
#pyinstaller --onefile --hidden-import=hid --hidden-import=pygame scale.py
# get screen size
pygame.init()

info = pygame.display.Info()


VENDOR_ID = 0x057e  # Nintendo Co., Ltd
PRODUCT_ID = 0x0306  # Balance Board

SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

coordinates = {"top_left": 7, "top_right": 3, "bottom_left": 9, "bottom_right": 5}
tare_vals = [0, 0, 0, 0]
sensitivity = 1.0
historicalCoords = [(0,0) for _ in range(100)]
scaleFactor = 2.6441910428028423
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
    data = device.read(32)  # Read 32 bytes
    return data

def parse_data(data):
    global tare_vals
    # extract the 4 sensors data from the 32 bytes and apply the tare_vals
    top_left = data[coordinates['top_left']] + data[coordinates['top_left']+1]/255
    top_right = data[coordinates['top_right']] + data[coordinates['top_right']+1]/255
    bottom_left = data[coordinates['bottom_left']] + data[coordinates['bottom_left']+1]/255
    bottom_right = data[coordinates['bottom_right']] + data[coordinates['bottom_right']+1]/255
    # apply tare_vals
    top_left -= tare_vals[0]    
    top_right -= tare_vals[1]
    bottom_left -= tare_vals[2]
    bottom_right -= tare_vals[3]
    # apply scaleFactor
    top_left = top_left * scaleFactor
    top_right = top_right * scaleFactor
    bottom_left = bottom_left * scaleFactor
    bottom_right = bottom_right * scaleFactor
    
    # round to 2 decimal places
    top_left = round(top_left, 2)
    top_right = round(top_right, 2)
    bottom_left = round(bottom_left, 2)
    bottom_right = round(bottom_right, 2)
    return top_left, top_right, bottom_left, bottom_right

def tare(device):
    # compute the average of the 10 first readings
    print("Taring...")
    global tare_vals
    i = 0
    while i < 100:
        data = device.read(32)
        print(data)
        if data:
            tare_vals[0] += data[coordinates['top_left']] + data[coordinates['top_left']+1]/255
            tare_vals[1] += data[coordinates['top_right']] + data[coordinates['top_right']+1]/255
            tare_vals[2] += data[coordinates['bottom_left']] + data[coordinates['bottom_left']+1]/255
            tare_vals[3] += data[coordinates['bottom_right']] + data[coordinates['bottom_right']+1]/255
            i += 1
    tare_vals[0] /= 100
    tare_vals[1] /= 100
    tare_vals[2] /= 100
    tare_vals[3] /= 100
    print(f"Tare: {tare_vals}")

def calculate_coordinates(top_left, top_right, bottom_left, bottom_right):
    # scale values up
    top_left /= -weight
    top_right /= -weight
    bottom_left /= -weight
    bottom_right /= -weight
    
    # Simple average for x and y position, adjust as necessary for your setup
    x = (top_left + bottom_left) / 2 - (top_right + bottom_right) / 2
    y = (top_left + top_right) / 2 - (bottom_left + bottom_right) / 2
    
    x *= SCREEN_WIDTH * 0.9
    y *= SCREEN_HEIGHT * 0.9
    return x, y

def calibrate(known_weight, device):
    global scaleFactor
    scaleFactor = 1
    weight = measure_weight(device)
    scaleFactor = known_weight / weight
    


def measure_weight(device):
    weight_vals = [0, 0, 0, 0]
    for _ in range(10):
        data = read_data(device)
        if data:
            top_left, top_right, bottom_left, bottom_right = parse_data(data)
            weight_vals[0] += top_left
            weight_vals[1] += top_right
            weight_vals[2] += bottom_left
            weight_vals[3] += bottom_right
    weight_vals = [val / 10 for val in weight_vals]
    weight = sum(weight_vals)
    print(f"Measured weight: {weight}")
    return weight


def wait_for_key():
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return

def main():
    global sensitivity, weight

    # screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Wii Balance Board Ball")

    device = connect_wii_board()
    if device:
        midScreen = SCREEN_WIDTH/2.3
        midHeight = SCREEN_HEIGHT/2.5
        font = pygame.font.Font(None, 82)
        text = font.render("     Step \n\n\n\nthe board", True, (250,250,250))
        screen.blit(text, (midScreen, midHeight))
        text = font.render("\n\n     OFF\n", True, (250,0,0))
        screen.blit(text, (midScreen, midHeight))
        font = pygame.font.Font(None, 62)
        # and press enter
        text = font.render("\n\n\n\n\n\n\n\n\n\nand press enter", True, (250,250,250))
        screen.blit(text, (midScreen, midHeight))
        pygame.display.flip()  # Update display
        wait_for_key()
        tare(device)
        # clear screen
        screen.fill((0, 0, 0))
        text = font.render("    Step \n\nthe board", True, (250,250,250))
        screen.blit(text, (midScreen, midHeight))
        text = font.render("\n     ON", True, (0,250,0))
        screen.blit(text, (midScreen, midHeight))
        pygame.display.flip()  # Update display
        wait_for_key()
        weight = measure_weight(device)
        sensitivity = weight # Adjust sensitivity based on weight

        maxX = 0
        maxY = 0
        minx = SCREEN_WIDTH
        miny = SCREEN_HEIGHT
        try:
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        device.close()
                        return
                  
                
                data = read_data(device)
                if data:
                    top_left, top_right, bottom_left, bottom_right = parse_data(data)
                    x, y = calculate_coordinates(top_left, top_right, bottom_left, bottom_right)
                    
                    
                    maxX = max(maxX, x)
                    maxY = max(maxY, y)
                    minx = min(minx, x)
                    miny = min(miny, y)

                    
                    # print(f"Top left: {top_left}, Top right: {top_right}, Bottom left: {bottom_left}, Bottom right: {bottom_right}")
                    # print(f"Ball position: x={x}, y={y}")
                    curr_weight = top_left + top_right + bottom_left + bottom_right
                    screen.fill((255, 255, 255))  # Clear screen with white
                    ball_x = SCREEN_WIDTH//2 + int(x)  # Center the x coordinate
                    ball_y = SCREEN_HEIGHT//2 + int(y)  # Center the y coordinate
                    historicalCoords.pop(0)
                    historicalCoords.append((ball_x, ball_y))
                    # add a circle on the canvas of diameter 10
                    # pygame.draw.circle(screen, (0, 0, 0), (SCREEN_WIDTH//2, SCREEN_HEIGHT//2), 500)
                    # pygame.draw.circle(screen, (255,255,255), (SCREEN_WIDTH//2, SCREEN_HEIGHT//2), 490)
                    pygame.draw.line(screen, (0, 0, 0), (0, SCREEN_HEIGHT // 2), (SCREEN_WIDTH, SCREEN_HEIGHT // 2), int(SCREEN_WIDTH/200))
                    pygame.draw.line(screen, (0, 0, 0), (SCREEN_WIDTH // 2, 0), (SCREEN_WIDTH // 2, SCREEN_HEIGHT), int(SCREEN_WIDTH/200))
                    for i in range(1, len(historicalCoords)):
                        pygame.draw.circle(screen, (i*255/len(historicalCoords), 0, 0), historicalCoords[i], i*20/len(historicalCoords))
                    pygame.draw.circle(screen, (255, 0, 0), (ball_x, ball_y), 20)  # Draw red ball
                    
                                        
                    perc_left = (top_left + bottom_left) / weight
                    perc_right = (top_right + bottom_right) / weight
                        
                    # add horizontal bar to show weight
                    pygame.draw.rect(screen, (0, 0, 0), (0, SCREEN_HEIGHT - 10, SCREEN_WIDTH, 10))
                    pygame.draw.rect(screen, (255, 0, 0), (0, SCREEN_HEIGHT - 20, int(SCREEN_WIDTH * weight / weight), 20))
                    # pygame.draw.rect(screen, (0, 255, 0), (0, SCREEN_HEIGHT - 20, int(SCREEN_WIDTH * curr_weight / weight), 20)) # (screen, color, (x, y, width, height)
                    x0 = SCREEN_WIDTH//2 - perc_left * SCREEN_WIDTH//2
                    x1 = SCREEN_WIDTH//2 - x0
                    pygame.draw.rect(screen, (0, 255, 0), (x0, SCREEN_HEIGHT - 20, x1, 20))
                    x0 = SCREEN_WIDTH//2 
                    x1 = perc_right * SCREEN_WIDTH//2
                    pygame.draw.rect(screen, (0, 255, 0), (x0, SCREEN_HEIGHT - 20, x1, 20))
                    
                    
                    # print the weight of each quadrant
                    font = pygame.font.Font(None, 64)
                    
                    text = font.render(f"{round(perc_left*100,0)}%", True, (0, 0, 0))
                    screen.blit(text, (50, SCREEN_HEIGHT - 100))
                    text = font.render(f"{round(perc_right*100,0)}%", True, (0, 0, 0))
                    screen.blit(text, (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100))
                    #print total weight
                    text = font.render(f"Total weight: {round(curr_weight,0)} kg", True, (0, 0, 0))
                    screen.blit(text, (SCREEN_WIDTH/2.2, SCREEN_HEIGHT*0.9))
                    
                    # draw rectangle with max values and min values
                    pygame.draw.rect(screen, (0, 0, 0), (minx+ SCREEN_WIDTH//2, miny+ SCREEN_HEIGHT//2, maxX-minx, maxY-miny), int(SCREEN_WIDTH/200))
                                        
                pygame.display.flip()  # Update display


        except KeyboardInterrupt:
            print("Disconnected")
            device.close()

if __name__ == "__main__":
    main()
    # get board battery level
