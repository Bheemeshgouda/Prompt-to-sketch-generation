from diffusers import StableDiffusionPipeline  # NOT StableDiffusionXLPipeline for dreamlike-anime-1.0
import torch
from PIL import Image, ImageOps, ImageFilter
from functools import lru_cache
import os
import time

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Using device: {DEVICE}")

_PIPE = None

@lru_cache(maxsize=1)
def load_model():
    """Loads and caches the Stable Diffusion pipeline for forensic sketch generation."""
    global _PIPE
    if _PIPE is not None:
        return _PIPE

    # Dreamlike anime 1.0 is an SD 1.5 model (not SDXL), so use StableDiffusionPipeline
    model_id = "dreamlike-art/dreamlike-anime-1.0"
    print("[MODEL] Loading Stable Diffusion pipeline ...")
    start = time.time()
    try:
        pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
        )
        if DEVICE == "cuda":
            pipe = pipe.to("cuda")
            pipe.enable_xformers_memory_efficient_attention()
            pipe.enable_attention_slicing()
        else:
            pipe = pipe.to("cpu")
        _PIPE = pipe
        print(f"[MODEL] Model loaded in {time.time() - start:.2f}s")
        return pipe
    except Exception as e:
        print(f"[ERROR] Failed to load SD pipeline: {e}")
        raise

def truncate_prompt(prompt, max_tokens=75):
    """Ensures prompt fits token count limit (approximate; exact limit is 77 tokens for most SD1.5 pipelines)."""
    words = prompt.split()
    if len(words) > max_tokens:
        print(f"[WARN] Prompt too long, truncating to {max_tokens} tokens.")
        return ' '.join(words[:max_tokens])
    return prompt

def convert_to_sketch(image, threshold=185):
    """Convert generated image to clean high-contrast line-drawing."""
    try:
        img = image.convert("L")
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.FIND_EDGES)
        img = ImageOps.invert(img)
        img = img.point(lambda x: 0 if x < threshold else 255)
        img = ImageOps.autocontrast(img)
        return img.convert("RGB")
    except Exception as e:
        print(f"[ERROR] Sketch postprocessing failed: {e}")
        return image

def generate_sketch_image(prompt, output_path, enhance_sketch=True, threshold=185):
    """
    Generate a forensic-style sketch from a text prompt and save it.
    Returns output_path on success; None on failure.
    """
    start = time.time()
    try:
        pipe = load_model()
        # Truncate prompt to avoid tokenizer/indexing errors
        base_prompt = truncate_prompt(prompt, max_tokens=55)
        # Compose a full prompt suitable for line-art
        full_prompt = (
            f"highly detailed police composite sketch, {base_prompt}, "
            "black and white pencil line drawing, front view, clean strong lines, sharp contours, forensic sketch, solid black outlines, no shading, white background"
        )
        # Final safety truncation to prevent over-length
        full_prompt = truncate_prompt(full_prompt, max_tokens=75)

        negative_prompt = (
            "photo, photorealistic, painting, colorful, color, shadow, shading, 3d, blur, cartoon, anime, watermark, logo, text, background"
        )
        print(f"[GEN] Generating from prompt: {full_prompt}")

        result = pipe(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=28,
            guidance_scale=8.0,
            width=512,
            height=512
        )
        image = result.images[0]

        if enhance_sketch:
            image = convert_to_sketch(image, threshold=threshold)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)
        print(f"[GEN] Sketch saved: {output_path} ({time.time() - start:.2f}s)")
        return output_path
    except Exception as e:
        print(f"[ERROR] Sketch generation failed: {e}")
        return None

# Optionally preload for CUDA
if DEVICE == "cuda":
    try:
        load_model()
    except Exception as e:
        print(f"[ERROR] Model preload failed: {e}")
