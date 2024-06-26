"""
    Simple Tkinter GUI for Qualisys LSL.
"""

import argparse
import asyncio
import logging
import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

import old_ui.link as link

LOG = logging.getLogger("qlsl")

class App(tk.Frame):
    def __init__(self, master, async_loop):
        super().__init__(master)
        self.master = master
        self.async_loop = async_loop
        self.master.title("QTM LSL App")
        self.set_icon()
        self.pack()
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        self.parent_directory = 'C:\\Users\\QTM\\Desktop\\motion_capture_data'
        self.create_layout()
        self.set_geometry()
        self.link_handle = None
        self.start_task = None
    
    def set_icon(self):
        try:
            icon_path = os.path.join("images", "qtm.ico")
            self.master.iconbitmap(icon_path)
        except Exception as ex:
            LOG.debug("Failed to set window icon: " + repr(ex))
    
    def set_geometry(self):
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        x = int(ws/2.5)
        y = int(hs/2.5)
        self.master.geometry("+{}+{}".format(x, y))
        self.master.update()
        w = self.master.winfo_width()
        h = self.master.winfo_height()
        self.master.minsize(w, h)

    def choose_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.parent_directory.set(folder_path)

    def create_layout(self):
        self.qtm_host = tk.StringVar()
        self.qtm_host.set("127.0.0.1")
        self.qtm_port = tk.StringVar()
        self.qtm_port.set(link.QTM_DEFAULT_PORT)
        row_number = 0
        """
        tk.Label(self, text="QTM Server Address    ").grid(row=row_number, sticky="w")
        self.entry_host = tk.Entry(self, textvariable=self.qtm_host)
        self.entry_host.grid(row=row_number, column=1)
        row_number += 1

        
        tk.Label(self, text="QTM Server Port").grid(row=row_number, sticky="w")
        self.entry_port = tk.Entry(self, textvariable=self.qtm_port)
        self.entry_port.grid(row=row_number, column=1)
        row_number += 1
        """

        self.parent_directory = tk.StringVar(value=self.parent_directory)
        self.folder_display = tk.Entry(self, textvariable=self.parent_directory, state='readonly', width=50, justify='left')
        self.folder_display.grid(row=row_number, column=0, sticky="w")
        self.btn_folder = tk.Button(
            self, text="Choose New Folder", width=15, command=self.choose_folder
        )
        self.btn_folder.grid(row=row_number, column=1, sticky="e")
        self.lbl_time = tk.Label(self, text="")
        self.lbl_time.grid(row=row_number,  sticky="w")
        row_number += 1

        self.participant_name = tk.StringVar(value="Leah2002")
        tk.Label(self, text="Participant Name   ").grid(row=row_number, sticky="w")
        self.entry_participant_name = tk.Entry(self, textvariable=self.participant_name)
        self.entry_participant_name.grid(row=row_number, column=1)
        row_number += 1

        self.trial_number = tk.StringVar()
        tk.Label(self, text="Trial Number   ").grid(row=row_number, sticky="w")
        self.entry_trial_number = tk.Spinbox(self, from_=1, to=500, textvariable=self.trial_number)
        self.entry_trial_number.grid(row=row_number, column=1)
        row_number += 1

        self.starting_yaw = tk.StringVar()
        tk.Label(self, text="Initial Angle of Baby   ").grid(row=row_number, sticky="w")
        self.entry_starting_yaw = tk.Spinbox(self, values=[-90, -45, 0, 45, 90], textvariable=self.starting_yaw)
        self.entry_starting_yaw.grid(row=row_number, column=1)
        row_number += 1

        self.btn_link = tk.Button(
            self, text="Link", width=10, command=self.start_or_stop
        )
        self.btn_link.grid(row=row_number, column=1, sticky="e")
        
        row_number += 1
        self.lbl_time = tk.Label(self, text="")
        self.lbl_time.grid(row=row_number,  sticky="w")
        row_number += 1


        self.lbl_packets = tk.Label(self, text="")
        self.lbl_packets.grid(row=row_number, sticky="w")
        self.lbl_status = tk.Label(self, text="")
        self.lbl_status.grid(row=row_number, column=1, sticky="e")
        row_number += 1
        self.lbl_folder = tk.Label(self, text="")
        self.lbl_folder.grid(row=row_number, sticky="w")

        self.enable_input(True)

        self.grid(padx=25, pady=(15, 20))
        col_count, _ = self.grid_size()
        for col in range(col_count):
            self.grid_columnconfigure(col, pad=5)
        self.grid_rowconfigure(1, pad=10)
    
    def enable_input(self, enable):
        if enable:
            #self.entry_host["state"] = "normal"
            #self.entry_port["state"] = "normal"
            self.btn_link["text"] = "Start"
        else:
            #self.entry_host["state"] = "disabled"
            #self.entry_port["state"] = "disabled"
            self.btn_link["text"] = "Stop"
    
    def on_state_changed(self, new_state):
        if new_state == link.State.INITIAL:
            self.lbl_status["text"] = ""
            self.lbl_time["text"] = ""
            self.lbl_packets["text"] = ""
        elif new_state == link.State.WAITING:
            self.lbl_status["text"] = "Waiting on QTM"
        elif new_state == link.State.STREAMING:
            self.lbl_status["text"] = "Streaming"
        elif new_state == link.State.STOPPED:
            self.lbl_status["text"] = "Stopped"
            self.enable_input(True)
            self.link_handle = None
    
    def on_error(self, msg):
        messagebox.showerror("Error", msg)
    
    def start_or_stop(self):
        if self.link_handle:
            self.do_stop()
        else:
            if self.start_task:
                if not self.start_task.cancelled():
                    self.start_task.cancel()
            else:
                self.do_start()

    def do_stop(self):
        asyncio.ensure_future(self.link_handle.shutdown(self.target_file))
    
    def do_start(self):
        port_str = self.qtm_port.get()
        try:
            port = int(port_str)
            if port < 0 or port > 65535:
                raise ValueError
        except ValueError:
            self.on_error("'{}' is not a valid port number".format(port_str))
            return
        host = self.qtm_host.get()
        self.start_task = asyncio.ensure_future(self.do_async_start(host, port))

    async def do_async_start(self, host, port):
        self.export_filename = f''
        try:
            err_msg = None
            self.lbl_status["text"] = "Connecting to QTM"
            self.enable_input(False)
            self.link_handle = await link.init(
                qtm_host=host,
                qtm_port=port,
                qtm_version=link.QTM_DEFAULT_VERSION,
                on_state_changed=self.on_state_changed,
                on_error=self.on_error,
                starting_yaw=int(self.starting_yaw.get())
            )
        except asyncio.CancelledError:
            self.link_handle = None
            LOG.error("Start attempt canceled")
        except link.LinkError as err:
            self.link_handle = None
            err_msg = str(err)
        except Exception as ex:
            self.link_handle = None
            LOG.error("gui: do_async_start exception: " + repr(ex))
            err_msg = ("An internal error occurred. "
                "See log messages for details.")
            raise
        finally:
            if not self.link_handle:
                self.enable_input(True)
                self.lbl_status["text"] = "Start failed"
                if err_msg:
                    self.on_error(err_msg)
            self.start_task = None

    def format_packet_count(self, count):
        mil = 1000000
        if count > mil:
            m = int(count/mil)
            rem = count%mil
            ten_k = int(rem/10000)
            fmt = "{}.{:02d}m".format(m, ten_k)
        elif count > 1000:
            k = int(count/1000)
            rem = count%1000
            ten = int(rem/10)
            fmt = "{}.{:02d}k".format(k, ten)
        else:
            fmt = str(count)
        return fmt
    
    def format_time(self, tm):
        fmt = time.strftime('%H:%M:%S', time.gmtime(tm))
        return fmt
    
    def display_link_info(self):
        if self.link_handle and self.link_handle.is_streaming():
            self.target_folder = f"{self.parent_directory.get()}\\{datetime.now().strftime('%Y-%m-%d')}_{self.participant_name.get()}"
            if not os.path.exists(self.target_folder):
                os.makedirs(self.target_folder)

            self.target_file = self.target_folder + f"\\trial_{self.trial_number.get()}_startAngle_{self.starting_yaw.get()}.csv"

            self.lbl_folder["text"] = "Saving data to: {}".format(
                self.target_file
            ) 

            elapsed_time = self.link_handle.elapsed_time()
            self.lbl_time["text"] = "Elapsed time: {}".format(
                self.format_time(elapsed_time)
            )
            packet_count = self.link_handle.packet_count
            self.lbl_packets["text"] = "Packet count: {}".format(
                self.format_packet_count(packet_count)
            )
            

    async def updater(self, interval=1/20):
        try:
            LOG.debug("gui: updater enter")
            while True:
                self.display_link_info()
                self.update()
                await asyncio.sleep(interval)
        finally:
            LOG.debug("gui: updater exit")
    
    async def stop_async_loop(self):
        self.async_loop.stop()
        self.master.destroy()
        LOG.debug("gui: stop_async_loop")
    
    def run_async_loop(self):
        asyncio.ensure_future(self.updater())
        self.async_loop.run_forever()

    def close(self):
        tasks = asyncio.all_tasks()
        for task in tasks:
            task.cancel()
        asyncio.ensure_future(self.stop_async_loop())

def main():
    root = tk.Tk()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = App(master=root, async_loop=loop)
    app.run_async_loop()
    loop.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qualisys LSL App.")
    parser.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="log debug messages"
    )
    args = parser.parse_args()
    if args.verbose:
        LOG.setLevel(logging.DEBUG)
    else:
        LOG.setLevel(logging.INFO)
    main()
