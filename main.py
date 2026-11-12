
import cv2
from pathlib import Path
from tracker import ByteTrackTracker
from counter import LineCounter
from event_logger import EventLogger


def main():
    print("Loading YOLO model and starting VISIONTRACK...")

    tracker = ByteTrackTracker(model_path="yolo11n.pt")

    # Save both files in the project folder.
    project_dir = Path(__file__).resolve().parent
    csv_path = project_dir / "events.csv"
    frame_path = project_dir / "latest_frame.jpg"

    logger = EventLogger(str(csv_path))
    print("CSV will be saved to:", csv_path)

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        return

    counter = None
    frame_count = 0

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("ERROR: Could not read camera frame.")
                break

            height, width = frame.shape[:2]

            if counter is None:
                counter = LineCounter(
                    line_y=height // 2,
                    margin=10,
                    entry_direction="down",
                    line_x_range=(0, width),
                )

            # Detect and track objects.
            result = tracker.update(frame)
            boxes = result.boxes

            if boxes is not None and boxes.id is not None:
                track_ids = boxes.id.int().cpu().tolist()
                coordinates = boxes.xyxy.cpu().tolist()
                class_ids = boxes.cls.int().cpu().tolist()

                for track_id, box, class_id in zip(
                    track_ids, coordinates, class_ids
                ):
                    x1, y1, x2, y2 = box

                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    label = result.names[int(class_id)]

                    event = counter.update(
                        object_id=int(track_id),
                        x=center_x,
                        y=center_y,
                        label=label,
                    )

                    if event is not None:
                        print(
                            f"CROSSING DETECTED: "
                            f"{event.event_type}, ID={event.object_id}"
                        )

                        logger.log_event(
                            event.label,
                            event.event_type,
                        )

            # Draw detections and counting line.
            display = result.plot()

            cv2.line(
                display,
                (0, height // 2),
                (width, height // 2),
                (0, 255, 255),
                2,
            )

            stats = counter.get_statistics()

            cv2.putText(
                display,
                f"ENTRY: {stats['total_entries']}  "
                f"EXIT: {stats['total_exits']}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            # Save every fifth processed frame for the dashboard.
            frame_count += 1
            if frame_count % 5 == 0:
                cv2.imwrite(str(frame_path), display)

            # Show the webcam window.
            cv2.imshow("VISIONTRACK - Object Counter", display)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    print("VISIONTRACK stopped.")
    print("CSV file:", csv_path)
    print("Latest frame:", frame_path)


if __name__ == "__main__":
    main()
