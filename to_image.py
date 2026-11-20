import os
import json
from io import BytesIO
import requests
from PIL import Image, ImageDraw

def draw_boxes_on_image(
    image_source: str,
    boxes: list,
    output_path: str = None,
    color: str = "#ff2852",
    compare_boxes: list = None,
    compare_color: str = "#00c853",
    max_width: int = 1200,
) -> Image.Image:
    """
    Рисует нормализованные рамки [{"left", "top", "width", "height"}] на фото.
    image_source: путь к локальному файлу или HTTP/HTTPS ссылка.
    compare_boxes: (опционально) второй список рамок другим цветом для сравнения.
    """
    # 1. Загружаем изображение (URL или локальный файл)
    if image_source.startswith(("http://", "https://")):
        resp = requests.get(image_source, timeout=30)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
    else:
        img = Image.open(image_source).convert("RGB")

    w, h = img.size
    draw = ImageDraw.Draw(img)
    line_w = max(3, int(min(w, h) * 0.006))

    # Функция отрисовки списка рамок
    def _draw_list(box_list, box_color):
        for b in box_list:
            x0 = int(w * float(b["left"]))
            y0 = int(h * float(b["top"]))
            x1 = int(w * (float(b["left"]) + float(b["width"])))
            y1 = int(h * (float(b["top"]) + float(b["height"])))
            draw.rectangle([x0, y0, x1, y1], outline=box_color, width=line_w)

    # Сначала рисуем основные рамки, поверх (если есть) — рамки для сравнения
    if boxes:
        _draw_list(boxes, color)
    if compare_boxes:
        _draw_list(compare_boxes, compare_color)

    # Уменьшаем слишком большие фото для удобства просмотра
    if max_width and w > max_width:
        new_h = int(h * (max_width / w))
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, quality=90)

    return img


# --- ПРИМЕР 1: Одиночное фото (по URL или с диска) ---
# boxes = [{"left": 0.25, "top": 0.13, "width": 0.56, "height": 0.6}]
# img = draw_boxes_on_image(
#     "https://inaturalist-open-data.s3.amazonaws.com/photos/169737815/original.jpeg",
#     boxes=boxes,
#     output_path="out/169737815_boxed.jpg"
# )


# --- ПРИМЕР 2: Массовая отрисовка прямо из вашего JSONL ---
def render_from_jsonl(jsonl_path: str, out_dir: str = "rendered_boxes", limit: int = 20):
    """Отрисовывает первые N фото из вашего JSONL-файла (где есть photo_id, image_url и boxes)."""
    os.makedirs(out_dir, exist_ok=True)
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            item = json.loads(line)
            pid = item["photo_id"]
            url = item.get("image_url") or f"assets/{pid}.jpg"
            boxes = item.get("boxes", [])

            out_file = os.path.join(out_dir, f"{pid}_n{len(boxes)}.jpg")
            draw_boxes_on_image(url, boxes=boxes, output_path=out_file)
            print(f"[{i+1}/{limit}] Сохранено: {out_file}")

# render_from_jsonl("pilot_normalized.jsonl", out_dir="pilot_preview", limit=20)