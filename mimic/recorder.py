import argparse
import threading
import time

import scipy.stats
import numpy as np
from pynput import mouse, keyboard

class Recorder:
    def __init__(self, stop_key_char='s'):
        self.stop_key = keyboard.KeyCode.from_char(stop_key_char)
        self.recording_stopped = threading.Event()
        self.generating_stopped = threading.Event()

    def on_press_common(self, key):
        if key == self.stop_key:
            self.recording_stopped.set()

    def start_recording(self):
        self.recording_stopped.wait()

    def generate_and_execute_tasks(self, number_of_tasks=10):
        raise NotImplementedError("This method should be implemented by subclasses.")

    def on_any_input(self, *args):
        self.generating_stopped.set()

    def run(self):
        raise NotImplementedError("This method should be implemented by subclasses.")



class ClickRecorder(Recorder):
    def __init__(self, stop_key_char='s'):
        super().__init__(stop_key_char)
        self.click_times = []
    
    def on_click(self, x, y, button, pressed):
        if pressed and not self.recording_stopped.is_set():
            click_time = time.time()
            if self.click_times:
                interval = click_time - self.click_times[-1]
                print(f"Recorded interval: {interval}")
            self.click_times.append(click_time)

    def start_recording(self):
        print(f"Recording clicks... Press {self.stop_key} to stop.")
        with mouse.Listener(on_click=self.on_click) as listener_mouse, \
             keyboard.Listener(on_press=self.on_press_common) as listener_keyboard:
            super().start_recording()  # Waits for the stop signal
        print(f"Recorded click intervals: {self.click_times}")

    def generate_and_execute_tasks(self, number_of_clicks=10):
        intervals = np.diff(self.click_times)
        if not intervals.size:
            print("Not enough intervals to calculate statistics.")
            return
        
        shape, loc, scale = scipy.stats.lognorm.fit(intervals, floc=0)
        synthetic_intervals = scipy.stats.lognorm.rvs(shape, loc, scale, size=number_of_clicks)
        jitter = np.random.uniform(-0.01 * scale, 0.01 * scale, number_of_clicks)
        synthetic_intervals = np.clip(synthetic_intervals, np.min(intervals), np.max(intervals))
        synthetic_intervals += jitter

        print(f"Generating and executing {number_of_clicks} synthetic clicks. Any user input will stop the script.")
        self.generating_stopped.clear()

        with mouse.Listener(on_move=self.on_any_input), keyboard.Listener(on_press=self.on_any_input):
            for interval in synthetic_intervals:
                if self.generating_stopped.is_set():
                    break
                time.sleep(interval)
                mouse.Controller().click(mouse.Button.left)
                print("Click: ", interval)

        if self.generating_stopped.is_set():
            print("Stopped click generation due to input.")

    def run(self):
        self.start_recording()
        self.generate_and_execute_tasks(parse_arguments().number_of_clicks)

    def run(self, number_of_clicks=10):  # Now accepts number_of_clicks as a parameter
        self.start_recording()
        self.generate_and_execute_tasks(number_of_clicks)  # Pass number_of_clicks to the method


def parse_arguments():
    parser = argparse.ArgumentParser(description='Record mouse clicks and generate synthetic clicks.')
    parser.add_argument('-n', '--number-of-clicks', type=int, default=100, help='Number of synthetic clicks to generate.')
    parser.add_argument('-s', '--stop-key', type=str, default='s', help='Key to press to stop recording.')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_arguments()
    click_recorder = ClickRecorder(stop_key_char=args.stop_key)
    click_recorder.run(args.number_of_clicks)

