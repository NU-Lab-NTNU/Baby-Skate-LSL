import csv
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider, TextBox
import matplotlib.patches as patches
import tkinter as tk
from tkinter import filedialog
import datetime

def load_data(filepath):
    timestamps = []
    x = []
    y = []
    yaw = []

    with open(filepath, 'r') as data_file:
        data_reader = csv.reader(data_file)
        next(data_reader)
        for row in data_reader:
            timestamps.append(datetime.datetime.strptime(row[0][:-2], "%Y-%m-%dT%H:%M:%S.%f"))
            x.append(float(row[1]))
            y.append(float(row[2]))
            yaw.append(float(row[6]))
        
        timestamps = [round((timestamp - timestamps[0]).total_seconds(), 2) for timestamp in timestamps]
        return np.array(timestamps), np.array(x), np.array(y), np.array(yaw)
    

def open_file_dialog():
    root = tk.Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(title="Select a trial to visualise", filetypes=[("CSV files", "*.csv")])
    return filepath

def update(sample):
    x_subset = x[:sample+1]
    y_subset = y[:sample+1]
    valid_indices = np.isfinite(x_subset) & np.isfinite(y_subset)
    trajectory.set_data(x_subset[valid_indices], y_subset[valid_indices])

    if sample > 0 and np.isfinite(x[sample]) and np.isfinite(y[sample]) and np.isfinite(yaw[sample]):
        dx = np.cos(np.deg2rad(yaw[sample]))
        dy = np.sin(np.deg2rad(yaw[sample]))
        arrow.set_positions((x[sample], y[sample]), (x[sample] + 0.2*dx, y[sample] + 0.2*dy))
        #arrow_angle = np.deg2rad(yaw[sample])
        #arrow.set_transform(ax.transData + Affine2D().rotate_around(x[sample], y[sample], arrow_angle))
        slider.label.set_text(timestamps[sample])

    timestamp_text.set_val(timestamps[sample])
    fig.canvas.draw_idle()

def main():
    global timestamp_text, timestamps, x, y, yaw, slider, trajectory, arrow, fig, ax, slider
    
    filepath = open_file_dialog()
    print(filepath)
    timestamps, x, y, yaw = load_data(filepath)

    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    ax.set_xlim(-2, 2)
    ax.set_ylim(-2, 2)
    ax.axhline(0, color='black', linewidth=0.2)
    ax.axvline(0, color='black', linewidth=0.2)
    plt.subplots_adjust(bottom=0.15)

    title_text = filepath.split('/')
    participant_name = title_text[-2].split('_')[-1]
    trial_number = title_text[-1].split('_')[1]
    start_angle = title_text[-1].split('_')[3]
    ax.set_title(f"Trajectory for {participant_name}: Trial {trial_number}, Starting Angle {start_angle} degrees")
    ax.set_xlabel("Room Width [m]")
    ax.set_ylabel("Room Length [m]")

    trajectory, = ax.plot([], [], 'b-', lw=2)
    
    arrow = patches.FancyArrowPatch((0, 0), (0, 0), color='r', mutation_scale=15)
    ax.add_patch(arrow)

    axslider = plt.axes([0.2, 0.02, 0.65, 0.03], facecolor="lightgoldenrodyellow")

    slider = Slider(axslider, 't(s): ', 0, len(timestamps) - 1, valinit=0, valstep=1)

    slider.on_changed(update)

    axtimestamp = plt.axes([0.2, 0.05, 0.65, 0.03], facecolor="lightgoldenrodyellow")
    timestamp_text = TextBox(axtimestamp, 'Timepoint since start of trial in seconds: ', initial=timestamps[0])

    plt.show()

if __name__ == '__main__':
    main()
