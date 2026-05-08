# TeslaMate Dashboard

一个只读 TeslaMate 报表界面。它不依赖 TeslaMate 的 Web UI 或 Grafana，只读取 TeslaMate PostgreSQL 中 `public` schema 的行程、充电、位置、状态、升级等数据；Nginx 负责对外入口和 Basic Auth，后端与数据库都不暴露到宿主机端口。

## 架构

```text
浏览器
  |
  | Basic Auth
  v
Nginx / Frontend  -- 内网 HTTP -->  FastAPI Backend  -- Docker 内网 -->  TeslaMate PostgreSQL
```

默认生产部署只发布 `web` 的 `WEB_PORT`。`api` 只在 Docker 内网暴露 `8000`，TeslaMate、Grafana、PostgreSQL 不需要对外开放端口。

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

## 生产部署

### 1. 创建只读数据库用户

在 TeslaMate 的 PostgreSQL 数据库里执行 [deploy/create-readonly-user.sql](deploy/create-readonly-user.sql)，先替换密码：

```sql
create user dashboard_readonly with password 'replace-with-a-strong-password';
grant connect on database teslamate to dashboard_readonly;
grant usage on schema public to dashboard_readonly;
grant select on all tables in schema public to dashboard_readonly;
grant select on all sequences in schema public to dashboard_readonly;
alter default privileges for role teslamate in schema public
  grant select on tables to dashboard_readonly;
alter role dashboard_readonly set default_transaction_read_only = on;
alter role dashboard_readonly set statement_timeout = '15s';
```

不要给 `private` schema 授权。这样后端无法读取 Tesla API token。

### 2. 找到 TeslaMate Docker 网络

在部署机上查看 TeslaMate 所在网络：

```bash
sudo docker network ls | grep -i tesla
```

常见值是 `teslamate_default`。`DATABASE_URL` 里的数据库 host 要使用该网络内 PostgreSQL 服务名，常见是 `database`。

### 3. 配置环境变量

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

TESLAMATE_DOCKER_NETWORK=teslamate_default
DATABASE_URL=postgresql://dashboard_readonly:replace-with-a-strong-password@database:5432/teslamate
```

### 4. 启动

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

只要外层还有反向代理或公网入口，把它转发到 `WEB_PORT` 即可；不需要暴露 TeslaMate、Grafana 或 PostgreSQL。

## GitHub Actions 推送到阿里云镜像仓库

工作流在 [.github/workflows/publish.yml](.github/workflows/publish.yml)。在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 添加：

| Secret | 示例 |
| --- | --- |
| `ALIYUN_REGISTRY` | `registry.cn-shenzhen.aliyuncs.com` |
| `ALIYUN_NAMESPACE` | `your-namespace` |
| `ALIYUN_USERNAME` | 阿里云镜像仓库用户名 |
| `ALIYUN_PASSWORD` | 阿里云镜像仓库密码或访问凭证 |

推送到 `main` 时会构建并推送：

```text
registry.cn-shenzhen.aliyuncs.com/your-namespace/tesla-dashboard-api:<commit-sha>
registry.cn-shenzhen.aliyuncs.com/your-namespace/tesla-dashboard-api:latest
registry.cn-shenzhen.aliyuncs.com/your-namespace/tesla-dashboard-web:<commit-sha>
registry.cn-shenzhen.aliyuncs.com/your-namespace/tesla-dashboard-web:latest
```

推送 `v*` tag 时会额外使用 tag 名作为镜像 tag。

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
