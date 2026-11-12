import csv
from pathlib import Path
from datetime import datetime


class EventLogger:
    def __init__(self, filename="events.csv"):
        self.filename = Path(__file__).resolve().parent / filename

        # Create the CSV file and its headers if it doesn't exist
        if not self.filename.exists():
            with open(self.filename, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "timestamp",
                    "label",
                    "event_type"
                ])

        print(f"Event log file: {self.filename}")

    def log_event(self, label, event_type):
        with open(self.filename, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                label,
                event_type
            ])

        print(f"Logged: {label} - {event_type}")
