import argparse
import threading
import time
import numpy as np
import scipy.stats
from pynput import mouse, keyboard

class ClickRecorder:
    def __init__(self, stop_key_char='s'):
        self.stop_key = keyboard.KeyCode.from_char(stop_key_char)
        self.click_times = []
        self.last_click_time = None
        self.recording_stopped = threading.Event()
        self.generating_stopped = threading.Event()

    def on_click(self, x, y, button, pressed):
        if pressed and not self.recording_stopped.is_set():
            click_time = time.time()
            if self.last_click_time is not None:
                interval = click_time - self.last_click_time
                self.click_times.append(click_time)
                print(f"Recorded interval: {interval}")
            self.last_click_time = click_time

    def on_move_during_generation(self, x, y):
        print("Input detected, stopping click generation...")
        self.generating_stopped.set()

    def on_press_during_recording(self, key):
        if key == self.stop_key:
            print("Stop key pressed, stopping recording...")
            self.recording_stopped.set()

    def on_press_during_generation(self, key):
        print("Input detected, stopping click generation...")
        self.generating_stopped.set()

    def start_recording(self):
        print(f"Recording... Press {self.stop_key} to stop.")
        with mouse.Listener(on_click=self.on_click) as self.listener_mouse, \
             keyboard.Listener(on_press=self.on_press_during_recording) as self.listener_keyboard:
            self.recording_stopped.wait()
        print(f"Recorded click intervals: {self.click_times}")


    def generate_and_execute_clicks(self, number_of_clicks=10):
        if len(self.click_times) < 3:
            print("Not enough clicks recorded to generate intervals. Need at least 3 clicks.")
            return

        intervals = np.diff(self.click_times)
        if len(intervals) == 0:
            print("Not enough intervals to calculate statistics.")
            return

        # Fit a log-normal distribution to the recorded intervals
        shape, loc, scale = scipy.stats.lognorm.fit(intervals, floc=0)
        
        # Generate synthetic intervals from the fitted distribution
        synthetic_intervals = scipy.stats.lognorm.rvs(shape, loc, scale, size=number_of_clicks)
        
        # Add jitter after generation
        jitter_magnitude = 0.01 * scale
        jitter = np.random.uniform(-jitter_magnitude, jitter_magnitude, number_of_clicks)
        synthetic_intervals = np.clip(synthetic_intervals, np.min(intervals), np.max(intervals))
        synthetic_intervals += jitter

        print(f"Generating and executing {number_of_clicks} synthetic clicks. Any user input will stop the script.")
        self.generating_stopped.clear()

        # Use a local function to handle stop signal without printing
        def on_any_input(*args):
            self.generating_stopped.set()

        with mouse.Listener(on_move=on_any_input) as listener_mouse, \
             keyboard.Listener(on_press=on_any_input) as listener_keyboard:

            for interval in synthetic_intervals:
                if self.generating_stopped.is_set():
                    break
                
                #print(f"Waiting {interval:.2f} seconds to click.")
                start_time = time.time()
                while time.time() - start_time < interval:
                    if self.generating_stopped.is_set():
                        break
                    time.sleep(0.01)  # Short sleep to frequently check the stop condition
                
                if not self.generating_stopped.is_set():
                    mouse.Controller().click(mouse.Button.left)
                    print("Click.")
                else:
                    break

        # After breaking out of the loop, check if it was due to input
        if self.generating_stopped.is_set():
            print("Stopped click generation due to input.")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Record mouse clicks and generate synthetic clicks.')
    parser.add_argument('-n', '--number-of-clicks', type=int, default=100, help='Number of synthetic clicks to generate.')
    parser.add_argument('-s', '--stop-key', type=str, default='s', help='Key to press to stop recording.')
    args = parser.parse_args()
    return args.number_of_clicks, args.stop_key

if __name__ == "__main__":
    number_of_clicks, stop_key_char = parse_arguments()
    click_recorder = ClickRecorder(stop_key_char=stop_key_char)
    click_recorder.start_recording()
    click_recorder.generate_and_execute_clicks(number_of_clicks=number_of_clicks)

