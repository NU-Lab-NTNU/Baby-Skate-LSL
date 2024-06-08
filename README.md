# Baby Skate Mocap Recording

## Intro
This repo is heavily based on [the Qualisys LSL app](https://github.com/qualisys/qualisys_lsl_app), mostly changing the GUI to suit our needs.
Proper documentation coming soon (TM).

The data saved is:
- an Excel file containing all 6DOF measurements with timestamps
    - three different 6DOF bodies are defined: baby on little skate, baby on big skate, and mother.
- an .mp4 video from the USB webcam that records the entire field of movement

WIP:
- Excel file with movement data on specific markers (on feet)

## GUI
There are two different GUIs, the old one being more primitive and basically a carbon copy of the Qualisys LSL app. To make things easier for the experimenters that have to do a lot of work around the baby anyways, a newer GUI is provided with what's hopefully less complexity and fewer things to think about before actually doing a recording.

Disclaimer: I am in no way, shape or form a graphics designer, so things don't look pretty, but I can promise they work at least. :)

## Data visualisation
The data visualisation folder currently has a simple script that loads the recorded data from the Excel file where you can drag along the timeline and see exactly the sample and the timestamp of any movement. The direction the baby is pointing towards is also displayed in the form of an arrow.

No analysis is done in this little program, it only serves as a little visualisation of how a single trial went.

Planned TODO: Add in mother trajectory as well, and be able to toggle between showing it and not.