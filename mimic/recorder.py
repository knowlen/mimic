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

    def run(self, number_of_clicks=10):  
        self.start_recording()
        self.generate_and_execute_tasks(number_of_clicks) 

class MouseRecorder(Recorder):
    def __init__(self, stop_key_char='s'):
        super().__init__(stop_key_char)
        self.mouse_events = []  # To store both clicks and movements
        self.ignore_input = False  # New flag to control input handling

    def on_click(self, x, y, button, pressed):
        # Record click event with timestamp
        event_time = time.time()
        self.mouse_events.append(('click', event_time, (x, y), button, pressed))

    def on_move(self, x, y):
        # Record movement event with timestamp
        event_time = time.time()
        # potential future optimization: limit data recorded to significant_move only
        if not self.mouse_events or (self.mouse_events[-1][0] != 'move' or self.significant_move(x, y)):
            self.mouse_events.append(('move', event_time, (x, y)))

    def significant_move(self, x, y):
        # placeholder 
        return True 

    def start_recording(self):
        print(f"Recording mouse clicks and movements... Press {self.stop_key.char} to stop.")
        with mouse.Listener(on_click=self.on_click, on_move=self.on_move) as listener_mouse, \
             keyboard.Listener(on_press=self.on_press_common) as listener_keyboard:
            super().start_recording()
        print(f"Recorded mouse events: {len(self.mouse_events)}")


    def on_any_input(self, *args):
        if not self.ignore_input:
            self.generating_stopped.set()

    def generate_and_execute_tasks(self, number_of_tasks=None):
        print("Generating and executing recorded mouse events. Any user input will stop the script.")
        self.generating_stopped.clear()
        
        # Use context managers to manage listeners without manual start or stop
        with mouse.Listener(on_move=self.on_any_input) as listener_mouse, keyboard.Listener(on_press=self.on_any_input) as listener_keyboard:
            prev_time = None
            for event_type, event_time, position, *args in self.mouse_events:
                if self.generating_stopped.is_set():
                    break

                # Delay to match the recorded timing, temporarily ignoring inputs
                if prev_time is not None:
                    self.ignore_input = True  # Ignore inputs during sleep
                    time.sleep(event_time - prev_time)
                    self.ignore_input = False  # Re-enable input handling after sleep

                if event_type == 'click':
                    button, pressed = args[0], args[1]
                    if pressed:
                        mouse.Controller().click(button)
                elif event_type == 'move':
                    mouse.Controller().position = position

                prev_time = event_time

            if not self.generating_stopped.is_set():
                print("Mouse event generation completed.")
            else:
                print("Stopped generation due to input.")

    def run(self, number_of_tasks=None):
        self.start_recording()
        self.generate_and_execute_tasks()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Record mouse clicks and generate synthetic clicks.')
    parser.add_argument('-n', '--number-of-clicks', type=int, default=100, help='Number of synthetic clicks to generate.')
    parser.add_argument('-s', '--stop-key', type=str, default='s', help='Key to press to stop recording.')
    parser.add_argument('-m', '--mode', type=str, default='clicks', help='Thing to record: clicks, mouse, keyboard, or all')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_arguments()
    if args.mode == 'clicks':
        click_recorder = ClickRecorder(stop_key_char=args.stop_key)
        click_recorder.run(args.number_of_clicks)
    elif args.mode == 'mouse':
        mouse_recorder = MouseRecorder(stop_key_char=args.stop_key)
        mouse_recorder.run()

