"""LSB (Least Significant Bit) steganografi.

Veri formatı (bit düzeyinde):
    [4 byte uzunluk (big-endian)] [veri] [32 byte SHA-256 checksum]

Her bit, görüntü piksellerinin renk kanallarının en düşük bitine yazılır.
"""

import hashlib
import os
import struct

from PIL import Image, ImageDraw, ImageFont


class SteganographyManager:
    """PNG görüntüsüne veri gizleme / çıkarma (LSB yöntemi)."""

    @staticmethod
    def create_carrier_image(path: str, width: int = 1024, height: int = 1024) -> None:
        """Güzel gradyanlı ve kilit ikonlu taşıyıcı PNG görüntüsü oluşturur.

        Görsel GitHub'da paylaşılabilecek kalitede üretilir.
        LSB steganografi yine sorunsuz çalışır.
        """
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # Çok küçük görsellerde (< 64px) sadece gradyan uygula, detay çizme
        min_side = min(width, height)
        simple_mode = min_side < 64

        # --- Çapraz gradyan arka plan (koyu lacivert → mor → mavi) ---
        for y in range(height):
            for x in range(width):
                # Çapraz mesafe (0..1)
                t = ((x / width) + (y / height)) / 2.0
                r = int(30 * (1 - t) + 40 * t)
                g = int(30 * (1 - t) + 60 * t)
                b = int(60 * (1 - t) + 180 * t)
                img.putpixel((x, y), (r, g, b))

        if simple_mode:
            img.save(path, "PNG")
            return

        cx, cy = width // 2, height // 2
        scale = min(width, height) / 1024.0

        # --- Dekoratif dış halka ---
        ring_r = int(220 * scale)
        ring_w = int(6 * scale)
        draw.ellipse(
            [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
            outline=(100, 140, 255, 40), width=ring_w,
        )

        # --- Kalkan gövdesi ---
        shield_w = int(160 * scale)
        shield_h = int(190 * scale)
        sx, sy = cx - shield_w, cy - int(70 * scale)

        # Kalkan üst yuvarlak kısım
        draw.rounded_rectangle(
            [sx, sy, sx + shield_w * 2, sy + shield_h],
            radius=int(30 * scale),
            fill=(25, 50, 120),
            outline=(89, 180, 250),
            width=int(4 * scale),
        )

        # --- Kilit gövdesi ---
        lock_w = int(80 * scale)
        lock_h = int(70 * scale)
        lx = cx - lock_w // 2
        ly = cy - int(10 * scale)

        draw.rounded_rectangle(
            [lx, ly, lx + lock_w, ly + lock_h],
            radius=int(12 * scale),
            fill=(89, 180, 250),
        )

        # Kilit halkası (arc)
        arc_w = int(50 * scale)
        arc_h = int(50 * scale)
        arc_x = cx - arc_w // 2
        arc_y = ly - arc_h + int(8 * scale)
        draw.arc(
            [arc_x, arc_y, arc_x + arc_w, arc_y + arc_h],
            start=180, end=0,
            fill=(89, 180, 250),
            width=int(10 * scale),
        )

        # Anahtar deliği
        hole_r = int(10 * scale)
        draw.ellipse(
            [cx - hole_r, ly + int(18 * scale),
             cx + hole_r, ly + int(18 * scale) + hole_r * 2],
            fill=(25, 50, 120),
        )
        # Anahtar deliği alt çizgi
        line_w = int(4 * scale)
        draw.rectangle(
            [cx - line_w // 2, ly + int(35 * scale),
             cx + line_w // 2, ly + int(52 * scale)],
            fill=(25, 50, 120),
        )

        # --- "SecureVault" yazısı ---
        text = "SecureVault"
        font_size = int(48 * scale)
        try:
            font = ImageFont.truetype("segoeui.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        text_x = cx - tw // 2
        text_y = cy + int(130 * scale)
        # Gölge
        draw.text((text_x + 2, text_y + 2), text, fill=(0, 0, 0), font=font)
        # Ana metin
        draw.text((text_x, text_y), text, fill=(200, 220, 255), font=font)

        # --- Alt yazı ---
        sub_text = "Encrypted Password Manager"
        sub_size = int(20 * scale)
        try:
            sub_font = ImageFont.truetype("segoeui.ttf", sub_size)
        except (OSError, IOError):
            try:
                sub_font = ImageFont.truetype("arial.ttf", sub_size)
            except (OSError, IOError):
                sub_font = ImageFont.load_default()

        sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
        stw = sub_bbox[2] - sub_bbox[0]
        draw.text(
            (cx - stw // 2, text_y + int(55 * scale)),
            sub_text, fill=(130, 160, 220), font=sub_font,
        )

        import random
        rng = random.SystemRandom()
        for _ in range(80):
            px = rng.randint(0, width - 1)
            py = rng.randint(0, height - 1)
            brightness = rng.randint(150, 255)
            dot_r = rng.randint(1, max(1, int(3 * scale)))
            draw.ellipse(
                [px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                fill=(brightness, brightness, brightness),
            )

        img.save(path, "PNG")

    @staticmethod
    def get_capacity(image_path: str) -> int:
        """Görüntünün saklayabileceği maksimum bayt sayısını döndürür."""
        with Image.open(image_path) as img:
            w, h = img.size
        total_bits = w * h * 3   # her kanal 1 bit
        overhead = 4 + 32        # uzunluk + checksum
        return (total_bits // 8) - overhead

    @staticmethod
    def encode(image_path: str, data: bytes) -> None:
        """Veriyi görüntüye LSB yöntemiyle gömer."""
        with Image.open(image_path) as src:
            rgb = src.convert("RGB")
            size = rgb.size
            raw = bytearray(rgb.tobytes())

        checksum = hashlib.sha256(data).digest()
        payload = struct.pack(">I", len(data)) + data + checksum

        max_bytes = len(raw) // 8
        if len(payload) > max_bytes:
            raise ValueError(
                f"Veri çok büyük ({len(payload)} bayt). "
                f"Görüntü kapasitesi: {max_bytes} bayt."
            )

        bit_idx = 0
        for byte_val in payload:
            for shift in range(7, -1, -1):
                raw[bit_idx] = (raw[bit_idx] & 0xFE) | ((byte_val >> shift) & 1)
                bit_idx += 1

        new_img = Image.frombytes("RGB", size, bytes(raw))
        new_img.save(image_path, "PNG")
        new_img.close()

    @staticmethod
    def decode(image_path: str) -> bytes:
        """Görüntüden LSB yöntemiyle veri çıkarır ve bütünlüğünü doğrular."""
        with Image.open(image_path) as src:
            rgb = src.convert("RGB")
            raw = rgb.tobytes()

        def _read_bytes(start_bit: int, count: int) -> tuple[bytes, int]:
            result = bytearray(count)
            idx = start_bit
            for i in range(count):
                val = 0
                for _ in range(8):
                    val = (val << 1) | (raw[idx] & 1)
                    idx += 1
                result[i] = val
            return bytes(result), idx

        # Uzunluk (4 bayt)
        length_bytes, next_bit = _read_bytes(0, 4)
        length = struct.unpack(">I", length_bytes)[0]

        max_data = (len(raw) // 8) - 4 - 32
        if length > max_data:
            raise ValueError("Geçersiz veri uzunluğu; görüntü bozulmuş olabilir.")

        # Veri
        data, next_bit = _read_bytes(next_bit, length)

        # Checksum (32 bayt SHA-256)
        stored_checksum, _ = _read_bytes(next_bit, 32)
        calculated_checksum = hashlib.sha256(data).digest()
        if stored_checksum != calculated_checksum:
            raise ValueError("Veri bütünlüğü doğrulaması başarısız; veri bozulmuş.")

        return data
