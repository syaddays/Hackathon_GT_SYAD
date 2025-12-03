# 🚀 Auto-Creative Engine  
> **Tagline:** A Generative AI system that converts a brand’s logo + product image into 10+ studio-quality ad creatives with AI-generated captions — automatically packaged into a ready-to-download ZIP.

---

## 1. The Problem (Real World Scenario)

**Context:** In modern marketing teams, designers and content creators spend countless hours creating multiple ad creative variations for A/B testing, seasonal campaigns, and platform-specific formats.

**The Pain Point:** This creative production workflow is slow, repetitive, and expensive.  
If a marketing team wants 10 variations of a product ad, the manual design cycle can consume an entire day.

> **My Solution:** I built **Auto-Creative Engine**, a fully automated system that accepts a brand logo + product image and produces a complete creative package — including high-resolution creatives and AI-generated captions — in a single run.

---

## 2. Expected End Result

**For the User:**

- **Input:** A product image + branded logo  
- **Action:** Run one Python command  
- **Output:** A downloadable ZIP containing:
  - 10+ unique AI-generated ad creatives  
  - Consistent branding with automatic logo placement  
  - Marketing-ready captions (headline, body, CTA, hashtags)  
  - A metadata-rich manifest file (seeds, prompts, tones)

This package is ready for immediate use across Meta, Google, LinkedIn, or display campaigns.

---

## 3. Technical Approach

I wanted to push beyond simple image generation prompts and build a **mini production-grade creative pipeline**, similar in structure to what actual marketing automation tools use.

**System Architecture:**

1. **Asset Ingestion:**  
   Accepts logo (PNG/SVG) and product image (JPG/PNG). Images are normalized to RGBA for clean compositing.

2. **Concept-Based Generation Engine:**  
   Instead of generating random images, I designed **10 Creative Concepts** (e.g., Hero Shot, Lifestyle Café, Minimalist, Duotone Brand Style, Macro Close-Up).  
   Each concept uses:
   - deterministic seeds  
   - custom-crafted prompts  
   - negative prompts to avoid distortions/watermarks  

3. **Generative AI (Image Creation):**  
   - Uses **AI Horde (Stable Diffusion community API)** for text-to-image generation  
   - Automatically handles width/height, model selection, seed consistency  
   - Falls back to a mock generator for offline demos  

4. **AI Caption Generator:**  
   - Calls **Hugging Face Inference API** to generate structured JSON captions  
   - Includes headline, 25-word body, CTA, and hashtags  
   - Produces 3 tone variants per creative (Formal, Witty, Urgent)

5. **Brand Integration (Logo Compositing):**  
   - Logo resized proportionally  
   - Safe margins applied  
   - Consistent placement across all creatives  

6. **Packaging:**  
   - All creatives stored in `/images/`  
   - `manifest.json` contains prompt, seed, tone, and generation metadata  
   - `captions.csv` links captions to corresponding files  
   - Everything bundled into **creatives.zip**

---

## 4. Tech Stack

- **Language:** Python 3.11  
- **Generative Models:** Stable Diffusion (AI Horde API)  
- **Caption LLM:** Hugging Face Inference API  
- **Image Manipulation:** Pillow  
- **Data Packaging:** JSON, CSV, ZIP  
- **Environment:** Local Python execution  

---

## 5. Visual Proof

**Generated Creatives (Examples)**  
_(Displayed during demo)_  

**Caption JSON Samples**  
_(Formal, Witty, Urgent tones)_  

_Images automatically branded with the logo and consistent resolution._

---

## 6. How to Run

```bash
# 1. Clone Repository
git clone https://github.com/username/auto-creative-engine.git

# 2. Navigate
cd auto-creative-engine

# 3. Install Dependencies
pip install pillow requests python-dotenv

# 4. Add API Keys
export HUGGINGFACE_API_TOKEN="your_hf_key"
export STABLEHORDE_API_KEY="optional_horde_key"

# 5. Run the Engine
python auto_creative_engine.py \
    --logo assets/logo.png \
    --product assets/product.jpg \
    --product-desc "Matte Black Travel Mug 12oz" \
    --provider ai_horde \
    --per-concept 1 \
    --out creatives_out
