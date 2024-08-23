# Devon White, PPD 2024
# AT Commander


import tkinter as tk
from tkinter import *
from tkinter import font, ttk
import serial
from typing import Union, Tuple, List, Optional

import serial.tools
import serial.tools.list_ports
import math

DIM_X = 1280
DIM_Y = 720

root = tk.Tk()
root.title("AT Commander")
root.geometry(f"{DIM_X}x{DIM_Y}")

BAUD_OPTIONS    = [115200, 9600]
DEFAULT_BAUD    = 115200
BUTTON_WIDTH    = 15    # Width is the horizontal measurement, in this context
PADDING_X       = 5
PADDING_Y       = 5
LABEL_FONT      = font.Font(root=root, family="Consolas", size=12)
MONITOR_FONT   = font.Font(root=root, family="Consolas", size=12)

nRF9160 = serial.Serial()
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')
settings_tab = ttk.Frame(notebook)
commands_tab = ttk.Frame(notebook,width=DIM_X)
notebook.add(settings_tab, text="Settings")
notebook.add(commands_tab, text="Commands")


###################################################################################################
class SerialPowerSwitch(tk.Button):
    """A custom button used to toggle a serial connection

    Args:
        master: The master container of the button
        **kwargs:   Any additional arguments belonging to the parent class tk.Button
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(master, command=self.toggle, **kwargs)
        self.is_on = False
        self.configure(width=10, relief="raised", bg="red", text="Off")
    
    def toggle(self):
        """Toggles the connection to the serial device
        """
        global nRF9160      # Serial device

        # If the connection is open, attempt to close it
        if nRF9160.is_open:
            try:
                nRF9160.close()
                self.is_on = False
            except:
                serial_monitor.insert(tk.INSERT, "Failed to close serial device.\r\n")
                print(e)
                self.is_on = True
                return
        
        # Else if the connection is closed, attempt to open it
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

        # Recolor button to match the status of the connection
        if self.is_on:
            self.configure(bg="green", text="On")
        else:
            self.configure(bg="red", text="Off")


class ATButton(tk.Button):
    """A special button used to control the transmission of AT commands

    Args:
        tk (_type_): _description_
    """

    # Ignore incoming responses
    # Prevents confusion with prompted responses vs. non-prompted info dumping



    def __init__(self, at_command:str, master:Tk=commands_tab):
        super().__init__(master=master, command=self.submit_cmd)
        self.at_command = at_command
        self.config(text=f"AT{at_command}",font=LABEL_FONT,width=BUTTON_WIDTH)


    def submit_cmd(self) -> None:
        self.send_at_cmd(self.at_command)

    def send_at_cmd(self, command: str) -> None:
        global nRF9160
        if nRF9160 is not None:
            if nRF9160.is_open:
                nRF9160.write(f"AT{command}\r\n".encode())
                response = nRF9160.read_all().decode()
                while not "OK" in response and not "ERROR" in response:
                    response = nRF9160.read_all().decode()
                prev_line = response.split("\n")[0]
                for line in response.split("\n"):
                    if "OK" in line:
                        serial_monitor.insert(tk.INSERT,chars=f"{prev_line}\r\n")
                    if "ERROR" in line:
                        serial_monitor.insert(tk.INSERT,chars=f"{line}\r\n")
                    prev_line = line
            elif port_svar.get() != "Select Port":
                serial_monitor.insert(tk.INSERT,f"Error: Serial Device \"{port_svar.get()}\" is not open.\r\n")
            else:
                serial_monitor.insert(tk.INSERT,f"Error: Please select a serial port.\r\n")

# END - Custom Classes
###################################################################################################


def get_devices() -> List[str]:
    devices = serial.tools.list_ports.comports()
    port_list = []
    for dev in devices:
        port_list.append(dev.name)
    return port_list


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
conn_switch = SerialPowerSwitch(master=conn_frame, font=LABEL_FONT)
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


def get_columns(event=None):
    root.update_idletasks()  # Ensure all geometry is updated
    button_width_pixels = at_buttons[0].winfo_reqwidth()  # Get the actual width of the buttons in pixels
    commands_tab_width = commands_tab.winfo_width()       # Get the current width of the commands tab
    columns = max(1, int(commands_tab_width / button_width_pixels))  # Calculate the number of columns

    print("commands_tab width:", commands_tab_width)
    print("Button width in pixels:", button_width_pixels)
    print("Calculated columns:", columns)

    for i, button in enumerate(at_buttons):
        row = i // columns  # Calculate row number
        col = i % columns   # Calculate column number
        button.grid(row=row, column=col, padx=PADDING_X, pady=PADDING_Y)


commands_tab.bind("<Configure>", get_columns)

# MONITOR WIDGETS
serial_monitor = Text(root, height="100", width="150", fg="white", bg="black", blockcursor=True, insertbackground="green", font=MONITOR_FONT)
serial_monitor.pack(padx=PADDING_X, pady=PADDING_Y)

# SERIAL DEVICE

root.mainloop()



