# Qwen2VL-OCR

**Author:** aroky amatthew

A local Gradio web app that extracts text from images in any language using the Qwen2-VL vision-language model, with built-in keyword search.

## Features

- **OCR:** Extracts text in any language from uploaded images using Qwen2-VL-2B-Instruct.
- **Keyword Search:** Search for keywords within the extracted text.
- **GPU Accelerated:** Automatically uses your NVIDIA GPU (float16) for fast inference; falls back to CPU if unavailable.

## Setup

### Prerequisites

- Python 3.10+
- NVIDIA GPU with CUDA drivers (recommended)
- Git

### Installation

1. **Create & activate a virtual environment:**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install PyTorch (GPU):**

   ```powershell
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

   > For CPU-only, use `https://download.pytorch.org/whl/cpu` instead.

3. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

4. **Log in to Hugging Face (for model download):**

   ```powershell
   huggingface-cli login
   ```

### Running

```powershell
python app.py
```

Open `http://127.0.0.1:7860` in your browser. Upload an image, optionally enter a keyword, and hit Submit.

## Notes

- First launch downloads ~4 GB of model weights.
- GPU inference takes a few seconds per image; CPU takes 30–120+ seconds.
