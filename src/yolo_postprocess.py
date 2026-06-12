import numpy as np


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.45) -> list[int]:
    if len(boxes) == 0:
        return []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1) * (y2 - y1)
    order = np.argsort(scores)[::-1]

    keep: list[int] = []
    while len(order) > 0:
        i = int(order[0])
        keep.append(i)
        if len(order) == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-10)

        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


def _map_bbox_to_original(
    bx1: float, by1: float, bx2: float, by2: float,
    orig_size: tuple[int, int],
    model_size: tuple[int, int],
) -> dict:
    """Map a bounding box from model input space back to original image pixel space."""
    src_w, src_h = orig_size
    target_w, target_h = model_size

    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2

    x1 = (bx1 + left) / scale
    y1 = (by1 + top) / scale
    x2 = (bx2 + left) / scale
    y2 = (by2 + top) / scale

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w = x2 - x1
    h = y2 - y1

    return {
        "x": round(cx, 1),
        "y": round(cy, 1),
        "width": round(w, 1),
        "height": round(h, 1),
    }


def extract_detections(
    predictions: np.ndarray,
    class_names: list[str],
    orig_size: tuple[int, int],
    model_size: tuple[int, int],
    conf_threshold: float = 0.3,
    iou_threshold: float = 0.45,
) -> tuple[str, float, list[dict]]:
    """Parse YOLO ONNX output, apply NMS, map bboxes to original image space."""
    preds = np.asarray(predictions)

    if preds.ndim == 3:
        p = preds[0]
        num_classes = len(class_names)

        if p.shape[0] == 4 + num_classes:
            cx = p[0, :]
            cy = p[1, :]
            w = p[2, :]
            h = p[3, :]
            scores = p[4:, :]

            scores = _sigmoid(scores)

            class_scores = np.max(scores, axis=0)
            class_ids = np.argmax(scores, axis=0)

            mask = class_scores >= conf_threshold
            if not np.any(mask):
                return "unknown_device", 0.0, []

            cx_arr, cy_arr = cx[mask], cy[mask]
            w_arr, h_arr = w[mask], h[mask]
            cs_arr = class_scores[mask]
            cid_arr = class_ids[mask]

            x1 = cx_arr - w_arr / 2
            y1 = cy_arr - h_arr / 2
            x2 = cx_arr + w_arr / 2
            y2 = cy_arr + h_arr / 2

            boxes = np.stack([x1, y1, x2, y2], axis=1)

            indices = nms(boxes, cs_arr, iou_threshold)

            if len(indices) == 0:
                return "unknown_device", 0.0, []

            # Keep top-K detections (limit to 10)
            top_k = min(len(indices), 10)
            indices = indices[:top_k]

            detections: list[dict] = []
            best_idx = indices[0]
            best_class_id = int(cid_arr[best_idx])
            best_conf = float(cs_arr[best_idx])
            best_class = (
                class_names[best_class_id]
                if 0 <= best_class_id < len(class_names)
                else "unknown_device"
            )

            for i in indices:
                cid = int(cid_arr[i])
                label = (
                    class_names[cid]
                    if 0 <= cid < len(class_names)
                    else "unknown"
                )
                conf = float(cs_arr[i])
                bx1_f, by1_f, bx2_f, by2_f = boxes[i].tolist()

                bbox = _map_bbox_to_original(
                    bx1_f, by1_f, bx2_f, by2_f,
                    orig_size, model_size,
                )
                detections.append({
                    "class": label,
                    "confidence": round(conf, 3),
                    "bbox": bbox,
                })

            return best_class, best_conf, detections

    return "unknown_device", 0.0, []
