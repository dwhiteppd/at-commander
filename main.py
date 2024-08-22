import tkinter as tk
from tkinter import *
from tkinter import font, ttk
import serial
from typing import Union, Tuple, List

import serial.tools
import serial.tools.list_ports


root = tk.Tk()
root.title("AT Commander")
root.geometry("600x500")

BAUD_OPTIONS    = [115200, 9600]
DEFAULT_BAUD    = 115200
PADDING_X       = 5
PADDING_Y       = 5
LABEL_FONT      = font.Font(root=root, family="Consolas", size=12)
MONITOR_FONT   = font.Font(root=root, family="Consolas", size=12)


def get_devices() -> List[str]:
    devices = serial.tools.list_ports.comports()
    port_list = []
    for dev in devices:
        port_list.append(dev.name)
    return port_list

def get_input() -> None:
    print(serial_monitor.get("1.0",END))

def get_cnum() -> str:
    thingy91 = serial.Serial(port=port_svar.get(), baudrate=baud_ivar.get())
    
    print("Waiting for Response...")
    pos = serial_monitor.index(tk.INSERT)
    print("Index: ", pos)
    thingy91.write("AT+CNUM\r\n".encode())
    while not "+CNUM" in serial_monitor.get(pos, END):
        serial_monitor.insert(pos,chars=thingy91.read_until().decode())
    print("Done")


###################################################################################################
# WIDGETS

# NOTEBOOK - Contains tabs
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')
settings_tab = ttk.Frame(notebook)
commands_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")
notebook.add(commands_tab, text="Commands")


# COMPORT WIDGETS
port_list = get_devices()

port_frame = tk.Frame(settings_tab)
port_frame.pack(anchor=tk.W)

port_labl = Label(port_frame, text="Port:", font=LABEL_FONT)
port_labl.pack(side=tk.LEFT, anchor=tk.W, padx=PADDING_X, pady=PADDING_Y)

port_svar = StringVar(root)
port_svar.set("Select Port")

port_menu = OptionMenu(port_frame, port_svar, *port_list)
port_menu.config(font=LABEL_FONT)
port_menu.pack(side=tk.LEFT, anchor=tk.W, padx=PADDING_X, pady=PADDING_Y)


# BAUDRATE WIDGETS
baud_frame = tk.Frame(settings_tab)
baud_frame.pack(anchor=tk.W)
baud_labl = Label(baud_frame, text="Baud:", font=LABEL_FONT)
baud_labl.pack(side=tk.LEFT, anchor=tk.W, padx=PADDING_X, pady=PADDING_Y)
baud_ivar = IntVar(root)
baud_ivar.set(DEFAULT_BAUD)
baud_menu = OptionMenu(baud_frame, baud_ivar, *BAUD_OPTIONS)
baud_menu.config(font=LABEL_FONT)
baud_menu.pack(side=tk.LEFT, anchor=tk.W, padx=PADDING_X, pady=PADDING_Y)


# MONITOR WIDGETS
serial_monitor = Text(root, height="100", width="150", fg="white", bg="black", blockcursor=True, insertbackground="green", font=MONITOR_FONT)
button = Button(commands_tab, text="AT+CNUM", command=get_cnum, font=LABEL_FONT)
button.pack()
serial_monitor.pack(padx=PADDING_X, pady=PADDING_Y)





root.mainloop()
