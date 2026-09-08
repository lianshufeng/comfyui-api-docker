# SenseNova U1.5 ComfyUI API Docker 

这是一个最小化 Demo，用一个容器同时运行 ComfyUI 和 Comfyui2api。

## 目录结构

```text
.
├── SenseNova-U1.5-8B-MoT-T8-int8/  # 模型文件，不会复制进镜像
├── docker/                          # 镜像构建所需文件，无需修改
├── docker-compose.yml
└── Dockerfile
```

用户只需准备模型目录并执行启动命令，不需要修改 `docker/`。输入、输出、用户数据库和 API 运行记录保存在容器内部，不会在项目根目录生成额外目录。

## 准备模型

在项目根目录创建 `SenseNova-U1.5-8B-MoT-T8-int8`，并放入以下两个文件：

```text
SenseNova-U1.5-8B-MoT-T8-int8/
├── SenseNova-U1.5-8B-MoT-T8-int8-convrot-tagged.safetensors
└── SenseNova-U1.5-8B-MoT-LoRA-8step-ComfyUI.safetensors
```

Compose 只会把这个目录只读挂载到容器的 `/models`。启动脚本会自动把两个模型映射到 ComfyUI 所需的位置。

## 启动

要求：Docker、Docker Compose、NVIDIA Container Toolkit，以及一张可用的 NVIDIA GPU。

```bash
docker compose up --build
```

如需为 API 设置访问令牌：

```bash
SENSENOVA_API_TOKEN=your-token docker compose up --build
```

Windows PowerShell：

```powershell
$env:SENSENOVA_API_TOKEN = "your-token"
docker compose up --build
```

启动后：

- ComfyUI：<http://127.0.0.1:8188>
- API：<http://127.0.0.1:8460>
- 健康检查：<http://127.0.0.1:8460/health>

停止并删除容器：

```bash
docker compose down
```

容器删除后，容器内的输入、输出和运行记录也会被删除；模型文件不受影响。

## 自动构建

推送到 GitHub 的 `master` 分支后，GitHub Actions 会自动构建并推送：

```text
lianshufeng/comfyui-api-docker:latest
```

需要在 GitHub 仓库中配置 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN` 两个 Actions Secrets。

另一个工作流会把 Git 仓库同步到 CNB，需要配置 `CNB_USERNAME` 和 `CNB_TOKEN`。CNB 收到 `master` 分支后，会根据 `.cnb.yml` 构建并推送 `latest` 和 `amd64` 镜像。
