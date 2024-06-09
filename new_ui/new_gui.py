import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
from enum import Enum
import os
from datetime import datetime
import asyncio
import logging
import time

import mocap_recording as mocap_recording

LOG = logging.getLogger("qlsl")

class PickingPhase(Enum):
    BABY_POSITION = 0
    MOTHER_POSITION = 1
    CONFIRM = 2

class App(tk.Frame):
    def __init__(self, master=None, async_loop=None):
        super().__init__(master)
        self.master = master
        self.async_loop = async_loop
        self.master.title("Motion Capture Recording")
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        self.grid(sticky="nsew")
        self.canvas_width = 800
        self.canvas_height = 800
        self.visible_circles_mask = [1, 1, 1, 1, 1, 0, 0]
        self.circle_ids = [None] * 7
        self.picking_phase = PickingPhase.BABY_POSITION
        self.baby_and_mother_idxs = [None, None]
        self.parent_directory = 'C:\\Users\\QTM\\Desktop\\motion_capture_data'
        self.recording = False
        self.cap = None
        self.video_recorder = None
        self.mocap_recorder = None
        self.create_layout()

    def main_loop(self):
        asyncio.ensure_future(self.updater())
        self.async_loop.run_forever()

    async def stop_main_loop(self):
        self.async_loop.stop()
        self.master.destroy()
        LOG.debug("gui: stop_main_loop")

    def close(self):
        tasks = asyncio.all_tasks()
        for task in tasks:
            task.cancel()
        asyncio.ensure_future(self.stop_main_loop())

    async def updater(self, interval=1/20):
        try:
            LOG.debug("gui: updater enter")
            while True:
                self.update()
                if self.recording and self.mocap_recorder:
                    self.mocap_elapsed_time.set(f"Elapsed time: {self.get_formatted_time()}")
                    self.mocap_packet_number.set(f"Packets received: {self.get_formatted_packet_count()}")
                else:
                    self.mocap_elapsed_time.set("")
                    self.mocap_packet_number.set("")
                await asyncio.sleep(interval)
        finally:
            LOG.debug("gui: updater exit")
    
    def get_formatted_time(self):
        elapsed_time = self.mocap_recorder.elapsed_time()
        return time.strftime('%H:%M:%S', time.gmtime(elapsed_time))
    
    def get_formatted_packet_count(self):
        packet_count = self.mocap_recorder.packet_count
        if packet_count > 1e6:
            millions = int(packet_count/1e6)
            rem = packet_count%1e6
            tens_thousands = int(rem/1e4)
            formatted_count = "{}.{:02d}M".format(millions, tens_thousands)
        elif packet_count > 1e3:
            thousands = int(packet_count/1e3)
            rem = packet_count%1e3
            tens = int(rem/10)
            formatted_count = "{}.{:02d}k".format(thousands, tens)
        else:
            formatted_count = str(packet_count)
        return formatted_count
        
    def choose_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.parent_directory.set(folder_path)

    def create_layout(self):
        row_number = 0
        settings_frame = tk.Frame(self)
        settings_frame.grid(row=row_number, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        tk.Label(settings_frame, text="Data is currently saved in:   ").grid(row=row_number, sticky="w")
        self.parent_directory = tk.StringVar(value=self.parent_directory)
        self.folder_display = tk.Entry(settings_frame, textvariable=self.parent_directory, state='readonly', width=50, justify='left')
        self.folder_display.grid(row=row_number, column=1, sticky="w")
        self.folder_button = tk.Button(
            settings_frame, text="Choose New Folder", width=15, command=self.choose_folder
        )
        self.folder_button.grid(row=row_number, column=2, sticky="e")
        
        self.lbl_time = tk.Label(settings_frame, text="")
        self.lbl_time.grid(row=row_number,  sticky="w")
        row_number += 1

        self.participant_name = tk.StringVar(value="Leah2002")
        tk.Label(settings_frame, text="Participant Name   ").grid(row=row_number, sticky="w")
        self.participant_name_entry = tk.Entry(settings_frame, textvariable=self.participant_name)
        self.participant_name_entry.grid(row=row_number, column=1, sticky='w')
        row_number += 1

        self.trial_number = 1
        self.trial_number_str = tk.StringVar(value=f"Trial Number: {self.trial_number}")
        tk.Label(settings_frame, textvariable=self.trial_number_str).grid(row=row_number, sticky="w")
        row_number += 1

        vcmd = self.register(self.validate_input)

        self.degrees = tk.StringVar(value="5")

        self.label = tk.Label(settings_frame, text="Send triggers every ")
        self.label.grid(row=row_number, column=0, sticky='w')

        self.degree_entry = tk.Entry(settings_frame, textvariable=self.degrees, width=5, validate="key", validatecommand=(vcmd, "%P"))
        self.degree_entry.grid(row=row_number, column=1, sticky='w')

        self.label_unit = tk.Label(settings_frame, text=" degrees")
        self.label_unit.grid(row=row_number, column=1, sticky='e')
        # -----------------------------------------------------------------------------------------------------
        mocap_status_frame = tk.Frame(self)
        mocap_status_frame.grid(row=0, column=1, columnspan=2, rowspan=3, sticky="nsew", padx=10, pady=10)
        
        self.mocap_recording_status = tk.StringVar(value="")
        self.mocap_recording_status_label = tk.Label(mocap_status_frame, textvariable=self.mocap_recording_status)
        self.mocap_recording_status_label.grid(row=0, column=0, sticky='w')

        self.mocap_packet_number = tk.StringVar(value="")
        self.mocap_packet_number_label = tk.Label(mocap_status_frame,  textvariable=self.mocap_packet_number)
        self.mocap_packet_number_label.grid(row=1, column=0, sticky='w')

        self.mocap_elapsed_time = tk.StringVar(value="")
        self.mocap_elapsed_time_label = tk.Label(mocap_status_frame, textvariable=self.mocap_elapsed_time)
        self.mocap_elapsed_time_label.grid(row=2, column=0, sticky='w')
        # -----------------------------------------------------------------------------------------------------
        self.interactive_frame = tk.Frame(self)
        self.interactive_frame.grid(row=row_number, rowspan=4, column=0, sticky="nsew")

        self.camera_feed_frame = tk.Frame(self)
        self.camera_feed_frame.grid(row=row_number, column=1, sticky="nsew")

        self.phase_description = tk.StringVar(value="Click on the circle corresponding to where the baby is pointing")
        tk.Label(self.interactive_frame, textvariable=self.phase_description, font=('TkDefaultFont', 20)).grid(row=row_number, sticky="w", pady=0)
        row_number += 1
        self.canvas = tk.Canvas(self.interactive_frame, width=self.canvas_width, height=self.canvas_height, highlightthickness=2)
        self.canvas.grid(row=row_number+2, sticky="w", pady=0)
        self.canvas.config(scrollregion=(0, 200, self.canvas_width, self.canvas_height))


        self.camera_label = tk.Label(self.camera_feed_frame)
        self.camera_label.grid(row=row_number, column=2, sticky="w")

        self.draw_position_picker()
        self.capture_camera()

    def validate_input(self, inp):
        return inp.isdigit() or inp == ""
    
    def draw_position_picker(self):
        x_center = self.canvas_width / 2
        y_center = self.canvas_height / 2
        line_length = min(self.canvas_width, self.canvas_height) * 0.4

        # Horizontal line
        self.canvas.create_line(x_center - line_length/2, y_center,
                                x_center + line_length/2, y_center,
                                fill='#CCCC00')
        # Vertical line
        self.canvas.create_line(x_center, y_center - line_length/2,
                                x_center, y_center,
                                fill='#CCCC00')

        # Diagonal from top left
        self.canvas.create_line(x_center - line_length/2, y_center - line_length/2,
                                x_center + line_length, y_center + line_length,
                                fill='blue')

        # Diagonal from top right
        self.canvas.create_line(x_center + line_length/2, y_center - line_length/2,
                                x_center - line_length, y_center + line_length,
                                fill='blue')
        circle_radius = 10
        circle_color = 'red'
        self.circle_coords = [(x_center - line_length/2, y_center),                 # Left end of horizontal line
                              (x_center - line_length/2, y_center - line_length/2), # Top end of left diagonal
                              (x_center, y_center - line_length/2),                 # Top end of vertical line
                              (x_center + line_length/2, y_center - line_length/2), # Top end of right diagonal
                              (x_center + line_length/2, y_center),                 # Right end of horizontal line
                              (x_center + line_length, y_center + line_length),     # Bottom end of left diagonal
                              (x_center - line_length, y_center + line_length)      # Bottom end of right diagonal
                             ]    
        
        for idx, coord in enumerate(self.circle_coords):
            if not self.visible_circles_mask[idx]:
                continue
    
            x, y = coord
            circle_id = self.canvas.create_oval(x - circle_radius, y - circle_radius,
                                                x + circle_radius, y + circle_radius,
                                                fill=circle_color, outline=circle_color)
            self.circle_ids[idx] = circle_id

            if self.picking_phase != PickingPhase.CONFIRM:
                self.canvas.tag_bind(circle_id, '<Enter>', lambda event: self.canvas.config(cursor='hand2'))
                self.canvas.tag_bind(circle_id, '<Leave>', lambda event: self.canvas.config(cursor=''))

        if self.picking_phase != PickingPhase.CONFIRM:
            for idx, circle_id in enumerate(self.circle_ids):
                if circle_id is not None:
                    self.canvas.tag_bind(circle_id, '<Button-1>', self.circle_clicked)
        else:
            self.canvas.config(cursor='')
   
    def circle_clicked(self, event):
        circle_id = event.widget.find_closest(event.x, event.y + 200)[0] # Adding 200 since we're cropping the top 200px of the canvas, but the circles are technically still drawn at the original canvas coordinates.
        circle_index = self.circle_ids.index(circle_id)
        self.baby_and_mother_idxs[self.picking_phase.value] = circle_index
        self.picking_phase = PickingPhase(self.picking_phase.value + 1)
        for circle_id in self.circle_ids:
            self.canvas.delete(circle_id)
            self.circle_ids = [None] * 7

        if self.picking_phase == PickingPhase.MOTHER_POSITION:
            self.phase_description.set("Click on the circle corresponding to where the mother is starting")
            self.visible_circles_mask = [0, 0, 0, 0, 0, 1, 1]
            self.canvas.config(cursor='')
            self.draw_position_picker()
        elif self.picking_phase == PickingPhase.CONFIRM:
            self.phase_description.set("This is your choice of starting positions. Do you want to start recording?")
            self.visible_circles_mask = [0, 0, 0, 0, 0, 0, 0]
            for circle_idx in self.baby_and_mother_idxs:
                self.visible_circles_mask[circle_idx] = 1
            self.canvas.config(cursor='')
            self.draw_position_picker()
            self.confirmation_buttons()
        
    def confirmation_buttons(self):
        row_number = 4
        self.cancel_button = tk.Button(self.interactive_frame, text="No, I need to re-pick the positions", bg="darkred", fg="white", command=self.cancel_selection)
        self.cancel_button.grid(row=row_number, column=0, columnspan=1, sticky="ew", padx=5, pady=5)
        
        self.start_recording_button = tk.Button(self.interactive_frame, text="Yes, Start Recording", bg="darkgreen", fg="white", command=self.start_recording)
        self.start_recording_button.grid(row=row_number+1, column=0, columnspan=1, sticky="ew", padx=5, pady=5)

    def cancel_selection(self):
        self.picking_phase = PickingPhase.BABY_POSITION
        self.phase_description.set("Click on the circle corresponding to where the baby is pointing")
        self.baby_and_mother_idxs = [None, None]
        self.visible_circles_mask = [1, 1, 1, 1, 1, 0, 0]
        for circle_id in self.circle_ids:
            self.canvas.delete(circle_id)
            self.circle_ids = [None] * 7
        self.cancel_button.grid_remove()
        self.start_recording_button.grid_remove()
        self.draw_position_picker()
    
    def get_baby_angle(self):
        idx_to_angle = ['-90', '-45', '0', '45', '90']
        return idx_to_angle[self.baby_and_mother_idxs[0]]
    
    def get_mother_side(self):
        return 'right' if self.baby_and_mother_idxs[1] == 5 else 'left'

    def start_recording(self):
        self.participant_name_entry.config(state='readonly')
        self.degree_entry.config(state='readonly')
        self.folder_button.config(state='disabled')

        self.phase_description.set("Recording In Progress")
        self.target_folder = f"{self.parent_directory.get()}\\{datetime.now().strftime('%Y-%m-%d')}_{self.participant_name.get()}\\"
        num_of_files_in_folder = len(os.listdir(self.target_folder))
        # If for some reason the program was restarted after a few trials have been recorded,
        # we want the trial number to continue from where it stopped, not reset back to 1,
        # given that we don't want the experimenters to think about accidentally overwriting
        # the data (just quality of life things)
        if num_of_files_in_folder != 0:
            self.trial_number = int(num_of_files_in_folder / 2) + 1 # Dividing by 2 since we save video files as well
        self.trial_number_str.set(f"Trial Number: {self.trial_number}")
        self.target_filename = f"trial_{self.trial_number}_babyAngle_{self.get_baby_angle()}_motherSide_{self.get_mother_side()}"

        # Video recording
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_recorder = cv2.VideoWriter(self.target_folder+self.target_filename+'.mp4', fourcc, 20.0, (frame_width, frame_height))

        # Mocap recording
        self.started_mocap_recording = asyncio.ensure_future(self._start_mocap_recording())
        self.recording = True

        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)
        self.cancel_button.grid_remove()
        self.start_recording_button.grid_remove()
        self.stop_recording_button = tk.Button(self.interactive_frame, text="STOP RECORDING", bg="darkred", fg="white", command=self.stop_recording)
        self.stop_recording_button.grid(row=5, column=0, columnspan=1, sticky="ew", padx=5, pady=5)

    async def _start_mocap_recording(self, host_ip='127.0.0.1', port='22223'):
        try:
            err_msg = None
            self.mocap_recording_status.set("Connecting to Motion Capture software") 
            self.mocap_recorder = await mocap_recording.init(
                qtm_host=host_ip,
                qtm_port=port,
                qtm_version=mocap_recording.QTM_DEFAULT_VERSION,
                on_state_changed=self.mocap_state_update,
                on_error=self.on_error,
                starting_yaw=int(self.get_baby_angle())
            )
        except asyncio.CancelledError:
            LOG.error("Start attempt canceled")
        except mocap_recording.LinkError as err:
            err_msg = str(err)
        except Exception as ex:
            LOG.error("gui: do_async_start exception: " + repr(ex))
            err_msg = ("An internal error occurred. "
                "See log messages for details.")
            raise
        finally:
            if not self.mocap_recorder:
                self.mocap_recording_status.set("Streaming Start Failed. Please try again.")
                if err_msg:
                    self.on_error(err_msg)
            self.started_mocap_recording = None

    def on_error(self, msg):
        messagebox.showerror("Error", msg)
        self.stop_recording()

    def mocap_state_update(self, new_state):
        if new_state == mocap_recording.State.INITIAL:
            self.mocap_recording_status.set("")
            self.mocap_elapsed_time.set("")
            self.mocap_packet_number.set("")
        elif new_state == mocap_recording.State.WAITING:
            self.mocap_recording_status.set("Waiting on Motion Capture software")
        elif new_state == mocap_recording.State.STREAMING:
            self.mocap_recording_status.set("Motion Capture Data Streaming")
        elif new_state == mocap_recording.State.STOPPED:
            self.mocap_recording_status.set("Motion Capture Stream Stopped")
            
    def stop_recording(self):
        self.degree_entry.config(state='normal')
        self.phase_description.set("Do you want to keep this trial or record over it?")
        self.stop_recording_button.grid_remove()
        self.continue_trial_button = tk.Button(self.interactive_frame, text="No, this was a bad trial. Record over it.", bg="darkred", fg="white", command=self.record_over_trial)
        self.continue_trial_button.grid(row=4, column=0, columnspan=1, sticky="ew", padx=5, pady=5)

        self.record_over_trial_button = tk.Button(self.interactive_frame, text="Yes, go to the next trial.", bg="darkgreen", fg="white", command=self.goto_new_trial)
        self.record_over_trial_button.grid(row=5, column=0, columnspan=1, sticky="ew", padx=5, pady=5)

        self.recording = False
        if self.video_recorder:
            self.video_recorder.release()
            self.video_recorder = None
        
        if self.mocap_recorder:
            asyncio.ensure_future(self.mocap_recorder.shutdown(self.target_folder + self.target_filename + '.xlsx'))
    
    def goto_new_trial(self):
        self.continue_trial_button.grid_remove()
        self.record_over_trial_button.grid_remove()
        self.trial_number += 1
        self.trial_number_str.set(f"Trial Number: {self.trial_number}")
        self.picking_phase = PickingPhase.BABY_POSITION
        self.phase_description.set("Click on the circle corresponding to where the baby is pointing")
        self.baby_and_mother_idxs = [None, None]
        self.visible_circles_mask = [1, 1, 1, 1, 1, 0, 0]
        for circle_id in self.circle_ids:
            self.canvas.delete(circle_id)
            self.circle_ids = [None] * 7
        self.draw_position_picker()

    def record_over_trial(self):
        self.continue_trial_button.grid_remove()
        self.record_over_trial_button.grid_remove()
        self.phase_description.set("Press the button when you're ready to record again.")
        self.start_recording_button = tk.Button(self.interactive_frame, text="Start Recording", bg="darkgreen", fg="white", command=self.start_recording)
        self.start_recording_button.grid(row=4, column=0, columnspan=1, sticky="ew", padx=5, pady=5)

    def capture_camera(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        def update_feed():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                frame_height, frame_width, _ = frame.shape
                aspect_ratio = frame_width / frame_height

                if self.canvas_width / self.canvas_height > aspect_ratio:
                    new_width = int(self.canvas_height * aspect_ratio)
                    new_height = self.canvas_height
                else:
                    new_width = self.canvas_width
                    new_height = int(self.canvas_width / aspect_ratio)

                if self.recording:
                    writing_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    self.video_recorder.write(writing_frame)

                frame = cv2.resize(frame, (new_width, new_height))
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image=image)

                self.camera_label.config(image=photo, width=new_width, height=new_height)
                self.camera_label.image = photo


            self.master.after(10, update_feed)
        
        update_feed()

def main():
    root = tk.Tk()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = App(master=root, async_loop=loop)
    app.main_loop()
    loop.close()

if __name__ == "__main__":
    main()
