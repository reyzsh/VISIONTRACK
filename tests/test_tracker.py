import cv2
from tracker import ByteTrackTracker


def main():
    # Create the ByteTrack tracker
    tracker = ByteTrackTracker()

    # Open laptop webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Webcam started.")
    print("Move objects/persons in front of the camera.")
    print("Press Q to quit.")

    while True:
        # Read one frame from webcam
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read frame.")
            break

        # Send frame to YOLO + ByteTrack
        result = tracker.update(frame)

        # Draw bounding boxes and tracking IDs
        annotated_frame = result.plot()

        # Display the result
        cv2.imshow("ByteTrack Object Tracking", annotated_frame)

        # Press Q to exit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Release webcam
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()