"""
detector.py

Object detection using a pretrained YOLO model (Ultralytics).

Takes a single BGR frame (a NumPy array, as returned by OpenCV from a webcam
or cv2.imread) and returns a list of Detection objects.

This module only does detection. It does not do tracking, counting,
or any dashboard work.

Install:
    pip install ultralytics opencv-python
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass(frozen=True)
class Detection:
    """One detected object in a frame."""

    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Bounding box as (x1, y1, x2, y2) in pixel coordinates."""
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def center(self) -> Tuple[int, int]:
        """Center point (cx, cy) of the bounding box."""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def __str__(self) -> str:
        return f"{self.class_name} {self.confidence:.2f} {self.bbox}"


class ObjectDetector:
    """Wraps a pretrained YOLO model for single-frame object detection.

    Example:
        detector = ObjectDetector()
        detections = detector.detect(frame)
        annotated = detector.draw(frame, detections)
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
        iou_threshold: float = 0.45,
        classes: Optional[Sequence[int]] = None,
        device: Optional[str] = None,
        image_size: int = 640,
    ) -> None:
        """
        Args:
            model_path: Pretrained weights. "yolov8n.pt" is small and fast and is
                downloaded automatically on first use. Others: yolov8s.pt,
                yolov8m.pt, yolo11n.pt, etc.
            conf_threshold: Minimum confidence (0-1) to keep a detection.
            iou_threshold: IoU threshold for non-maximum suppression.
            classes: Optional list of class IDs to keep (e.g. [0] for person only).
                None keeps all 80 COCO classes.
            device: "cpu", "cuda", "cuda:0", "mps", or None to auto-select.
            image_size: Inference image size. Smaller is faster.
        """
        if not 0.0 <= conf_threshold <= 1.0:
            raise ValueError("conf_threshold must be between 0 and 1")
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1")

        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.classes = list(classes) if classes is not None else None
        self.device = device
        self.image_size = image_size

        self.model = YOLO(model_path)
        # Maps class id -> class name, e.g. {0: "person", 39: "bottle", ...}
        self.class_names = self.model.names

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run detection on one frame.

        Args:
            frame: BGR image as a NumPy array of shape (H, W, 3), the format
                OpenCV gives you from VideoCapture.read() or cv2.imread().

        Returns:
            A list of Detection objects (empty if nothing was found).
        """
        self._validate_frame(frame)

        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            classes=self.classes,
            device=self.device,
            imgsz=self.image_size,
            verbose=False,
        )

        detections: List[Detection] = []
        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)

        for (x1, y1, x2, y2), conf, cid in zip(xyxy, confs, class_ids):
            detections.append(
                Detection(
                    class_id=int(cid),
                    class_name=str(self.class_names[int(cid)]),
                    confidence=float(conf),
                    x1=int(x1),
                    y1=int(y1),
                    x2=int(x2),
                    y2=int(y2),
                )
            )
        return detections

    def detect_image_file(self, path: str) -> List[Detection]:
        """Convenience: load an image from disk and run detection on it."""
        frame = cv2.imread(path)
        if frame is None:
            raise FileNotFoundError(f"Could not read image: {path}")
        return self.detect(frame)

    def draw(
        self,
        frame: np.ndarray,
        detections: Iterable[Detection],
        color: Tuple[int, int, int] = (0, 200, 0),
    ) -> np.ndarray:
        """Return a copy of `frame` with boxes and labels drawn on it."""
        annotated = frame.copy()
        for det in detections:
            cv2.rectangle(annotated, (det.x1, det.y1), (det.x2, det.y2), color, 2)

            label = f"{det.class_name} {det.confidence:.2f}"
            (tw, th), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            # Keep the label inside the frame if the box touches the top edge.
            label_top = max(det.y1 - th - baseline, 0)
            cv2.rectangle(
                annotated,
                (det.x1, label_top),
                (det.x1 + tw + 4, label_top + th + baseline),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (det.x1 + 2, label_top + th),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )
        return annotated

    @staticmethod
    def _validate_frame(frame: np.ndarray) -> None:
        if not isinstance(frame, np.ndarray):
            raise TypeError("frame must be a NumPy array (BGR image)")
        if frame.size == 0:
            raise ValueError("frame is empty")
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"frame must have shape (H, W, 3), got {frame.shape}"
            )
