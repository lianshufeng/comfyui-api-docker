"""Register a selected mounted model with ComfyUI's OpenAI-compatible API."""

import argparse
import json
import os
from pathlib import Path


COMFYUI_ROOT = Path(os.environ.get("COMFYUI_ROOT", "/opt/ComfyUI"))
WORKFLOWS_DIR = Path(os.environ.get("WORKFLOWS_DIR", "/root/comfyui-api-workflows"))
QWEN_MODEL = "qwen_image_2.1_int8_convrot"
SENSENOVA_MODEL = "SenseNova-U1.5-8B-MoT-T8-int8-convrot-tagged"
SENSENOVA_LORA = "SenseNova-U1.5-8B-MoT-LoRA-8step-ComfyUI.safetensors"
QWEN_COMPANIONS = {
    "clip": ("qwen3vl_8b_int8_convrot.safetensors", "text_encoders"),
    "vae": ("qwen_image_2.1_vae_bf16.safetensors", "vae"),
}


def find_file(root: Path, name: str) -> Path:
    matches = sorted(path for path in root.rglob(name) if path.is_file())
    if not matches:
        raise ValueError(f"Required model file not found in {root}: {name}")
    if len(matches) != 1:
        raise ValueError(f"Multiple copies of {name} found in {root}")
    return matches[0]


def link_model(source: Path, category: str) -> None:
    destination = COMFYUI_ROOT / "models" / category / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        if not destination.is_symlink():
            raise ValueError(f"Refusing to replace existing model file: {destination}")
        destination.unlink()
    destination.symlink_to(source)


def qwen_workflow(model_name: str) -> dict:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": model_name + ".safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN_COMPANIONS["clip"][0], "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN_COMPANIONS["vae"][0]}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["2", 0], "prompt": "", "negative_prompt": "", "vae": ["3", 0], "resolution": 1024}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1], "latent_image": ["5", 0], "seed": 42, "steps": 40, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": model_name}},
    }


def qwen_parameter_spec() -> dict:
    return {
        "version": 1,
        "kind": "txt2img",
        "prompt_node": "4.prompt",
        "negative_prompt_node": "4.negative_prompt",
        "parameters": {
            "size": {"type": "size", "default": "1024x1024", "maps": [{"ref": "5.width", "part": "width"}, {"ref": "5.height", "part": "height"}]},
            "steps": {"type": "int", "default": 40, "maps": [{"ref": "6.steps"}]},
            "seed": {"type": "int", "default": 42, "maps": [{"ref": "6.seed"}]},
            "cfg": {"type": "float", "default": 1.0, "maps": [{"ref": "6.cfg"}]},
        },
    }


def sensenova_workflow(model_name: str, *, edit: bool, use_lora: bool) -> dict:
    model_path = f"SenseNovaU1.5/{model_name}.safetensors"
    workflow = {
        "1": {"class_type": "SenseNovaU15Loader", "inputs": {"model_name": model_path}},
        "2": {"class_type": "SenseNovaSamplingOptions", "inputs": {"model": ["11", 0] if use_lora else ["1", 0], "shift": 3.0}},
    }
    if use_lora:
        workflow["11"] = {"class_type": "SenseNovaU15EightStepLoRA", "inputs": {"model": ["1", 0], "lora_name": SENSENOVA_LORA, "strength_model": 0.85}}
    steps, cfg = (8, 1.0) if use_lora else (50, 4.0)
    if edit:
        workflow.update({
            "3": {"class_type": "LoadImage", "inputs": {"image": "example.png"}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": ""}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": ""}},
            "6": {"class_type": "SenseNovaReferenceImage", "inputs": {"positive": ["4", 0], "negative": ["5", 0], "Image-1": ["3", 0]}},
            "7": {"class_type": "EmptySenseNovaLatentImage", "inputs": {"width": 2048, "height": 2048, "batch_size": 1}},
            "8": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["6", 0], "negative": ["6", 1], "latent_image": ["7", 0], "seed": 42, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
            "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["1", 2]}},
            "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": model_name + "-edit"}},
        })
    else:
        workflow.update({
            "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": ""}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": ""}},
            "5": {"class_type": "EmptySenseNovaLatentImage", "inputs": {"width": 2048, "height": 2048, "batch_size": 1}},
            "6": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0], "seed": 42, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
            "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
            "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": model_name}},
        })
    return workflow


def sensenova_parameter_spec(*, edit: bool, use_lora: bool) -> dict:
    prompt_node, negative_node, image_node, latent_node, sampler_node = ("4", "5", "3", "7", "8") if edit else ("3", "4", None, "5", "6")
    spec = {
        "version": 1,
        "kind": "img2img" if edit else "txt2img",
        "prompt_node": f"{prompt_node}.text",
        "negative_prompt_node": f"{negative_node}.text",
        "parameters": {
            "size": {"type": "size", "default": "2048x2048", "maps": [{"ref": f"{latent_node}.width", "part": "width"}, {"ref": f"{latent_node}.height", "part": "height"}]},
            "steps": {"type": "int", "default": 8 if use_lora else 50, "maps": [{"ref": f"{sampler_node}.steps"}]},
            "seed": {"type": "int", "default": 42, "maps": [{"ref": f"{sampler_node}.seed"}]},
            "cfg": {"type": "float", "default": 1.0 if use_lora else 4.0, "maps": [{"ref": f"{sampler_node}.cfg"}]},
        },
    }
    if image_node:
        spec["image_node"] = f"{image_node}.image"
    return spec


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a mounted ComfyUI model")
    parser.add_argument("--model", help="Main model filename without .safetensors")
    parser.add_argument("--model-dir", default=os.environ.get("AIHUB_MODEL_DIR", "/models"))
    args = parser.parse_args()
    if not args.model:
        return  # Preserve externally supplied workflows when no model is selected.

    model_name = Path(args.model).name.removesuffix(".safetensors")
    if model_name not in {QWEN_MODEL, SENSENOVA_MODEL}:
        raise ValueError(f"No automatic API recipe for model: {model_name}")
    model_root = Path(args.model_dir)
    if not model_root.is_dir():
        raise ValueError(f"Model directory does not exist: {model_root}")
    main_file = find_file(model_root, model_name + ".safetensors")
    if model_name == QWEN_MODEL:
        companions = {key: find_file(model_root, filename) for key, (filename, _) in QWEN_COMPANIONS.items()}
        link_model(main_file, "diffusion_models")
        for key, source in companions.items():
            link_model(source, QWEN_COMPANIONS[key][1])
        write_json(WORKFLOWS_DIR / f"{model_name}.json", qwen_workflow(model_name))
        write_json(WORKFLOWS_DIR / ".comfyui2api" / f"{model_name}.params.json", qwen_parameter_spec())
    else:
        destination = COMFYUI_ROOT / "models" / "diffusion_models" / "SenseNovaU1.5" / main_file.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            destination.unlink()
        elif destination.exists():
            raise ValueError(f"Refusing to replace existing model file: {destination}")
        destination.symlink_to(main_file)
        lora_files = sorted(path for path in model_root.rglob(SENSENOVA_LORA) if path.is_file())
        if len(lora_files) > 1:
            raise ValueError(f"Multiple copies of {SENSENOVA_LORA} found in {model_root}")
        use_lora = bool(lora_files)
        if use_lora:
            link_model(lora_files[0], "loras")
        for edit in (False, True):
            api_name = model_name + ("-edit" if edit else "")
            write_json(WORKFLOWS_DIR / f"{api_name}.json", sensenova_workflow(model_name, edit=edit, use_lora=use_lora))
            write_json(WORKFLOWS_DIR / ".comfyui2api" / f"{api_name}.params.json", sensenova_parameter_spec(edit=edit, use_lora=use_lora))
    print(f"Prepared model {model_name} from {model_root}; OpenAI model id: {model_name}", flush=True)


if __name__ == "__main__":
    main()
