import argparse
import time
import threading

import numpy as np
from pynput import mouse, keyboard

class ClickRecorder:
    def __init__(self, stop_key_char='s'):
        self.stop_key = keyboard.KeyCode.from_char(stop_key_char)
        self.click_times = []
        self.last_click_time = None
        self.generate_clicks_running = threading.Event()
        self.listener_mouse = None
        self.listener_keyboard = None

    def on_click(self, x, y, button, pressed):
        if pressed:
            click_time = time.time()
            if self.last_click_time is not None:
                interval = click_time - self.last_click_time
                self.click_times.append(click_time)
                print(f"Recorded interval: {interval}")
            self.last_click_time = click_time

    def on_press_during_recording(self, key):
        if key == self.stop_key:
            print("Stop key pressed, stopping recording...")
            self.listener_mouse.stop()
            self.listener_keyboard.stop()

    def on_press_during_generation(self, key):
        if key == self.stop_key:
            print("Stop key pressed, stopping generation of clicks...")
            self.generate_clicks_running.clear()

    def start_listeners(self, on_press_method):
        with mouse.Listener(on_click=self.on_click) as self.listener_mouse, keyboard.Listener(on_press=on_press_method) as self.listener_keyboard:
            self.listener_mouse.join()
            self.listener_keyboard.join()

    def start_recording(self):
        print("Recording... Press ` to stop.")
        self.start_listeners(self.on_press_during_recording)
        print(f"Recorded click intervals: {self.click_times}")

    def generate_and_execute_clicks(self, number_of_clicks=10):
        if len(self.click_times) < 3:
            print("Not enough clicks recorded to generate intervals. Need at least 3 clicks.")
            return

        # Calculate intervals
        intervals = np.diff(self.click_times)
        if len(intervals) == 0:
            print("Not enough intervals to calculate statistics.")
            return

        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)

        self.generate_clicks_running.set()
        listener_keyboard = keyboard.Listener(on_press=self.on_press_during_generation)
        listener_keyboard.start()

        print(f"Generating and executing {number_of_clicks} synthetic clicks. Press ` to stop.")
        for _ in range(number_of_clicks):
            if not self.generate_clicks_running.is_set():
                break  # Early exit if stop key is pressed
            synthetic_interval = np.random.normal(mean_interval, std_interval)
            print(f"Waiting {synthetic_interval:.2f} seconds to click.")
            time.sleep(max(synthetic_interval, 0.1))  # Ensure non-negative sleep time
            mouse.Controller().click(mouse.Button.left)
            print("Click.")

        listener_keyboard.stop()


def parse_arguments():
    parser = argparse.ArgumentParser(description='Record mouse clicks and generate synthetic clicks.')
    parser.add_argument('-n', '--number-of-clicks', type=int, default=10, help='Number of synthetic clicks to generate.')
    parser.add_argument('-s', '--stop-key', type=str, default='s', help='Key to press to stop recording or click generation.')
    
    args = parser.parse_args()
    return args.number_of_clicks, args.stop_key

if __name__ == "__main__":
    number_of_clicks, stop_key_char = parse_arguments()
    click_recorder = ClickRecorder(stop_key_char=stop_key_char)
    click_recorder.start_recording()
    click_recorder.generate_and_execute_clicks(number_of_clicks=number_of_clicks)
