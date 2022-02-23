import os
from pathlib import Path
from queue import Queue
from time import sleep
from typing import Dict

# pip install watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PATH_TO_WATCH = os.getcwd()


def main():
    handle_map: Dict[str, int] = {}

    def print_tail(file_path, file_handle, created: bool) -> bool:
        found_something = False
        current_pos = handle_map.get(file_path)
        if current_pos:
            # Seek to the last held position
            file_handle.seek(current_pos)
        elif not created:
            # This file was already there
            # we seek all the way to the end and just return
            file_handle.seek(0, os.SEEK_END)
            return True

        header_printed = False
        for line in file_handle:
            if not header_printed:
                print(f"\n{'-'*10}  {Path(file_path).name}  {'-'*10}")
                header_printed = True

            # Print each line
            print(line, end='', flush=True)
            found_something = True

        # Store the current position
        handle_map[file_path] = file_handle.tell()

        return found_something

    def print_tail_spin(*args, **kwargs):
        empty_requests = 0
        while True:
            if print_tail(*args, **kwargs):
                empty_requests = 0
            else:
                empty_requests += 1

            if empty_requests > 5:
                return

            sleep(0.3)

    def check_file(file_path, created: bool):
        try:
            with open(file_path) as file_handle:
                if created:
                    print_tail_spin(file_path, file_handle, True)
                else:
                    print_tail(file_path, file_handle, False)
        except (PermissionError, FileNotFoundError):
            # This happens a lot
            handle_map.pop(file_path, None)

    event_queue = Queue()

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            event_queue.put(event)

    custom_handler = Handler()

    def watchdog_monitor():
        ob = Observer()
        ob.schedule(custom_handler, PATH_TO_WATCH, recursive=True)
        ob.start()
        try:
            while True:
                event = event_queue.get()
                check_file(event.src_path, event.event_type == 'created')
                event_queue.task_done()
        finally:
            ob.stop()
            event_queue.join()
            ob.join()

    # Check files already in directory
    for path in Path(PATH_TO_WATCH).rglob("*.log"):
        check_file(str(path.resolve()), False)

    watchdog_monitor()


if __name__ == "__main__":
    main()
