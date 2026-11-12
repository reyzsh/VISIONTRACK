from ultralytics import YOLO


class ByteTrackTracker:
    def __init__(self, model_path="yolo11n.pt"):
        # Load YOLO model
        self.model = YOLO(model_path)

    def update(self, frame):
        """
        Takes one webcam frame and tracks objects using ByteTrack.

        Returns:
            YOLO tracking result for the current frame.
        """

        results = self.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        return results[0]