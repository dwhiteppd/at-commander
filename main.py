# Devon White, PPD 2024
# AT Commander


import tkinter as tk
from tkinter import *
from tkinter import font, ttk
import serial
from typing import Union, Tuple, List, Optional

import serial.tools
import serial.tools.list_ports


nRF9160 = serial.Serial()
root = tk.Tk()
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')
settings_tab = ttk.Frame(notebook)
commands_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")
notebook.add(commands_tab, text="Commands")


###################################################################################################
class ToggleSwitch(tk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, command=self.toggle, **kwargs)
        self.is_on = False
        self.configure(width=10, relief="raised", bg="red", text="Off")
    
    def toggle(self):
        global nRF9160
        if nRF9160.is_open:
            try:
                nRF9160.close()
                self.is_on = False
            except:
                serial_monitor.insert(tk.INSERT, "Failed to close serial device.\r\n")
                print(e)
                self.is_on = True
                return
        else:
            try:
                nRF9160.port = port_svar.get()
                nRF9160.baudrate = baud_ivar.get()
                nRF9160.open()
                serial_monitor.insert(tk.INSERT, f"Connected: PORT={port_svar.get()}, BAUD={baud_ivar.get()}.\r\n")
                self.is_on = True
            except Exception as e:
                serial_monitor.insert(tk.INSERT, "Failed to open serial device, please check your connection and settings.\r\n")
                print(e)
                self.is_on = False
                return

        if self.is_on:
            self.configure(bg="green", text="On")
        else:
            self.configure(bg="red", text="Off")
###################################################################################################

class ATButton(tk.Button):
    def __init__(self, at_command:str, master:Tk=commands_tab):
        super().__init__(master=master, command=self.submit_cmd)
        self.at_command = at_command
        self.config(text=f"AT{at_command}",font=LABEL_FONT)


    def submit_cmd(self) -> None:
        send_at_cmd(self.at_command)


root.title("AT Commander")
root.geometry("1280x720")

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

def open_device() -> None:
    global nRF9160
    nRF9160.open()

def update_port() -> None:
    global nRF9160
    if port_svar.get() != "Select Port" and (nRF9160.portstr != port_svar.get()):
        if nRF9160.is_open:
            nRF9160.close()
        nRF9160.port = port_svar.get()
        nRF9160.open()

def update_baud() -> None:
    global nRF9160

    if nRF9160.is_open:
        nRF9160.close()
    nRF9160.baudrate = baud_ivar.get()
    nRF9160.open()

def get_input() -> None:
    print(serial_monitor.get("1.0",END))


def get_cnum() -> None:
    send_at_cmd("+CNUM")

def send_at_cmd(command: str) -> None:
    global nRF9160
    if nRF9160 is not None:
        if nRF9160.is_open:
            nRF9160.write(f"AT{command}\r\n".encode())
            response = nRF9160.read_all().decode()
            while not command in response:
                response = nRF9160.read_all().decode()
            for line in response.split("\n"):
                if command in line:
                    serial_monitor.insert(tk.INSERT,chars=f"{line}\r\n")
        elif port_svar.get() != "Select Port":
            serial_monitor.insert(tk.INSERT,f"Error: Serial Device \"{port_svar.get()}\" is not open.\r\n")
        else:
            serial_monitor.insert(tk.INSERT,f"Error: Please select a serial port.\r\n")


###################################################################################################
# WIDGETS

# NOTEBOOK - Contains tabs

LABEL_CNF = {
    "font": LABEL_FONT,
    "width": 12,
    "padx": 5,
    "pady": 5,
    "anchor": tk.E
}

OPTION_CNF = {
    "font": LABEL_FONT,
    "width": 12,
    "padx": 5,
    "pady": 5,
    "relief": "groove",
    "anchor": tk.W
}

# COMPORT WIDGETS
port_list = get_devices()

port_frame = tk.Frame(settings_tab)
port_frame.pack(anchor=tk.W)

port_labl = Label(port_frame, text="Port:", cnf=LABEL_CNF)
port_labl.pack(side=tk.LEFT)

port_svar = StringVar(root)
port_svar.set("Select Port")

port_menu = OptionMenu(port_frame, port_svar, *port_list)
port_menu.config(font=LABEL_FONT, cnf=OPTION_CNF)
port_menu.pack(side=tk.LEFT, anchor=tk.W)

# BAUDRATE WIDGETS
baud_frame = tk.Frame(settings_tab)
baud_frame.pack(anchor=tk.W)
baud_labl = Label(baud_frame, text="Baud:", cnf=LABEL_CNF)
baud_labl.pack(side=tk.LEFT, anchor=tk.W)
baud_ivar = IntVar(root)
baud_ivar.set(DEFAULT_BAUD)
baud_menu = OptionMenu(baud_frame, baud_ivar, *BAUD_OPTIONS)
baud_menu.config(font=LABEL_FONT, cnf=OPTION_CNF)
baud_menu.pack(side=tk.LEFT, anchor=tk.W)

# OPEN SERIAL DEVICE
conn_frame = tk.Frame(settings_tab)
conn_frame.pack(anchor=tk.W)
conn_labl = Label(conn_frame, text="Connection:", cnf=LABEL_CNF)
conn_labl.pack(side=tk.LEFT)
conn_switch = ToggleSwitch(master=conn_frame, font=LABEL_FONT)
conn_switch.pack(side=tk.LEFT,anchor=tk.W,padx=PADDING_X,pady=PADDING_Y)

# AT BUTTONS
at_buttons = []
at_buttons.append(ATButton(at_command="+CNUM"))
at_buttons.append(ATButton(at_command="+CGMI"))
at_buttons.append(ATButton(at_command="+CGMM"))
at_buttons.append(ATButton(at_command="+CGMR"))
at_buttons.append(ATButton(at_command="+CGSN"))
at_buttons.append(ATButton(at_command="%SHORTSWVER"))
at_buttons.append(ATButton(at_command="%HWVERSION"))
at_buttons.append(ATButton(at_command="%XMODEMUUID"))
at_buttons.append(ATButton(at_command="+ODIS"))
at_buttons.append(ATButton(at_command="+ODISNTF"))
at_buttons.append(ATButton(at_command="%2DID"))

for b in at_buttons:
    b.pack(side=tk.LEFT)

# button = Button(commands_tab, text="AT+CNUM", command=get_cnum, font=LABEL_FONT)
# button.pack()

# MONITOR WIDGETS
serial_monitor = Text(root, height="100", width="150", fg="white", bg="black", blockcursor=True, insertbackground="green", font=MONITOR_FONT)
serial_monitor.pack(padx=PADDING_X, pady=PADDING_Y)

# SERIAL DEVICE




root.mainloop()
