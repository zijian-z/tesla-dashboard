# TeslaMate Dashboard

一个完整编排的 TeslaMate 采集 + 只读报表界面。TeslaMate 只负责采集车辆数据；报表由本项目的 FastAPI 后端和移动端优先的前端提供。Nginx 是唯一对外入口，负责 Basic Auth，API、TeslaMate、PostgreSQL、MQTT 都不直接暴露到宿主机公网端口。

## 架构

```text
浏览器
  |
  | Basic Auth
  v
Nginx / Frontend  -- 内网 HTTP -->  FastAPI Backend  -- Docker 内网 -->  PostgreSQL
       |
       └── 可选代理 /teslamate/ 到内网 TeslaMate 初始化页面

TeslaMate Collector  -- 内网 --> PostgreSQL + MQTT
```

默认生产部署只发布 `web` 的 `WEB_PORT`。`api` 只在 Docker 内网暴露 `8000`，TeslaMate 只在 Docker 内网暴露 `4000`，PostgreSQL 和 MQTT 也都只在内网可见。`database` 镜像内置首次启动恢复备份脚本，`db-init` 服务会自动创建只读数据库账号，不需要手工执行 SQL，也不需要在部署目录额外复制脚本文件。

## 功能

- 当前车辆状态、电量、额定续航、里程表、温度、胎压、软件版本
- 周期行程统计：里程、时长、最高速度、估算能耗
- 周期充电统计：充电次数、电量、费用、SOC 增量、进行中的充电
- 日趋势、月汇总、电量/续航趋势、在线/睡眠/离线状态占比
- 最近行程、最近充电、常到地点、充电地点
- 移动端优先的单页界面

## 本地用当前备份验证

当前目录里的 `teslamate.bck` 是 PostgreSQL 18 plain SQL dump，可以直接用本地 compose 恢复测试库：

```bash
docker compose version
```

如果提示 `unknown command: docker compose` 或 `unknown shorthand flag: 'f' in -f`，说明没有安装 Docker Compose v2 插件。在 Ubuntu 24.04 上安装：

```bash
sudo apt-get update
sudo apt-get install -y docker-compose-v2
```

```bash
sudo docker compose -f compose.local.yaml up --build
```

访问：

```text
http://localhost:8080
用户名：admin
密码：change-me-local
```

首次启动会导入 `teslamate.bck`，需要等待 PostgreSQL 初始化完成。重新导入时先删除本地 volume：

```bash
sudo docker compose -f compose.local.yaml down -v
sudo docker compose -f compose.local.yaml up --build
```

如果你曾用旧版 `compose.local.yaml` 启动并看到 PostgreSQL 18 的 `/var/lib/postgresql/data (unused mount/volume)` 报错，先停止旧容器：

```bash
sudo docker compose -f compose.local.yaml down
```

旧的失败 volume 名通常是 `tesla-dashboard-local_pgdata`。新版配置使用 `pgdata18`，不会再复用旧卷；确认不需要旧测试卷后可清理：

```bash
sudo docker volume rm tesla-dashboard-local_pgdata
```

## 生产部署

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```dotenv
IMAGE_REGISTRY=registry.cn-shenzhen.aliyuncs.com
IMAGE_NAMESPACE=your-namespace
IMAGE_TAG=latest

WEB_PORT=8080
BASIC_AUTH_USER=admin
BASIC_AUTH_PASSWORD=change-this-password

MOSQUITTO_TAG=2
TESLAMATE_TAG=latest
TM_ENCRYPTION_KEY=replace-with-a-long-random-encryption-key
TM_DB_USER=teslamate
TM_DB_PASS=replace-with-a-strong-database-password
TM_DB_NAME=teslamate
TZ=Asia/Shanghai

DASHBOARD_DB_USER=dashboard_readonly
DASHBOARD_DB_PASSWORD=replace-with-a-different-strong-password
```

建议用下面的命令生成强随机值：

```bash
openssl rand -base64 48
```

`TM_ENCRYPTION_KEY` 是 TeslaMate 加密密钥，生产环境创建后要妥善保管。`DASHBOARD_DB_USER` 会由 `db-init` 自动创建为只读账号；它只获得 `public` schema 的读权限，不会获得 `private` schema 权限。

大陆机器部署前，先在 GitHub Actions 手工运行一次 `Build and Push Images`，把本项目镜像和运行依赖镜像都推送到阿里云镜像仓库。生产 `compose.yaml` 默认会从 `${IMAGE_REGISTRY}/${IMAGE_NAMESPACE}` 拉取所有镜像，不再直接依赖 Docker Hub。

生产部署目录最少只需要这些文件：

- `compose.yaml`
- `.env`
- 可选的 TeslaMate 数据库备份文件，例如 `teslamate.bck`

恢复备份和创建只读账号的脚本已经打进 `tesla-dashboard-postgres` 镜像，不需要额外复制 `deploy/` 目录。

### 2. 启动

先确认部署机有 Docker Compose v2：

```bash
docker compose version
```

Ubuntu 24.04 如果缺失 Compose v2：

```bash
sudo apt-get update
sudo apt-get install -y docker-compose-v2
```

```bash
sudo docker compose pull
sudo docker compose up -d
```

之后访问：

```text
http://部署机IP:8080
```

第一次启动后，先用同一个入口访问 `http://部署机IP:8080/teslamate/` 完成 TeslaMate 授权初始化；之后日常使用 `http://部署机IP:8080/` 查看本项目的报表界面。TeslaMate 没有发布独立宿主机端口，`/teslamate/` 也受同一组 Basic Auth 保护。

只要外层还有反向代理或公网入口，把它转发到 `WEB_PORT` 即可；不需要额外暴露 TeslaMate、PostgreSQL 或 MQTT。

### 3. 直接导入同级目录备份

如果 `compose.yaml` 同级目录里存在数据库备份文件，`database` 服务在第一次创建新的 PostgreSQL 卷时会自动导入。支持的文件名优先级包括：

- `teslamate.bck`
- `teslamate.sql`
- `teslamate.dump`
- `teslamate.backup`
- 以及这些后缀的 `.gz` 版本

如果目录里有多个备份文件，脚本会按名称优先级取第一个匹配项。这个导入只在数据库卷首次初始化时执行一次；后续镜像更新、容器重启不会再次导入，也不会覆盖已有数据。若要重新导入，需要先删除对应的 PostgreSQL volume。

如果备份里包含旧的 TeslaMate token，并且 `TM_ENCRYPTION_KEY` 也保持一致，那么恢复后通常可以直接继续使用，不需要重新额外配置授权 token。

完整重建并重新导入备份：

```bash
sudo docker compose down -v --remove-orphans
sudo docker compose pull
sudo docker compose up -d database
sudo docker compose logs -f database
sudo docker compose up -d
```

`down -v` 会删除 PostgreSQL 持久化 volume。只有在确认同级目录里的备份文件可用时才执行这条命令。

## GitHub Actions 推送到阿里云镜像仓库

工作流在 [.github/workflows/publish.yml](.github/workflows/publish.yml)。在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 添加：

| Secret | 示例 |
| --- | --- |
| `ALIYUN_REGISTRY` | `registry.cn-shenzhen.aliyuncs.com` |
| `ALIYUN_NAME_SPACE` | `your-namespace` |
| `ALIYUN_REGISTRY_USER` | 阿里云镜像仓库用户名 |
| `ALIYUN_REGISTRY_PASSWORD` | 阿里云镜像仓库密码或访问凭证 |

这个 workflow 只支持手工触发。到 GitHub Actions 页面选择 `Build and Push Images`，点击 `Run workflow`，填写镜像 tag，默认是 `latest`。

```text
registry.cn-shenzhen.aliyuncs.com/your-namespace/tesla-dashboard-api:<image_tag>
registry.cn-shenzhen.aliyuncs.com/your-namespace/tesla-dashboard-web:<image_tag>
registry.cn-shenzhen.aliyuncs.com/your-namespace/tesla-dashboard-postgres:<image_tag>
registry.cn-shenzhen.aliyuncs.com/your-namespace/postgres:18-trixie
registry.cn-shenzhen.aliyuncs.com/your-namespace/eclipse-mosquitto:2
registry.cn-shenzhen.aliyuncs.com/your-namespace/teslamate:latest
```

## 直接开发

后端：

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://teslamate:teslamate@localhost:5432/teslamate uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器会把 `/api` 代理到 `http://localhost:8000`。
