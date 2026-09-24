# SenseNova U1.5 ComfyUI API Docker 

这是一个最小化 Demo，用一个容器同时运行 ComfyUI 和 Comfyui2api。

## 目录结构

```text
.
├── models/                         # 可选的本地模型目录，不会复制进镜像
├── docker/                          # 镜像构建所需文件，无需修改
├── docker-compose.yml
└── Dockerfile
```

用户只需准备 `models/` 并执行启动命令，不需要修改 `docker/`。模型保存在 `models/`；输入、输出、用户数据库和 API 运行记录仍保存在容器内部。

## 准备模型

将 SenseNova INT8 主模型和官方 8 步 LoRA 放在同一目录，然后将该目录只读挂载到容器的 `/models`。本机 Compose 示例使用 `../../huggingface/Comfy-Org/SenseNova-U1.5-8B-MoT-T8`：

```text
SenseNova-U1.5-8B-MoT-T8/
├── SenseNova-U1.5-8B-MoT-T8-int8-convrot-tagged.safetensors
└── SenseNova-U1.5-8B-MoT-LoRA-8step-ComfyUI.safetensors
```

`sensenova` Compose 服务通过 `--model SenseNova-U1.5-8B-MoT-T8-int8-convrot-tagged` 选择主模型。镜像会从 `/models` 加载该模型并注册同名文生图模型及带 `-edit` 后缀的图生图模型；无需挂载工作流目录。检测到官方 8 步 LoRA 时，会自动使用 8 步、CFG 1 的工作流；只有主模型时使用 50 步、CFG 4。SenseNova 默认尺寸为 2048×2048；在 RTX 3060 12GB 上实测 8 步出图约 192 秒，1024×1024 及更低分辨率的测试图出现异常纹理。

### Qwen-Image-2.1 INT8

Qwen-Image-2.1 INT8 可以只挂载一个模型包目录到 `/models`，无需另行挂载 API 工作流。目录中需包含以下三个文件（可以放在子目录中）：

```text
qwen_image_2.1_int8_convrot.safetensors
qwen3vl_8b_int8_convrot.safetensors
qwen_image_2.1_vae_bf16.safetensors
```

启动命令显式指定主模型名称，镜像会在挂载目录中查找三个文件并为 API 注册同名模型；无需挂载或打包 `qwen_t2i.json`：

```bash
docker run --gpus all -p 8460:8460 -v /path/to/Qwen-Image-2.1:/models:ro \
  docker.cnb.cool/vvllm/comfyui-api:latest \
  --model qwen_image_2.1_int8_convrot
```

调用 OpenAI 兼容接口时，`model` 填 `qwen_image_2.1_int8_convrot`。在 AIHub 中可将三个文件打成一个模型包，由平台挂载到 `/models`，并将启动命令设为 `--model qwen_image_2.1_int8_convrot`；镜像也兼容旧模板传入的 `/usr/local/bin/start-unified.sh`。模型权重在首次出图时由 ComfyUI 加载。当前自动 API 注册支持该 Qwen 模型；其他模型架构需要对应的加载与出图规则。

## 启动

要求：Docker、Docker Compose、NVIDIA Container Toolkit，以及一张可用的 NVIDIA GPU。

两种模型共用一张 GPU 时，每次只启动其中一个：

```bash
docker compose --profile sensenova up -d
# 或
docker compose --profile qwen up -d
```

如需为 API 设置访问令牌：

```bash
SENSENOVA_API_TOKEN=your-token docker compose --profile sensenova up -d
```

Windows PowerShell：

```powershell
$env:SENSENOVA_API_TOKEN = "your-token"
docker compose --profile sensenova up -d
```

启动后：

- SenseNova ComfyUI / API：<http://127.0.0.1:8188> / <http://127.0.0.1:8460>
- Qwen ComfyUI / API：<http://127.0.0.1:8189> / <http://127.0.0.1:8461>

停止并删除容器：

```bash
docker compose --profile sensenova down
# 或
docker compose --profile qwen down
```

容器删除后，容器内的输入、输出和运行记录也会被删除；模型文件不受影响。

## 自动构建

推送到 GitHub 的 `master` 分支后，GitHub Actions 会自动构建并推送：

```text
lianshufeng/comfyui-api-docker:latest
```

需要在 GitHub 仓库中配置 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN` 两个 Actions Secrets。

另一个工作流会把 Git 仓库同步到 CNB，需要配置 `CNB_USERNAME` 和 `CNB_TOKEN`。CNB 收到 `master` 分支后，会根据 `.cnb.yml` 构建并推送 `latest` 和 `amd64` 镜像。
