import io
import secrets
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import qrcode
from PIL import Image, ImageChops, ImageOps
from qrcode.constants import ERROR_CORRECT_M

from client.crypto.shamir import Share

QR_SCALE = 12
SHARE_SCALE = 6
PATTERNS = (
    ((1, 0), (0, 1)),
    ((0, 1), (1, 0)),
)


@dataclass(slots=True)
class RecoveryShareVisualAssets:
    qr_code: bytes
    share_one: bytes
    share_two: bytes
    overlay: bytes


@dataclass(slots=True)
class RecoveryShareVisualReconstruction:
    recovery_share: str
    qr_code: bytes
    overlay: bytes


def create_recovery_share_visuals(recovery_share: str) -> RecoveryShareVisualAssets:
    qr_matrix = _qr_matrix(recovery_share)
    share_one, share_two = _split_matrix(qr_matrix)
    overlay = _overlay_matrices(share_one, share_two)
    return RecoveryShareVisualAssets(
        qr_code=_matrix_to_png(qr_matrix, QR_SCALE),
        share_one=_matrix_to_png(share_one, SHARE_SCALE),
        share_two=_matrix_to_png(share_two, SHARE_SCALE),
        overlay=_matrix_to_png(overlay, SHARE_SCALE),
    )


def recover_recovery_share_from_visuals(share_one_path: str, share_two_path: str) -> str:
    return reconstruct_recovery_share_visuals(share_one_path, share_two_path).recovery_share


def reconstruct_recovery_share_visuals(
    share_one_path: str,
    share_two_path: str,
) -> RecoveryShareVisualReconstruction:
    first = _load_visual_share_image(share_one_path)
    second = _load_visual_share_image(share_two_path)
    if first.size != second.size:
        raise ValueError("visual share images must have the same dimensions")
    overlay = ImageChops.darker(first, second)
    qr_image = _recover_qr_image(_image_to_matrix(overlay, SHARE_SCALE))
    payload = _decode_qr_payload(qr_image)
    try:
        Share.from_text(payload)
    except ValueError as exc:
        raise ValueError("visual shares did not reconstruct a valid recovery share") from exc
    return RecoveryShareVisualReconstruction(
        recovery_share=payload,
        qr_code=_image_to_png(qr_image),
        overlay=_image_to_png(overlay),
    )


def _qr_matrix(payload: str) -> list[list[int]]:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    return [[1 if cell else 0 for cell in row] for row in qr.get_matrix()]


def _split_matrix(matrix: list[list[int]]) -> tuple[list[list[int]], list[list[int]]]:
    height = len(matrix)
    width = len(matrix[0]) if matrix else 0
    share_one = [[0] * (width * 2) for _ in range(height * 2)]
    share_two = [[0] * (width * 2) for _ in range(height * 2)]
    for y, row in enumerate(matrix):
        for x, cell in enumerate(row):
            pattern = secrets.choice(PATTERNS)
            partner = _invert_pattern(pattern) if cell else pattern
            _paint_pattern(share_one, x * 2, y * 2, pattern)
            _paint_pattern(share_two, x * 2, y * 2, partner)
    return share_one, share_two


def _invert_pattern(pattern: tuple[tuple[int, int], tuple[int, int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    return tuple(tuple(0 if value else 1 for value in row) for row in pattern)


def _paint_pattern(
    canvas: list[list[int]],
    start_x: int,
    start_y: int,
    pattern: tuple[tuple[int, int], tuple[int, int]],
) -> None:
    for offset_y, row in enumerate(pattern):
        for offset_x, value in enumerate(row):
            canvas[start_y + offset_y][start_x + offset_x] = value


def _overlay_matrices(first: list[list[int]], second: list[list[int]]) -> list[list[int]]:
    return [
        [1 if left or right else 0 for left, right in zip(first_row, second_row, strict=True)]
        for first_row, second_row in zip(first, second, strict=True)
    ]


def _matrix_to_png(matrix: list[list[int]], scale: int) -> bytes:
    image = _matrix_to_image(matrix, scale)
    return _image_to_png(image)


def _image_to_png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _load_visual_share_image(path: str) -> Image.Image:
    expanded_path = Path(path).expanduser()
    if not expanded_path.is_absolute():
        raise ValueError(f"visual share image path must be absolute: {path}")
    try:
        with Image.open(expanded_path) as image:
            grayscale = ImageOps.grayscale(image)
            return grayscale.point(lambda value: 0 if value < 128 else 255, mode="L")
    except FileNotFoundError as exc:
        raise ValueError(f"visual share image not found: {path}") from exc
    except OSError as exc:
        raise ValueError(f"invalid visual share image: {path}") from exc


def _decode_qr_payload(image: Image.Image) -> str:
    detector = cv2.QRCodeDetector()
    payload, _, _ = detector.detectAndDecode(cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR))
    payload = payload.strip()
    if not payload:
        raise ValueError("visual shares did not reconstruct a decodable recovery QR")
    return payload


def _recover_qr_image(overlay_matrix: list[list[int]]) -> Image.Image:
    height = len(overlay_matrix)
    width = len(overlay_matrix[0]) if overlay_matrix else 0
    if width % 2 != 0 or height % 2 != 0:
        raise ValueError("visual share images have invalid dimensions")
    matrix: list[list[int]] = []
    for start_y in range(0, height, 2):
        row: list[int] = []
        for start_x in range(0, width, 2):
            black_pixels = 0
            for offset_y in range(2):
                for offset_x in range(2):
                    if overlay_matrix[start_y + offset_y][start_x + offset_x] == 1:
                        black_pixels += 1
            row.append(1 if black_pixels >= 3 else 0)
        matrix.append(row)
    return _matrix_to_image(matrix, QR_SCALE)


def _matrix_to_image(matrix: list[list[int]], scale: int) -> Image.Image:
    height = len(matrix)
    width = len(matrix[0]) if matrix else 0
    image = Image.new("L", (width, height), 255)
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            image.putpixel((x, y), 0 if value else 255)
    return image.resize((width * scale, height * scale), resample=Image.Resampling.NEAREST)


def _image_to_matrix(image: Image.Image, scale: int) -> list[list[int]]:
    width, height = image.size
    if width % scale != 0 or height % scale != 0:
        raise ValueError("visual share images have invalid dimensions")
    matrix: list[list[int]] = []
    for start_y in range(0, height, scale):
        row: list[int] = []
        for start_x in range(0, width, scale):
            black_pixels = 0
            for offset_y in range(scale):
                for offset_x in range(scale):
                    if image.getpixel((start_x + offset_x, start_y + offset_y)) == 0:
                        black_pixels += 1
            row.append(1 if black_pixels >= (scale * scale) // 2 else 0)
        matrix.append(row)
    return matrix