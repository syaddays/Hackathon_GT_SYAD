"""
auto_creative_engine.py
Auto-Creative Engine (H-003) — Full prototype with AI Horde (StableHorde) + Hugging Face adapters.

What it does:
- Loads a logo (PNG/SVG) and a product image (JPG/PNG).
- For each concept bucket and tone, requests image generations via provider adapter functions (AI Horde or mock).
- Composites the provided logo onto each generated image (Pillow).
- Calls Hugging Face Inference API (or mock) to generate structured captions for each image.
- Produces high-res PNG/JPGs, manifest.json, captions.csv, and packages everything into creatives.zip.

Requirements:
- Python 3.9+
- pip install pillow requests python-dotenv
- Set environment variables for APIs (optional for mock):
    - STABLEHORDE_API_KEY (optional, for AI Horde priority)
    - HUGGINGFACE_API_TOKEN (recommended for HF captioning)
- Run:
    python auto_creative_engine.py --logo assets/logo.png --product assets/product.jpg --product-desc "Matte Black Travel Mug 12oz" --out demo_out --provider ai_horde --per-concept 1 --width 1024 --height 1024

Notes:
- AI Horde (community) availability is variable; keep mock provider for offline demos.
- Hugging Face model cold starts can add latency. Use lighter HF models if needed.
"""

import os
import sys
import json
import argparse
import time
import tempfile
import zipfile
import hashlib
import csv
from pathlib import Path

import requests
from PIL import Image, ImageOps, ImageDraw, ImageFont

# ---------------------------
# Prompt library
# ---------------------------
CONCEPT_PROMPTS = {
    "hero": "Hero shot — clean studio white background; {product}; centered; natural soft shadow; 50mm, shallow DOF; {brand_constraints}; high-detail, photorealistic; no text/watermarks",
    "lifestyle": "Lifestyle — {product} placed on a wooden cafe table near a latte, shallow DOF, warm golden-hour lighting, candid human hand interacting (no faces visible), {brand_constraints}; high-detail, photorealistic; no text/watermarks",
    "flatlay": "Flat-lay — top-down composition, {product} among related accessories, minimal clutter, brand color accents; high-detail, photorealistic; no text/watermarks",
    "closeup": "Close-up — macro shot of {product} texture and logo area, crisp details, soft gradient background; high-detail, photorealistic; no text/watermarks",
    "duotone": "Graphic duotone — {product} silhouette styled with brand palette duotone, high contrast, geometric shapes background; high-detail, photorealistic; no text/watermarks",
    "seasonal": "Seasonal festive — {product} with subtle holiday props (winter - snow-soft bokeh), cozy warm lighting, no religious icons, brand voice warm; high-detail, photorealistic; no text/watermarks",
    "action": "Action shot — {product} in motion (pouring or being grabbed), motion blur artfully used, dynamic angle, realistic; high-detail, photorealistic; no text/watermarks",
    "minimal": "Minimalist — {product} on a large negative-space backdrop with brand color accent, strong composition, subtle shadow, premium feel; high-detail, photorealistic; no text/watermarks",
    "outdoor": "Outdoor — {product} on a hiking trail bench, natural light, rugged props, realistic environmental integration; high-detail, photorealistic; no text/watermarks",
    "mockup": "Ad mockup — {product} with top-left reserved space for text, safe margins, high-contrast area for CTA overlay (do NOT render text in image); high-detail, photorealistic; no text/watermarks",
}
NEGATIVE_PROMPT = "watermark, lowres, text, extra fingers, logo of other brands, nsfw, noisy, oversaturated"

# ---------------------------
# Helpers
# ---------------------------
def deterministic_seed(*args):
    h = hashlib.sha256("||".join(map(str, args)).encode()).hexdigest()
    return int(h[:8], 16)

def safe_mkdir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

# ---------------------------
# Mock image generator (fast offline)
# ---------------------------
def generate_image_via_mock(prompt, seed, width=1024, height=1024):
    """Create a placeholder image with prompt text for offline testing."""
    img = Image.new("RGBA", (width, height), (245, 245, 245, 255))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    text = f"MOCK IMAGE\nseed:{seed}\n{prompt[:200]}"
    d.text((30, 30), text, fill=(30,30,30), font=font)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

# ---------------------------
# AI Horde (StableHorde) adapter
# Docs: community-run; availability varies.
# Set STABLEHORDE_API_KEY env var for better priority (optional).
# ---------------------------
AI_HORDE_BASE = "https://stablehorde.net/api"
AI_HORDE_KEY = os.environ.get("STABLEHORDE_API_KEY", None)

def generate_image_via_ai_horde(prompt, seed, width=1024, height=1024, timeout=180):
    """
    Submit an async job to StableHorde and poll for completion.
    Returns local PNG path.
    """
    headers = {"Content-Type": "application/json"}
    if AI_HORDE_KEY:
        headers["apikey"] = AI_HORDE_KEY
    else:
        headers["apikey"] = "0000000000"  # Anonymous key

    payload = {
        "prompt": prompt,
        "params": {
            "width": width,
            "height": height,
            "seed": str(int(seed) % (2**31 - 1)),
            "n": 1,
            "steps": 30,
            "sampler_name": "k_euler"
        },
        "nsfw": False,
        "trusted_workers": False,
        "slow_workers": True,
        "censor_nsfw": False,
        "workers": [],
        "worker_blacklist": False,
        "models": ["stable_diffusion"],
        "r2": True,
        "shared": False,
        "replacement_filter": True
    }
    try:
        r = requests.post(f"{AI_HORDE_BASE}/v2/generate/async", json=payload, headers=headers, timeout=30)
        if r.status_code not in [200, 202]:
            error_detail = r.text
            raise RuntimeError(f"AI Horde submit failed: {r.status_code} - {error_detail}")
        resp = r.json()
    except Exception as e:
        raise RuntimeError(f"AI Horde submit failed: {e}")

    job_id = resp.get("id") or resp.get("request_id") or resp.get("generation_id")
    if not job_id:
        raise RuntimeError(f"AI Horde returned no job id: {resp}")

    started = time.time()
    while True:
        try:
            q = requests.get(f"{AI_HORDE_BASE}/v2/generate/check/{job_id}", headers=headers, timeout=30)
            q.raise_for_status()
            status = q.json()
        except Exception as e:
            # transient; continue polling
            time.sleep(2)
            if time.time() - started > timeout:
                raise TimeoutError("AI Horde polling timed out")
            continue

        # status formatting varies; check common keys
        if status.get("done") or status.get("finished") or status.get("status") == "finished":
            # Need to fetch the actual result with a different endpoint
            try:
                result_req = requests.get(f"{AI_HORDE_BASE}/v2/generate/status/{job_id}", headers=headers, timeout=30)
                result_req.raise_for_status()
                result = result_req.json()
                
                # try to extract base64 image or URL
                gens = result.get("generations") or result.get("images") or []
                if isinstance(gens, list) and gens:
                    first = gens[0]
                    if isinstance(first, dict):
                        # Check for image URL first
                        img_url = first.get("img")
                        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
                            try:
                                rr = requests.get(img_url, timeout=30)
                                if rr.status_code == 200:
                                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                                    tmp.write(rr.content); tmp.close()
                                    return tmp.name
                            except Exception:
                                pass
                        
                        # Check for base64
                        b64_img = first.get("img") or first.get("b64") or first.get("base64")
                        if b64_img and not b64_img.startswith("http"):
                            import base64
                            data = base64.b64decode(b64_img)
                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            tmp.write(data); tmp.close()
                            return tmp.name
                
                raise RuntimeError("AI Horde finished but no image data found: " + str(result))
            except Exception as e:
                raise RuntimeError(f"Failed to fetch result: {e}")

        if time.time() - started > timeout:
            raise TimeoutError("AI Horde generation timeout")
        time.sleep(2)

# ---------------------------
# Hugging Face caption adapter
# ---------------------------
HF_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", None)
# default HF model (choose smaller one if latency matters)
HF_MODEL = os.environ.get("HF_MODEL", "google/flan-t5-small")  # small by default for speed

def generate_caption_via_hf(product_name, concept, tone):
    """
    Calls Hugging Face Inference API to request a JSON caption.
    Fallbacks to mock generator if no HF token or parsing fails.
    """
    if not HF_API_TOKEN:
        return generate_caption_via_mock(product_name, concept, tone)

    prompt = (
        "You are a concise marketing copywriter.\n"
        f"product_name: {product_name}\nconcept: {concept}\ntone: {tone}\n\n"
        "Output ONLY a JSON object with fields: headline (<=8 words), body (<=25 words), cta (1-3 words), hashtags (array of 3-6 strings).\n"
    )
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Accept": "application/json"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 80, "temperature": 0.7}, "options": {"wait_for_model": True}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
    except Exception:
        return generate_caption_via_mock(product_name, concept, tone)
    if r.status_code == 503:
        # model loading
        return generate_caption_via_mock(product_name, concept, tone)
    if not r.ok:
        return generate_caption_via_mock(product_name, concept, tone)
    out = r.json()
    text = ""
    if isinstance(out, dict) and out.get("error"):
        return generate_caption_via_mock(product_name, concept, tone)
    # HF sometimes returns list(s) with 'generated_text' keys
    if isinstance(out, list) and len(out) and isinstance(out[0], dict) and out[0].get("generated_text"):
        text = out[0]["generated_text"]
    elif isinstance(out, dict) and out.get("generated_text"):
        text = out["generated_text"]
    elif isinstance(out, str):
        text = out
    else:
        # fallback to raw string
        text = json.dumps(out)

    # best-effort extract JSON payload from model text
    try:
        jstart = text.find("{")
        if jstart != -1:
            j = json.loads(text[jstart:])
        else:
            j = json.loads(text)
        return {
            "headline": j.get("headline") or j.get("title") or "",
            "body": j.get("body") or "",
            "cta": j.get("cta") or "Shop now",
            "hashtags": j.get("hashtags") or []
        }
    except Exception:
        return generate_caption_via_mock(product_name, concept, tone)

# ---------------------------
# Mock caption generator
# ---------------------------
def generate_caption_via_mock(product_desc, concept, tone):
    HEAD = {
        "formal": "Premium performance, reliable every day.",
        "witty": "Sip smarter, not harder.",
        "urgent": "Limited stock — grab yours now!"
    }
    BODY = {
        "formal": f"The {product_desc} combines refined design with lasting durability — perfect for daily use.",
        "witty": f"This {product_desc} keeps your drink hot and your hands happy. Fancy that!",
        "urgent": f"Hurry — {product_desc} selling fast. Take it before it's gone."
    }
    CTA = {"formal": "Shop now", "witty": "Get it", "urgent": "Buy now"}
    hashtags = ["#design", "#everyday", "#musthave"]
    return {
        "headline": HEAD.get(tone, HEAD["formal"]),
        "body": BODY.get(tone, BODY["formal"]),
        "cta": CTA.get(tone, CTA["formal"]),
        "hashtags": hashtags
    }

# ---------------------------
# Image compositing helper
# ---------------------------
def composite_logo(base_image_path, logo_path, dest_path, placement="bottom_right", logo_scale=0.12, margin=40):
    base = Image.open(base_image_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    bw, bh = base.size
    new_logo_w = int(bw * logo_scale)
    lw, lh = logo.size
    ratio = new_logo_w / lw if lw > 0 else 1.0
    new_logo_h = int(lh * ratio)
    if new_logo_w <= 0 or new_logo_h <= 0:
        logo = logo
    else:
        logo = logo.resize((new_logo_w, new_logo_h), Image.LANCZOS)

    if placement == "bottom_right":
        x = bw - new_logo_w - margin
        y = bh - new_logo_h - margin
    elif placement == "bottom_left":
        x = margin
        y = bh - new_logo_h - margin
    elif placement == "top_left":
        x = margin
        y = margin
    else:
        x = int((bw - new_logo_w)/2)
        y = int((bh - new_logo_h)/2)

    out = Image.new("RGBA", base.size)
    out.paste(base, (0,0))
    out.alpha_composite(logo, dest=(x, y))
    out = out.convert("RGB")
    out.save(dest_path, quality=95)
    return dest_path

# ---------------------------
# Map providers
# ---------------------------
IMAGE_PROVIDER_MAP = {
    "mock": generate_image_via_mock,
    "ai_horde": generate_image_via_ai_horde
}

# ---------------------------
# Main pipeline
# ---------------------------
def run_pipeline(logo_path, product_desc, product_image_path, out_dir, provider="mock", per_concept=1, width=1024, height=1024):
    start_time = time.time()
    out_dir = Path(out_dir)
    if out_dir.exists():
        out_dir = out_dir.with_name(out_dir.name + "_" + str(int(time.time())))
    safe_mkdir(out_dir)
    images_dir = out_dir / "images"
    safe_mkdir(images_dir)

    manifest = {
        "created_at": time.time(),
        "product_desc": product_desc,
        "provider": provider,
        "width": width,
        "height": height,
        "items": []
    }

    brand_constraints = "include brand colors, no extra logos"
    provider_fn = IMAGE_PROVIDER_MAP.get(provider, generate_image_via_mock)

    # iterate over concept prompts
    for concept_name, prompt_template in CONCEPT_PROMPTS.items():
        for i in range(per_concept):
            seed = deterministic_seed(product_desc, concept_name, i)
            prompt = prompt_template.format(product=product_desc, brand_constraints=brand_constraints)
            # attach negative prompt
            full_prompt = prompt + " NEGATIVE_PROMPT: " + NEGATIVE_PROMPT
            print(f"[generate] concept={concept_name} seed={seed} prompt_snippet={full_prompt[:120]}")

            try:
                gen_image_path = provider_fn(full_prompt, seed, width=width, height=height)
            except Exception as e:
                print(f"[warn] generation failed for {concept_name} (seed {seed}): {e}; falling back to mock")
                gen_image_path = generate_image_via_mock(full_prompt, seed, width=width, height=height)

            # compose logo onto generated image
            out_image_name = f"{concept_name}_v{i}_s{seed}.jpg"
            out_image_path = images_dir / out_image_name
            try:
                composite_logo(gen_image_path, logo_path, str(out_image_path))
            except Exception as e:
                # if compositing fails, copy gen image to output as fallback
                print(f"[warn] compositing failed: {e}; copying generated image")
                Path(gen_image_path).replace(out_image_path)

            # generate captions for tones
            for tone in ["formal", "witty", "urgent"]:
                caption = generate_caption_via_hf(product_desc, concept_name, tone)
                item = {
                    "filename": out_image_name,
                    "concept": concept_name,
                    "seed": seed,
                    "provider_used": provider,
                    "tone": tone,
                    "caption": caption,
                    "prompt": full_prompt
                }
                manifest["items"].append(item)

    # write manifest.json and captions.csv
    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    csv_path = out_dir / "captions.csv"
    with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename","concept","seed","tone","headline","body","cta","hashtags"])
        for it in manifest["items"]:
            caps = it["caption"]
            writer.writerow([
                it["filename"],
                it["concept"],
                it["seed"],
                it["tone"],
                caps.get("headline",""),
                caps.get("body",""),
                caps.get("cta",""),
                " ".join(caps.get("hashtags", []))
            ])

    # zip outputs
    zip_path = out_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for img in images_dir.iterdir():
            z.write(img, arcname=f"images/{img.name}")
        z.write(manifest_path, arcname="manifest.json")
        z.write(csv_path, arcname="captions.csv")

    elapsed = time.time() - start_time
    print(f"[done] packaged creatives at: {zip_path} (elapsed {elapsed:.1f}s)")
    return zip_path

# ---------------------------
# CLI
# ---------------------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--logo", required=True, help="path to logo (png/svg)")
    p.add_argument("--product", required=True, help="product image path (for description fallback)")
    p.add_argument("--product-desc", default=None, help="product description (overrides auto)")
    p.add_argument("--out", default="out_creatives", help="output directory")
    p.add_argument("--provider", default="mock", choices=list(IMAGE_PROVIDER_MAP.keys()), help="image provider: mock|ai_horde")
    p.add_argument("--per-concept", type=int, default=1, help="images per concept")
    p.add_argument("--width", type=int, default=1024, help="image width (px)")
    p.add_argument("--height", type=int, default=1024, help="image height (px)")
    return p.parse_args()

def main():
    args = parse_args()
    logo = Path(args.logo)
    if not logo.exists():
        print("ERROR: logo not found:", args.logo)
        sys.exit(1)
    product_img = Path(args.product)
    if not product_img.exists():
        print("ERROR: product image not found:", args.product)
        sys.exit(1)
    desc = args.product_desc if args.product_desc else product_img.stem.replace("_", " ")
    zipfile_path = run_pipeline(str(logo), desc, str(product_img), args.out, provider=args.provider, per_concept=args.per_concept, width=args.width, height=args.height)
    print("Done. ZIP:", zipfile_path)

if __name__ == "__main__":
    main()

