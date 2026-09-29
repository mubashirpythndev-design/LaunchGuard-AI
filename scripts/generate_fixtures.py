"""Generate synthetic fixture images for LaunchGuard AI testing and demo scenarios."""
import os
from pathlib import Path
import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
API_FIXTURES = REPO_ROOT / "apps" / "api" / "tests" / "fixtures" / "images"
WEB_DEMO = REPO_ROOT / "apps" / "web" / "public" / "demo"

W, H = 800, 600

def create_base_scene() -> np.ndarray:
    """Create a realistic pad background with sky, pad surface, and gantry."""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    # Sky gradient (top dark steel blue to horizon light gray-blue)
    for y in range(400):
        alpha = y / 400.0
        b = int(140 + 40 * alpha)
        g = int(120 + 35 * alpha)
        r = int(100 + 30 * alpha)
        img[y, :] = (b, g, r)
    # Ground/concrete pad (y 400 to 600)
    for y in range(400, H):
        val = int(80 + (y - 400) * 0.15)
        img[y, :] = (val, val, val)
    # Launch mount / pad stand
    cv2.rectangle(img, (330, 420), (470, 460), (50, 50, 50), -1)
    cv2.rectangle(img, (310, 450), (490, 470), (40, 40, 40), -1)
    return img

def draw_rocket_body(img: np.ndarray) -> None:
    """Draw rocket fuselage and nose cone."""
    # Fuselage: cylinder from y=180 to y=430, x=370 to 430 (width 60)
    cv2.rectangle(img, (370, 180), (430, 430), (220, 220, 225), -1)
    cv2.rectangle(img, (370, 180), (430, 430), (160, 160, 165), 2)
    # Nose cone: triangle from (400, 100) down to (370, 180) and (430, 180)
    nose = np.array([[400, 90], [370, 180], [430, 180]], np.int32)
    cv2.fillPoly(img, [nose], (200, 50, 40))
    cv2.polylines(img, [nose], True, (150, 30, 20), 2)
    # Body roll markings
    cv2.rectangle(img, (370, 260), (400, 280), (30, 30, 30), -1)
    cv2.rectangle(img, (400, 280), (430, 300), (30, 30, 30), -1)

def draw_fins(img: np.ndarray, left_angle_deg: float = 45.0, right_angle_deg: float = 45.0) -> None:
    """Draw left and right fins with specified deviation from body."""
    # Left fin rooted at (370, 370) to (370, 430)
    # Right fin rooted at (430, 370) to (430, 430)
    # Left fin tip
    rad_l = np.radians(left_angle_deg)
    len_fin = 65
    tip_lx = int(370 - len_fin * np.sin(rad_l))
    tip_ly = int(430 - len_fin * np.cos(rad_l) + 20)
    left_fin = np.array([[370, 370], [tip_lx, tip_ly], [370, 430]], np.int32)
    cv2.fillPoly(img, [left_fin], (180, 40, 30))
    cv2.polylines(img, [left_fin], True, (130, 20, 10), 2)

    # Right fin tip
    rad_r = np.radians(right_angle_deg)
    tip_rx = int(430 + len_fin * np.sin(rad_r))
    tip_ry = int(430 - len_fin * np.cos(rad_r) + 20)
    right_fin = np.array([[430, 370], [tip_rx, tip_ry], [430, 430]], np.int32)
    cv2.fillPoly(img, [right_fin], (180, 40, 30))
    cv2.polylines(img, [right_fin], True, (130, 20, 10), 2)

def draw_person(img: np.ndarray, x: int, y: int) -> None:
    """Draw a human figure at (x, y) coordinates."""
    # Head
    cv2.circle(img, (x, y - 55), 8, (190, 160, 140), -1)
    # Torso (yellow safety jacket)
    cv2.rectangle(img, (x - 8, y - 46), (x + 8, y - 20), (30, 190, 220), -1)
    # Legs (dark pants)
    cv2.line(img, (x - 4, y - 20), (x - 6, y), (50, 40, 40), 4)
    cv2.line(img, (x + 4, y - 20), (x + 6, y), (50, 40, 40), 4)
    # Arms
    cv2.line(img, (x - 8, y - 42), (x - 12, y - 25), (30, 190, 220), 3)
    cv2.line(img, (x + 8, y - 42), (x + 12, y - 25), (30, 190, 220), 3)

def generate_fixtures() -> None:
    API_FIXTURES.mkdir(parents=True, exist_ok=True)
    WEB_DEMO.mkdir(parents=True, exist_ok=True)

    # 1. Normal (GO)
    img_normal = create_base_scene()
    draw_rocket_body(img_normal)
    draw_fins(img_normal, left_angle_deg=45.0, right_angle_deg=45.0)

    # 2. Misaligned Fin (HOLD) - Fin angle deviation 7.2 deg
    img_fin = create_base_scene()
    draw_rocket_body(img_fin)
    draw_fins(img_fin, left_angle_deg=41.0, right_angle_deg=48.2)

    # 3. Person in Zone (NO-GO) - Person at launchpad base
    img_person = create_base_scene()
    draw_rocket_body(img_person)
    draw_fins(img_person, left_angle_deg=45.0, right_angle_deg=45.0)
    draw_person(img_person, 350, 450)

    scenarios = {
        "normal.jpg": img_normal,
        "fin_misaligned.jpg": img_fin,
        "person_in_zone.jpg": img_person,
    }

    for name, img in scenarios.items():
        web_path = WEB_DEMO / name
        api_path = API_FIXTURES / name
        cv2.imwrite(str(web_path), img)
        cv2.imwrite(str(api_path), img)
        print(f"Generated {name} -> {web_path} and {api_path}")

    # Create check_id pass/fail copies per R14
    pairs = [
        ("body.cracks__pass.jpg", img_normal),
        ("body.cracks__fail.jpg", img_fin),
        ("fin.alignment__pass.jpg", img_normal),
        ("fin.alignment__fail.jpg", img_fin),
        ("zone.occupancy__pass.jpg", img_normal),
        ("zone.occupancy__fail.jpg", img_person),
        ("cue.smoke__pass.jpg", img_normal),
        ("cue.fire__pass.jpg", img_normal),
    ]
    for name, img in pairs:
        cv2.imwrite(str(API_FIXTURES / name), img)

    # Document provenance in SOURCES.md
    sources_content = """# Fixture Images Provenance

These test images are synthetically generated for LaunchGuard AI to provide reproducible, zero-external-dependency test fixtures and demo scenarios.

| File | Scenario | Purpose | Expected Verdict |
|---|---|---|---|
| `normal.jpg` | Normal flight vehicle | Symmetrical fins, clear pad | **GO** |
| `fin_misaligned.jpg` | Asymmetrical fin mount | 7.2 deg fin deviation (>6 deg crit / >3 deg warn) | **HOLD** |
| `person_in_zone.jpg` | Pad safety breach | Technician detected within danger exclusion zone | **NO-GO** |

Generated programmatically by `scripts/generate_fixtures.py`.
"""
    with open(API_FIXTURES / "SOURCES.md", "w", encoding="utf-8") as f:
        f.write(sources_content)
    print("Fixture generation complete.")

if __name__ == "__main__":
    generate_fixtures()
