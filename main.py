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
import threading
import re
import os
from PIL import Image, ImageTk

DIM_X = 1280
DIM_Y = 720

serial_lock = threading.Lock()
enable_trace = False

root = tk.Tk()
root.title("AT Commander")
root.geometry(f"{DIM_X}x{DIM_Y}")

BAUD_OPTIONS    = [115200, 9600]
DEFAULT_PORT    = "Select Port"
DEFAULT_BAUD    = 115200
BUTTON_WIDTH    = 15    # Width is the horizontal measurement, in this context
PADDING_X       = 5
PADDING_Y       = 5
LABEL_FONT      = font.Font(root=root, family="Consolas", size=12)
MONITOR_FONT    = font.Font(root=root, family="Consolas", size=12)
DARK_GRAY       = "#1f1f1f"
WHITE           = "white"

nRF9160 = serial.Serial()
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')
settings_tab = ttk.Frame(notebook)
commands_tab = ttk.Frame(notebook,width=DIM_X)
notebook.add(settings_tab, text="Settings")
notebook.add(commands_tab, text="Commands")
serial_monitor = Text(root, height="100", width="150", fg=WHITE, bg=DARK_GRAY, font=MONITOR_FONT)


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
                serial_monitor.insert(tk.END, f"Closed connection to PORT={port_svar.get()}, BAUD={baud_ivar.get()}.\r\n")
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
            self.configure(bg="light green", text="On")
        else:
            self.configure(bg="red", text="Off")

class LiveTraceSwitch(tk.Button):
    """A custom button used to toggle live modem tracing

    Args:
        master: The master container of the button
        **kwargs:   Any additional arguments belonging to the parent class tk.Button
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(master, command=self.toggle, **kwargs)
        self.is_on = False
        self.enable_trace = False
        self.configure(width=10, relief="raised", bg="red", text="Off")
    
    def toggle(self):
        """Toggles the connection to the serial device
        """
        self.is_on = not self.is_on
        # Recolor button to match the status of the connection
        if self.is_on:
            self.configure(bg="light green", text="On")
            self.enable_trace = True
            self.serial_thread = threading.Thread(target=self.live_trace, daemon=True)
            self.serial_thread.start()
        else:
            self.configure(bg="red", text="Off")
            self.enable_trace = False
            self.serial_thread = None

    def live_trace(self):
        global nRF9160
        while self.enable_trace:
            if nRF9160.is_open:
                with serial_lock:
                    if nRF9160.in_waiting > 0:
                        data = remove_ansi_escape_codes(nRF9160.readline().decode('utf-8').strip())
                        if data:
                            serprint(data)

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
        self.config(text=f"{at_command.cmd_s}",font=LABEL_FONT,width=BUTTON_WIDTH)
        self.tooltip = Tooltip(self, at_command.hint_s)

    def submit_cmd(self) -> None:
        # Running "submit_cmd" in separate thread to prevent blocking the main thread
        threading.Thread(target=self.send_at_cmd,args=(self.at_command,), daemon=True).start()

    def send_at_cmd(self, cmd: ATCommand) -> None:
        global nRF9160
        if nRF9160 is not None:
            with serial_lock:
                if nRF9160.is_open:
                    stamps = []
                    serprint(f"{get_timestamp()} -> {cmd.cmd_s}")
                    nRF9160.write(f"{cmd.cmd_s}\r\n".encode())
                    response = nRF9160.read_all().decode()
                    while not "OK" in response and not "ERROR" in response:
                        response = nRF9160.read_all().decode()
                        stamps.append(get_timestamp())

                    lines = response.split("\n")
                    for i in range(len(lines)-2):
                        lines[i] = f"{stamps[i]} <- {lines[i]}"
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

def remove_ansi_escape_codes(text) -> str:
    """Used to remove the ANSI escape codes "ESC" (escape) and "[0m" (text color reset)

    Args:
        text (str): The text to be purged of undesirable symbols

    Returns:
        str: The newly pruned string
    """
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

def on_copy():
    # Because Ctrl+C is not working natively for some dumb reason
    root.clipboard_clear()                                                        # Clear the clipboard
    serial_monitor.clipboard_append(serial_monitor.get("sel.first", "sel.last"))  # Append selected text to clip board

def load_settings() -> Tuple[Union[str,None], int]:
    try:
        with open("settings.json", 'r') as file:
            data = json.load(file)
            for s in data["settings"]:
                port = s["port"]
                baudrate = s["baudrate"]
    except:
        print("settings.json could not be opened or is missing. Using default settings.")
        port = DEFAULT_PORT
        baudrate = DEFAULT_BAUD
        pass

    return port, baudrate



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

loaded_port, loaded_baud = load_settings()

# COLUMN 1
column1 = tk.Frame(settings_tab)
column1.pack(side=tk.LEFT)

# COMPORT SELECT
port_list = get_devices()                                       # Get list of serial ports
port_frame = tk.Frame(column1)                                  # Make frame for port selection
port_frame.pack(side=tk.TOP)                                    # Pack frame into GUI
port_labl = Label(port_frame, text="Port:", cnf=LABEL_CNF)      #   Label the selection box
port_labl.pack(side=tk.LEFT)                                    #   Pack the label into the frame
port_svar = StringVar(root)                                     #   Create a variable to store port selectin
port_svar.set(loaded_port)                                      #   Default variable to display "Select Port"
port_menu = OptionMenu(port_frame, port_svar, *port_list)       #   Create drop-down menu listing port options
port_menu.config(font=LABEL_FONT, cnf=OPTION_CNF)               #   Configure the menu style
port_menu.pack(side=tk.LEFT)                                    #   Pack menu into frame

# BAUDRATE SELECT
baud_frame = tk.Frame(column1)                                  # Make frame for baud selection
baud_frame.pack(side=tk.TOP)                                    # Pack frame into GUI
baud_labl = Label(baud_frame, text="Baud:", cnf=LABEL_CNF)      #   Label the selection box
baud_labl.pack(side=tk.LEFT)                                    #   Pack the label into the frame
baud_ivar = IntVar(root)                                        #   Create a variable to store the baud rate
baud_ivar.set(loaded_baud)                                      #   Set the baud rate to the default value (115200)
baud_menu = OptionMenu(baud_frame, baud_ivar, *BAUD_OPTIONS)    #   Create Drop-down menu listing baud options
baud_menu.config(font=LABEL_FONT, cnf=OPTION_CNF)               #   Configure the menu style
baud_menu.pack(side=tk.LEFT)                                    #   Pack menu into frame

# CONNECT BUTTON
conn_frame = tk.Frame(column1)                                      # Make frame for serial connect button
conn_frame.pack(side=tk.TOP)                                        # Pack frame into GUI
conn_labl = Label(conn_frame, text="Connection:", cnf=LABEL_CNF)    #   Label the connect button
conn_labl.pack(side=tk.LEFT)                                        #   Pack label into the frame
conn_switch = SerialPowerSwitch(master=conn_frame, font=LABEL_FONT) #   Create toggle switch button
conn_switch.pack(side=tk.LEFT,padx=PADDING_X,pady=PADDING_Y)        #   Pack button into frame

# COLUMN 2
column2 = tk.Frame(settings_tab)
column2.pack(side=tk.LEFT, fill=tk.Y)

# LIVE TRACE BUTTON
trac_frame = tk.Frame(column2)                                  # Make frame for serial connect button
trac_frame.pack(side=tk.TOP)                                    # Pack frame into GUI
trac_labl = Label(column2, text="Live Trace:", cnf=LABEL_CNF)   #   Label the connect button
trac_labl.pack(side=tk.LEFT)                                    #   Pack label into the frame
trac_switch = LiveTraceSwitch(master=column2, font=LABEL_FONT)  #   Create toggle switch button
trac_switch.pack(side=tk.LEFT,padx=PADDING_X,pady=PADDING_Y)    #   Pack button into frame


# AT BUTTONS
command_buttons = []
at_commands = load_commands()
for command in at_commands:
    command_buttons.append(ATButton(command))

save_icon_name = "icon_save.jpg"
save_icon_image = Image.open(save_icon_name)
new_image = save_icon_image.resize((32, 32), Image.Resampling.LANCZOS)
photo = ImageTk.PhotoImage(new_image)

save_button = tk.Button(master=commands_tab,image=photo,text="Save Log",compound=tk.LEFT,font=LABEL_FONT)
save_button.config(width=100)
command_buttons.append(save_button)


def get_columns(event=None):
    root.update_idletasks()  # Ensure all geometry is updated
    button_width_pixels = command_buttons[0].winfo_reqwidth()  # Get the actual width of the buttons in pixels
    commands_tab_width = commands_tab.winfo_width()       # Get the current width of the commands tab
    columns = max(1, int(commands_tab_width / button_width_pixels))  # Calculate the number of columns

    for i, button in enumerate(command_buttons):
        row = i // columns  # Calculate row number
        col = i % columns   # Calculate column number
        button.grid(row=row, column=col, padx=PADDING_X, pady=PADDING_Y)


commands_tab.bind("<Configure>", get_columns)
serial_monitor.pack(padx=PADDING_X, pady=PADDING_Y)
serial_monitor.bind("<Key>", disable_typing)
serial_monitor.bind("<Control-c>", lambda event: on_copy())

root.mainloop()



