# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

tgState V2 is a Python FastAPI application that uses Telegram as a file storage backend. It provides a web UI for uploading/managing files and an image hosting service, with files stored in a Telegram channel.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Run production server (Docker)
docker build -t tgstate .
docker run -p 8000:8000 --env-file .env tgstate
```

## Architecture

### Core Components

- `app/main.py` - FastAPI app entry point, middleware for auth, mounts static files and routers
- `app/api/routes.py` - REST API endpoints for upload, download, file management, SSE updates
- `app/pages.py` - HTML page routes (index, settings, image hosting, password)
- `app/services/telegram_service.py` - Telegram Bot API wrapper for upload/download/delete
- `app/services/telegram_listener.py` - Telethon-based listener for group file detection
- `app/bot_handler.py` - python-telegram-bot handlers for file detection and "get" command replies
- `app/events.py` - Global asyncio.Queue for SSE event bus
- `app/database.py` - SQLite storage for file metadata (thread-safe with locks)
- `app/core/config.py` - Pydantic settings from `.env` file
- `app/core/http_client.py` - Shared httpx async client with lifespan management

### Key Patterns

**Composite File IDs**: Files are tracked using `message_id:file_id` format to enable deletion via Telegram API.

**Large File Handling**: Files ≥19.5MB are chunked and uploaded as multiple documents with a manifest file (`tgstate-blob\n{filename}\n{chunk_ids...}`). The manifest is used to reassemble during download.

**Dual Auth System**:
- `PASS_WORD` - Web UI login (cookie-based)
- `PICGO_API_KEY` - API access (header or form field)
- Auth logic varies based on which passwords are set (see `routes.py:17-85`)

**SSE Updates**: Real-time file list updates via `/api/file-updates` endpoint using `asyncio.Queue` in `app/events.py`.

**Bot "get" Command**: Users can reply "get" to any file message in the group to receive a download link.

## Environment Variables

Required:
- `BOT_TOKEN` - Telegram Bot API token
- `CHANNEL_NAME` - Target channel (@username)
- `API_ID`, `API_HASH` - Telethon credentials

Optional:
- `PASS_WORD` - Web UI password
- `PICGO_API_KEY` - API upload key
- `BASE_URL` - Public URL for generated links (default: http://127.0.0.1:8000)

## Recent Changes (Session Progress)

### Bug Fixes
1. **Description 同步问题** - 修复主页编辑 description 后图床页面不显示的问题 (`app/pages.py:65`)
2. **上传实时更新** - 修复上传完成后主页表格不实时更新的问题，添加 SSE 通知 (`app/api/routes.py:110-121`)

### New Features
1. **浏览器缓存** - 为 `/preview/{file_id}` 路由添加 `Cache-Control: public, max-age=31536000` 响应头，图片缓存 1 年 (`app/api/routes.py:171`)
2. **图床分页** - 图床页面支持分页显示，每页 20 张图片 (`app/pages.py:49-84`, `app/templates/image_hosting.html:112-130`, `app/static/css/style.css:1342-1388`)
3. **模态框优化** - 点击图片放大后适应页面大小显示 (`app/static/css/style.css:1004-1011`)

### Modified Files
| 文件 | 修改内容 |
|------|----------|
| `app/api/routes.py` | 上传后 SSE 通知、preview 缓存头 |
| `app/pages.py` | 图床分页逻辑、description 字段 |
| `app/templates/image_hosting.html` | 分页控件 |
| `app/static/css/style.css` | 分页样式、模态框适应页面 |
