# 🚀 Auto-Creative Engine (H-003)  
> **Tagline:** A Generative AI system that transforms a brand’s logo + product image into 10+ high-quality ad creatives with AI-generated captions.

---

## 1. The Problem
Brands spend a lot of time designing multiple versions of the same marketing creative.  
Every variation — background style, lighting, layout, caption, aspect ratio — is created manually.

This slows down:
- campaign launches  
- A/B testing  
- creative experimentation  

**Goal:** Automate this entire workflow using Generative AI.

---

## 2. The Vision

The **Auto-Creative Engine** will generate a complete creative package from just two inputs:

### **Input**
- A brand logo  
- A product image  

### **Intended Output**
A downloadable ZIP containing:
- 10+ AI-generated ad creatives  
- Consistent branding (logo placed automatically)
- AI-generated captions (headline + body + CTA + hashtags)
- manifest.json (prompts, seeds, metadata)

This gives marketers instant, ready-to-use ad assets.

---

## 3. Planned Technical Approach  
(This is an early-stage outline — implementation in progress.)

### **Image Generation**
Use a free or open API such as:
- **AI Horde (StableHorde)** for Stable Diffusion image generation  
- Deterministic seeds for reproducibility  
- Concept-based prompts (e.g., hero shot, lifestyle, flat-lay, minimalist)

### **Logo Integration**
- Resize and composite the logo onto generated images  
- Maintain brand consistency with safe margins and proportional scaling  

### **Caption Generation**
Use free LLM endpoints (e.g., HuggingFace models) to generate:
- Headline  
- Body  
- Call-To-Action  
- Hashtags  

### **Output Packaging**
Create:
- `/images/` directory  
- `manifest.json`  
- `captions.csv`  
- Final `creatives.zip`  

---

## 4. Status
This project is currently **under development**.  
- Prompt templates are being drafted  
- Image generator adapter is being integrated  
- Caption generator and output packaging are being set up  

A working prototype will follow soon.

---

## 5. Tech Stack (Planned)
- **Python 3.11**  
- **Stable Diffusion (AI Horde API)**  
- **HuggingFace Text Generation**  
- **Pillow** for image manipulation  
- **JSON / CSV** for metadata  
- **ZIP packaging** for final output  

---

    --out creatives_out
