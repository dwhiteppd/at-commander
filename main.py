# Devon White, PPD 2024
# AT Commander


import tkinter as tk
from tkinter import *
from tkinter import font, ttk
import serial
from typing import Union, Tuple, List, Optional

import serial.tools
import serial.tools.list_ports
import math, time, json
import datetime as dt

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
serial_monitor = Text(root, height="100", width="150", fg="white", bg="black", blockcursor=True, insertbackground="green", font=MONITOR_FONT)


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
                serial_monitor.insert(tk.END, "Failed to close serial device.\r\n")
                print(e)
                self.is_on = True
                return
        
        # Else if the connection is closed, attempt to open it
        else:
            nRF9160.port = port_svar.get()
            nRF9160.baudrate = baud_ivar.get()
            nRF9160.timeout = 3
            try:
                nRF9160.open()
                serial_monitor.insert(tk.END, f"Connected: PORT={port_svar.get()}, BAUD={baud_ivar.get()}.\r\n")
                self.is_on = True
            except Exception as e:
                serial_monitor.insert(tk.END, "Failed to open serial device, please check your connection and settings.\r\n")
                print(e)
                self.is_on = False
                return

        # Recolor button to match the status of the connection
        if self.is_on:
            self.configure(bg="green", text="On")
        else:
            self.configure(bg="red", text="Off")

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify="left",
                         background="#ffffe0", relief="solid", borderwidth=1,
                         font=("Consolas", "10", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class ATCommand():
    def __init__(self, command:str, hint:str=None, ignore:str=None, one_liner:bool=False) -> None:
        self.cmd_s    = command   # The command to be sent
        self.hint_s   = hint      # Tooltip shown on mouse hover
        self.ignore_s = ignore    # Responses to ignore after sending command
        self.one_liner  = one_liner # Indicates that the response should only be one line


class ATButton(tk.Button):
    """A special button used to control the transmission of AT commands
    """

    # Ignore incoming responses
    # Prevents confusion with prompted responses vs. non-prompted info dumping

    def __init__(self, at_command:ATCommand, master:Tk=commands_tab):
        super().__init__(master=master, command=self.submit_cmd)
        self.at_command = at_command
        self.config(text=f"AT{at_command.cmd_s}",font=LABEL_FONT,width=BUTTON_WIDTH)
        self.tooltip = Tooltip(self, at_command.hint_s)

    def submit_cmd(self) -> None:
        self.send_at_cmd(self.at_command)

    def send_at_cmd(self, cmd: ATCommand) -> None:
        global nRF9160
        if nRF9160 is not None:
            if nRF9160.is_open:
                stamps = []
                prev_response = ""
                serprint(f"{get_timestamp()} -> {cmd.cmd_s}")
                nRF9160.write(f"AT{cmd.cmd_s}\r\n".encode())
                response = nRF9160.read_all().decode()
                while not "OK" in response and not "ERROR" in response:
                    response = nRF9160.read_all().decode()
                    stamps.append(get_timestamp())

                lines = response.split("\n")
                for i in range(len(lines)-2):
                    lines[i] = f"{stamps[i]} <- {lines[i]}"
                    print(lines[i])
                prev_line = lines[0]

                # Command returns one line
                if cmd.one_liner:
                    for line in lines:
                        if line.strip() in "OK":
                            serprint(prev_line)
                            break
                        prev_line = line

                # Command returns multiple lines
                else:
                    for line in lines:
                        # If command has a specific ignore rule
                        if cmd.ignore_s:
                            if not cmd.ignore_s in line and not "OK" in line:
                                serprint(line)
                        # Else if the response has not finished
                        elif not "OK" in line:
                            serprint(line)

                        # If the command returned an error
                        if "ERROR" in line:
                            break
                        # If the command finished returning a response
                        if "OK" in line:
                            break
            elif port_svar.get() != "Select Port":
                serprint(f"{get_timestamp()} Error: Serial Device \"{port_svar.get()}\" is not open.")
            else:
                serprint(f"{get_timestamp()} Error: Please select a serial port.")



# END - Custom Classes
###################################################################################################


def get_devices() -> List[str]:
    devices = serial.tools.list_ports.comports()
    port_list = []
    for dev in devices:
        port_list.append(dev.name)
    return port_list

def serprint(msg: str) -> None:
    """Prints a string to the serial monitor widget

    Args:
        msg (str): The message to be stripped of leading/trailing white space and printed
        to the serial monitor, followed by a carriage return and linefeed.
    """
    serial_monitor.insert(tk.END,f"{msg.strip()}\r\n")
    serial_monitor.see(tk.END)

def load_commands() -> List[ATCommand]:
    """Loads commands from "atcommands.json"

    Returns:
        List[ATCommand]: A list of ATCommand objects
    """
    commands = []
    with open("atcommands.json", 'r') as file:
        data = json.load(file)
        for c in data['general']:
            one_line = (c['response_line_count'] == 1)
            commands.append(ATCommand(c['command'],c['description'],one_liner=one_line))
    return commands

def get_timestamp() -> str:
    ts = dt.datetime.now()
    ts_str = ts.strftime(format="%m%d%Y-%H:%M:%S.%f")[:-3]
    return (f"[{ts_str}]")

def disable_typing(event) -> str:
    return "break"


###################################################################################################
# WIDGETS

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
port_list = get_devices()                                       # Get list of serial ports
port_frame = tk.Frame(settings_tab)                             # Make frame for port selection
port_frame.pack(anchor=tk.W)                                    # Pack frame into GUI
port_labl = Label(port_frame, text="Port:", cnf=LABEL_CNF)      #   Label the selection box
port_labl.pack(side=tk.LEFT)                                    #   Pack the label into the frame
port_svar = StringVar(root)                                     #   Create a variable to store port selectin
port_svar.set("Select Port")                                    #   Default variable to display "Select Port"
port_menu = OptionMenu(port_frame, port_svar, *port_list)       #   Create drop-down menu listing port options
port_menu.config(font=LABEL_FONT, cnf=OPTION_CNF)               #   Configure the menu style
port_menu.pack(side=tk.LEFT, anchor=tk.W)                       #   Pack menu into frame

# BAUDRATE WIDGETS
baud_frame = tk.Frame(settings_tab)                             # Make frame for baud selection
baud_frame.pack(anchor=tk.W)                                    # Pack frame into GUI
baud_labl = Label(baud_frame, text="Baud:", cnf=LABEL_CNF)      #   Label the selection box
baud_labl.pack(side=tk.LEFT, anchor=tk.W)                       #   Pack the label into the frame
baud_ivar = IntVar(root)                                        #   Create a variable to store the baud rate
baud_ivar.set(DEFAULT_BAUD)                                     #   Set the baud rate to the default value (115200)
baud_menu = OptionMenu(baud_frame, baud_ivar, *BAUD_OPTIONS)    #   Create Drop-down menu listing baud options
baud_menu.config(font=LABEL_FONT, cnf=OPTION_CNF)               #   Configure the menu style
baud_menu.pack(side=tk.LEFT, anchor=tk.W)                       #   Pack menu into frame

# OPEN SERIAL DEVICE
conn_frame = tk.Frame(settings_tab)                                         # Make frame for serial connect button
conn_frame.pack(anchor=tk.W)                                                # Pack frame into GUI
conn_labl = Label(conn_frame, text="Connection:", cnf=LABEL_CNF)            #   Label the connect button
conn_labl.pack(side=tk.LEFT)                                                #   Pack label into the frame
conn_switch = SerialPowerSwitch(master=conn_frame, font=LABEL_FONT)         #   Create toggle switch button
conn_switch.pack(side=tk.LEFT,anchor=tk.W,padx=PADDING_X,pady=PADDING_Y)    #   Pack button into frame

# AT BUTTONS
at_buttons = []
at_commands = load_commands()
for command in at_commands:
    at_buttons.append(ATButton(command))

def get_columns(event=None):
    root.update_idletasks()  # Ensure all geometry is updated
    button_width_pixels = at_buttons[0].winfo_reqwidth()  # Get the actual width of the buttons in pixels
    commands_tab_width = commands_tab.winfo_width()       # Get the current width of the commands tab
    columns = max(1, int(commands_tab_width / button_width_pixels))  # Calculate the number of columns

    for i, button in enumerate(at_buttons):
        row = i // columns  # Calculate row number
        col = i % columns   # Calculate column number
        button.grid(row=row, column=col, padx=PADDING_X, pady=PADDING_Y)


commands_tab.bind("<Configure>", get_columns)
serial_monitor.pack(padx=PADDING_X, pady=PADDING_Y)
serial_monitor.bind("<Key>", disable_typing)

root.mainloop()



