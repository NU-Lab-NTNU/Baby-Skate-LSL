import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
from enum import Enum
import os
from datetime import datetime

class PickingPhase(Enum):
    BABY_POSITION = 0
    MOTHER_POSITION = 1
    CONFIRM = 2

class App(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.grid(sticky="nsew")
        self.canvas_width = 800
        self.canvas_height = 800
        self.visible_circles_mask = [1, 1, 1, 1, 1, 0, 0]
        self.circle_ids = [None] * 7
        self.picking_phase = PickingPhase.BABY_POSITION
        self.baby_and_mother_idxs = [None, None]
        self.parent_directory = 'C:\\Users\\QTM\\Desktop\\motion_capture_data'
        self.create_layout()

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
        circle_id = event.widget.find_closest(event.x, event.y + 200)[0]
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
        
    def start_recording(self):
        self.participant_name_entry.config(state='readonly')
        self.degree_entry.config(state='readonly')
        self.folder_button.config(state='disabled')
        self.phase_description.set("Recording In Progress")
        self.target_folder = f"{self.parent_directory.get()}\\{datetime.now().strftime('%Y-%m-%d')}_{self.participant_name.get()}"
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)
        self.cancel_button.grid_remove()
        self.start_recording_button.grid_remove()
        self.stop_recording_button = tk.Button(self.interactive_frame, text="STOP RECORDING", bg="darkred", fg="white", command=self.stop_recording)
        self.stop_recording_button.grid(row=5, column=0, columnspan=1, sticky="ew", padx=5, pady=5)

    def stop_recording(self):
        self.phase_description.set("Do you want to keep this trial or record over it?")
        self.stop_recording_button.grid_remove()
        self.continue_trial_button = tk.Button(self.interactive_frame, text="No, this was a bad trial. Record over it.", bg="darkred", fg="white", command=self.record_over_trial)
        self.continue_trial_button.grid(row=4, column=0, columnspan=1, sticky="ew", padx=5, pady=5)
        
        self.record_over_trial_button = tk.Button(self.interactive_frame, text="Yes, go to the next trial.", bg="darkgreen", fg="white", command=self.goto_new_trial)
        self.record_over_trial_button.grid(row=5, column=0, columnspan=1, sticky="ew", padx=5, pady=5)
    
    def goto_new_trial(self):
        self.continue_trial_button.grid_remove()
        self.record_over_trial_button.grid_remove()
        self.trial_number += 1
        self.trial_number_str.set(f"Trial number: {self.trial_number}")
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
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        def update_feed():
            ret, frame = cap.read()
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

                frame = cv2.resize(frame, (new_width, new_height))
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image=image)

                self.camera_label.config(image=photo, width=new_width, height=new_height)
                self.camera_label.image = photo


            self.master.after(10, update_feed)
        
        update_feed()

def main():
    root = tk.Tk()
    root.title("Motion Capture Recording")
    app = App(master=root)
    app.mainloop()

if __name__ == "__main__":
    main()
