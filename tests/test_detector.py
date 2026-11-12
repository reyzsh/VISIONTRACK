"""
test_detector.py

Opens the webcam, runs ObjectDetector on every frame, and shows the result in
a window so you can confirm detection works.

Run:
    python test_detector.py                  # webcam 0
    python test_detector.py --camera 1       # a different camera
    python test_detector.py --image pic.jpg  # test on a still image instead
    python test_detector.py --classes 0 39   # only person and bottle

Controls:
    q or ESC  -> quit
    s         -> save the current annotated frame as snapshot.jpg

Note: this is a manual demo script, so it is not meant for pytest.
"""

from __future__ import annotations

import argparse
import platform
import sys
import time

import cv2

from detector import ObjectDetector


def open_camera(index: int) -> cv2.VideoCapture:
    """Open the webcam. On Windows, DirectShow starts faster and more reliably."""
    if platform.system() == "Windows":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(index)
    return cap


def run_image_test(detector: ObjectDetector, path: str) -> int:
    frame = cv2.imread(path)
    if frame is None:
        print(f"ERROR: could not read image '{path}'")
        return 1

    detections = detector.detect(frame)
    print(f"Found {len(detections)} object(s) in {path}:")
    for det in detections:
        print(f"  {det}")

    cv2.imshow("Detection test (press any key to close)", detector.draw(frame, detections))
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return 0


def run_webcam_test(detector: ObjectDetector, camera_index: int) -> int:
    cap = open_camera(camera_index)
    if not cap.isOpened():
        print(
            f"ERROR: could not open camera {camera_index}. "
            "Check that it is connected, not used by another app, "
            "and that camera permission is allowed."
        )
        return 1

    print("Webcam opened. Press 'q' or ESC in the video window to quit.")

    window = "Object Detection Test"
    last_print = 0.0
    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("ERROR: failed to read a frame from the camera.")
                return 1

            detections = detector.detect(frame)
            annotated = detector.draw(frame, detections)

            # Smoothed FPS
            now = time.time()
            instant_fps = 1.0 / max(now - prev_time, 1e-6)
            fps = instant_fps if fps == 0.0 else 0.9 * fps + 0.1 * instant_fps
            prev_time = now

            cv2.putText(
                annotated,
                f"FPS: {fps:.1f}  Objects: {len(detections)}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(window, annotated)

            # Print detections to the terminal about once per second.
            if now - last_print >= 1.0 and detections:
                names = ", ".join(
                    f"{d.class_name}({d.confidence:.2f})" for d in detections
                )
                print(f"Detected: {names}")
                last_print = now

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                cv2.imwrite("snapshot.jpg", annotated)
                print("Saved snapshot.jpg")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Webcam test for ObjectDetector")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default 0)")
    parser.add_argument("--image", type=str, default=None, help="Test on an image file instead of the webcam")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO weights (default yolov8n.pt)")
    parser.add_argument("--conf", type=float, default=0.4, help="Confidence threshold (default 0.4)")
    parser.add_argument("--classes", type=int, nargs="*", default=None, help="Class IDs to keep, e.g. 0 for person")
    parser.add_argument("--device", type=str, default=None, help="cpu, cuda, mps (default: auto)")
    args = parser.parse_args()

    print(f"Loading model {args.model} (downloads on first run)...")
    detector = ObjectDetector(
        model_path=args.model,
        conf_threshold=args.conf,
        classes=args.classes,
        device=args.device,
    )
    print("Model loaded.")

    if args.image:
        return run_image_test(detector, args.image)
    return run_webcam_test(detector, args.camera)


if __name__ == "__main__":
    sys.exit(main())
