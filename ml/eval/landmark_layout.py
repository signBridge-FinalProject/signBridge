"""Shared MediaPipe Holistic landmark layout (SB-15 standard, reused by SB-50).

Depends on numpy only, so it can be imported without mediapipe or OpenCV
installed. Moved here unchanged from ``mediapipe_eval.py`` so the SB-15
evaluation and the SB-50 batch extraction use one definition of the layout.
"""

import numpy as np

# Landmark groups in the fixed concatenation order used for the feature vector.
# Pose is the only group whose landmarks carry a meaningful visibility score.
GROUPS = [
    # (name, attribute on Holistic results, landmark count, fields)
    ("pose", "pose_landmarks", 33, ("x", "y", "z", "visibility")),
    ("face", "face_landmarks", 468, ("x", "y", "z")),
    ("left_hand", "left_hand_landmarks", 21, ("x", "y", "z")),
    ("right_hand", "right_hand_landmarks", 21, ("x", "y", "z")),
]


def group_array(landmark_list, count, fields):
    """Convert a MediaPipe landmark list to a (count, len(fields)) array.

    Returns None if the group was not detected in this frame.
    """
    if landmark_list is None:
        return None
    lms = landmark_list.landmark
    if len(lms) != count:
        raise ValueError(f"expected {count} landmarks, got {len(lms)}")
    return np.array([[getattr(lm, f) for f in fields] for lm in lms], dtype=np.float32)


def flatten_frame(arrays):
    """Concatenate all groups into one fixed-size vector (zero-fill missing groups)."""
    parts = []
    for name, _, count, fields in GROUPS:
        arr = arrays[name]
        if arr is None:
            arr = np.zeros((count, len(fields)), dtype=np.float32)
        parts.append(arr.reshape(-1))
    return np.concatenate(parts)
