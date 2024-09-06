import mido
import asyncio
import signal
import sys
import struct
import socket
import colorsys
from led import Led
from collections import deque

inputs = mido.get_input_names()

# detect inputs
if len(inputs) == 0:
    print("[!] No inputs detected: " + str(inputs))
else:
    print("[+] Inputs detected: " + str(inputs))

# general variables
wled_connection = None
loop = None

# [usr] assign this to the LED count
led_count = 300 

# [usr] change this to 'true' to enable gradient mode:
gradient = True

# animation task dict (don't touch!)
note_task_dict = {}

# initializing the render array
render_notes = [Led(-1, [0, 0, 0]) for _ in range(led_count)]

if(gradient):
    print("[+] Gradient setting on!")
    ratio = 360/led_count
    # evenly distributing the leds:
    for i in range(led_count - 1):
        hue_val = (int)(i * ratio)
        render_notes[i].color = [hue_val, 100, 100]

# getting a socket on the ULED
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
addr = ("10.0.0.60", 21324)

# [usr] waterfall size; changing this variable will make the animation longer at the expense of performance
waterfall_size = 9

# [usr] change this to edit the FPS of the animation.
animation_fps = 60

# [usr] change this to edit the timeout (time it takes for control to be handed back (in seconds))
timeout = 20

# [usr] change this to edit the color for non-gradient modes
color = [255, 0, 255] 

async def waterfall_animation(note : int, on : bool) -> None:
    # plays the animation, or slowly stops it, depending on 'on'
    global render_notes
    startNote = note - waterfall_size//2

    for i in range(waterfall_size):
        if on:
            render_notes[startNote + i].layer += 1
            await asyncio.sleep(1/animation_fps)
            await update_leds(note)
            
        else:
            render_notes[startNote + i].layer -= 1
            await asyncio.sleep(1/animation_fps)
            await update_leds(note)
        
    await update_leds(note)
    
def print_render_notes():
    # debug printout for... debugging
    global render_notes
    for i in range(len(render_notes)):
        print("i: {index} | layer: {layer} | color: {color}".format(index = i, 
                                                                    layer = render_notes[i].layer, 
                                                                    color = render_notes[i].color))

def hsv_to_rgb(h, s, v):
    # normalize 
    h = h / 360.0
    s = s / 100.0
    v = v / 100.0
    
    # convert
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    
    # Scale to 255
    r = int(r * 255)
    g = int(g * 255)
    b = int(b * 255)

    return [r, g, b]
    
async def update_leds(note : int) -> None:
    # looks through the render_notes array and simply plays a color depending on the layer
    i = 0
    rgbColor = color
    
    # protocol header
    payload = struct.pack(">BBH", 4, timeout, 0) # note to self, 0 is the starting uled
    while(i < len(render_notes)):
        # for gradient
        if(gradient):
            rgbColor = hsv_to_rgb(render_notes[i].color[0], 
                                  render_notes[i].color[1], 
                                  render_notes[i].color[2])

        if(render_notes[i].layer <= -1):
            payload += struct.pack("BBB", 5, 5, 5)
        else:
            payload += struct.pack("BBB", rgbColor[0], rgbColor[1], rgbColor[2])
        i += 1
    
    # send the whole packet out (flash render_notes)
    sock.sendto(payload, addr)

async def handle_keypress(message):
    # called whenever we receive a signal from the MIDI device
    # the midi device is constantly pinging, with a clock signal
    global note_task_dict
    global render_notes

    if message.type == 'note_on' and message.velocity != 0:
        # note pressed 
        note = int(message.note)
        note -= 21
        note = (int)(float(note) * (led_count / 88))

        # start the animation and create a pointer to it
        task = loop.create_task(waterfall_animation(note, True))
        note_task_dict[note] = task

    elif message.type == 'note_on' and message.velocity == 0:
        # note depressed
        note = int(message.note)
        note -= 21
        note = (int)(float(note) * (led_count / 88))

        # turn off / cancel the animation (update the render_notes table)
        note_task_dict[note].cancel()
        del note_task_dict[note]
        
        # create a task to quit the animation
        loop.create_task(waterfall_animation(note, False))

# whenever ctrl+c is hit, this runs. closes the piano MIDI input
def exit_piano():
    print("[+] Exiting...")
    piano.close()
    sys.exit(0)

def signal_handler(sig, frame):
    exit_piano()

signal.signal(signal.SIGINT, signal_handler)

# looking for the piano
try:
    piano = mido.open_input('Digital Piano 0', callback=lambda msg: asyncio.run_coroutine_threadsafe(handle_keypress(msg), loop))
except Exception as e:
    print(f"[!] Piano not detected, aborting... {e}")
    sys.exit(0)

print("[+] Ready!")

async def main() -> None:
    global wled_connection
    global loop
    loop = asyncio.get_running_loop()
    # now wait for input...
    while True:
        await asyncio.sleep(1)
        

if __name__ == "__main__":
    asyncio.run(main())