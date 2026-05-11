# TeslaMate Dashboard

一个完整编排的 TeslaMate 采集栈和只读报表界面。默认只把 `web` 服务发布到宿主机 `80` 端口：

- `http://服务器/`：TeslaMate，用于授权和原生管理界面
- `http://服务器/dashboard/`：本项目的 dashboard

API、PostgreSQL、MQTT 和 TeslaMate 容器端口都只在 Docker 网络内使用。对外入口统一由内置 Nginx 提供 Basic Auth、静态页面和内部转发，避免在宿主机上额外暴露多个服务端口。

## 功能

- 当前车辆状态、电量、续航、里程、位置、温度、胎压、软件版本
- 默认 7 天数据，支持 30 天、90 天、一年、全部和自定义日期范围
- 概览、趋势、行程、充电、效率、电池、地点、车辆信息报表
- 概览页展示今日分时电量消耗，并按车辆休眠/未休眠状态预测今日剩余电量消耗
- 行程统计：里程、时长、最高车速、平均速度、能耗、海拔累计、路线排行
- 充电统计：电量、费用、SOC 增量、功率、AC/DC 月汇总、快充次数、充电地点
- 电池和车辆观测：电量/续航趋势、状态占比、温度、胎压
- 只读访问 TeslaMate 数据库，不写入业务表

Dashboard 会根据最新充电采样判断实时充电状态，避免从“充电中”备份恢复后把历史未闭合充电会话误判为当前仍在充电。

充电报表默认过滤小于 `0.5 kWh` 且 SOC 没有增加的微小会话，避免 TeslaMate 的极小补电记录把趋势误显示为每天充电。实时充电状态仍会单独展示。

## 架构

```text
Browser
  |
  v
web / Nginx :80
  |-- /dashboard/      -> dashboard frontend
  |-- /dashboard/api/  -> FastAPI api:8000
  `-- /               -> TeslaMate teslamate:4000

TeslaMate -> PostgreSQL + MQTT
FastAPI   -> PostgreSQL read-only role
```

`database` 镜像内置备份恢复脚本。首次创建数据库 volume 时，如果部署目录里有 TeslaMate 备份，会自动导入，并清空备份中的旧 TeslaMate token，方便新实例重新授权。

## 本地验证

当前目录存在 `teslamate.bck` 时，可以直接用本地 compose 恢复并验证：

```bash
sudo docker compose -f compose.local.yaml up --build
```

访问：

```text
http://localhost/dashboard/
用户名：admin
密码：change-me-local
```

本地重新导入备份：

```bash
sudo docker compose -f compose.local.yaml down -v
sudo docker compose -f compose.local.yaml up --build
```

如果宿主机 `80` 端口已被占用，可以临时修改 `compose.local.yaml` 的 `web.ports`，例如改为 `"8080:80"` 后访问 `http://localhost:8080/dashboard/`。

## 生产部署

### 1. 准备 `.env`

```bash
cp .env.example .env
```

至少需要确认这些值：

```dotenv
IMAGE_REGISTRY=registry.cn-shenzhen.aliyuncs.com
IMAGE_NAMESPACE=your-namespace
IMAGE_TAG=latest

WEB_PORT=80
BASIC_AUTH_USER=admin
BASIC_AUTH_PASSWORD=change-this-password

TM_ENCRYPTION_KEY=replace-with-a-long-random-encryption-key
TM_DB_PASS=replace-with-a-strong-database-password
DASHBOARD_DB_PASSWORD=replace-with-a-different-strong-password
TZ=Asia/Shanghai
```

建议生成强随机密钥和密码：

```bash
openssl rand -base64 48
```

`TM_ENCRYPTION_KEY` 是 TeslaMate 的加密密钥，生产环境创建后要妥善保存。`DASHBOARD_DB_USER` 默认是 `dashboard_readonly`，由 `db-init` 自动创建，只授予 `public` schema 的读取权限。

### 2. 启动

```bash
sudo docker compose pull
sudo docker compose up -d
```

首次启动后：

1. 打开 `http://服务器/` 完成 TeslaMate 授权。
2. 打开 `http://服务器/dashboard/` 查看 dashboard。

`WEB_PORT` 默认是 `80`。如果机器前面还有负载均衡或网关，建议让它直接转发到宿主机 `80`，不要额外发布 TeslaMate、API、PostgreSQL 或 MQTT 端口。

### 3. 只更新 dashboard

如果改动只涉及后端 API 或前端页面，不需要重建数据库、TeslaMate 或 MQTT。生产环境拉取新镜像后只重启 `api` 和 `web`：

```bash
sudo docker compose pull api web
sudo docker compose up -d --no-deps api web
```

本地源码验证时同样可以只重建这两个服务：

```bash
sudo docker compose -f compose.local.yaml up -d --build --no-deps api web
```

只有修改了 `database` 镜像、恢复脚本、TeslaMate、MQTT 或需要重新导入备份时，才需要处理对应服务或数据库 volume。

行程地图默认使用适合国内网络的瓦片源。需要替换地图源时，可以在构建前设置 `VITE_MAP_TILE_URL`、`VITE_MAP_TILE_SUBDOMAINS` 和 `VITE_MAP_COORDINATE_SYSTEM` 后重建 `web` 镜像。

## 导入备份

把备份文件放在 `compose.yaml` 同级目录，数据库 volume 首次创建时会自动导入。优先识别这些文件名：

- `teslamate.bck`
- `teslamate.sql`
- `teslamate.dump`
- `teslamate.backup`
- 上述后缀的 `.gz` 版本

导入只在新的 PostgreSQL volume 初始化时执行一次。需要重新导入时：

```bash
sudo docker compose down -v --remove-orphans
sudo docker compose pull
sudo docker compose up -d
```

`down -v` 会删除数据库持久化 volume。执行前确认备份文件可用。

## 镜像推送

大陆机器部署前，建议先用 GitHub Actions 把本项目镜像和运行依赖推送到阿里云镜像仓库。工作流文件：

```text
.github/workflows/publish.yml
```

需要在 GitHub `Settings -> Secrets and variables -> Actions` 配置：

| Secret | 用途 |
| --- | --- |
| `ALIYUN_REGISTRY` | 阿里云镜像仓库地址 |
| `ALIYUN_NAME_SPACE` | 命名空间 |
| `ALIYUN_REGISTRY_USER` | 仓库用户名 |
| `ALIYUN_REGISTRY_PASSWORD` | 仓库密码或访问凭证 |

手工运行 `Build and Push Images`，填写镜像 tag。`.env` 中的 `IMAGE_TAG` 要和推送的 tag 一致。

## 开发

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
