# 文件服务

实现：`CottonOGD/server/files/service.py`（业务）、`CottonOGD/api/files/views.py`
（v1 信封）、`CottonOGD/api/files/static_views.py`（非信封字节流）、
`CottonOGD/common/files.py`（X-Accel / 流式 / Range）。

## 1. 存储布局

```text
$FILE_STORAGE_ROOT/                  # 环境变量；不可写时回退 <repo>/temp/files（本机为 /data/web/CottonOGD/OGD/temp/files）
├── public/<stored_name>             # is_public=True，owner 为空
└── <user_id>/<relative_path>/<stored_name>
```

- `FileRecord.relative_path`：**纯目录路径，带尾斜杠**；根目录为 `''`。
- `FileRecord.stored_name`：随机 hex，磁盘名与展示名解耦；重命名/移动不改磁盘名。
- `FileRecord.filename`：用户可见文件名（单段，禁止 `/`、`\`、`..`）。
- 上传写入按 1 MiB 分块（`CHUNK_SIZE`），不会把大文件读入内存。
- 所有路径先经 `common/paths.py::validate_relative_path`
  （拒绝绝对路径、`.`/`..`、空组件、非法字符）与 `safe_join`。

`FILE_STORAGE_ROOT` 必须与 nginx snippet 中的
`/internal-files/` alias 保持一致，否则生产下载会 404。

## 2. 端点语义

### 公开文件

```http
GET /CottonOGD_api/api/v1/files/public/tree/?path=软件/
```

```json
{
  "code": 0, "message": "ok",
  "data": {
    "path": "软件/",
    "dirs": ["linux"],
    "files": [{
      "id": "uuid", "filename": "tool.zip", "size": 1024,
      "content_type": "application/zip", "created_at": "2026-11-20T10:00:00",
      "download_url": "/CottonOGD_api/api/v1/files/public/<uuid>/download/"
    }]
  }
}
```

- 只列出 `is_public=True`；子目录由更深层记录聚合，`dirs` 为直接子目录名。
- `path` 非法（绝对路径、`..`）→ `40002`。
- 下载：`GET files/public/<uuid>/download/`；UUID 不存在或磁盘文件缺失
  → `40401`。

### 个人文件（必须登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `files/my/tree/?path=` | 仅当前用户记录；结构与公开树一致 |
| POST | `files/my/upload/` | multipart：`file`、`path`、`replace` |
| DELETE | `files/my/<uuid>/` | 删除记录 + 物理文件，返回 `{deleted:true,id}` |
| POST | `files/my/<uuid>/move/` | JSON `{new_path,new_name}` |

上传规则：

- `path` 为空表示根目录；上传到 `软件/linux/` 会创建对应 owner 子目录。
- **同名冲突按 (owner, filename) 判定**，不区分目录；冲突 `40901`。
- `replace=true`（或 `1`/`yes`）时覆盖同名文件：复用原 `stored_name` 与原
  物理目录，记录更新为新的 `relative_path`/大小/类型。
- 非本人文件一律 `40401`（不泄露存在性）。

移动规则：

- `new_name` 必须通过单段文件名校验；`new_path` 通过目录校验，非法 `40002`。
- 目标目录若不存在会自动创建。
- 目标位置存在同名记录（排除自身）→ `40901`。
- 源物理文件缺失 → `40401`。

### 基因组数据下载

```http
GET /CottonOGD_api/api/v1/files/genome/<genome_id>/<file_type>/
```

| `file_type` | 文件后缀 |
|---|---|
| `genome` | `.genome.fa.gz` |
| `gene` | `.gene_genome.fa.gz` |
| `cds` | `.cds.fa.gz` |
| `protein` | `.pro.fa.gz` |
| `upstream2000` | `.upstream.fa.gz` |
| `gff3` | `.gff.gz` |

源目录固定为 `backend/data/genome/<genome_id>/<genome_id><suffix>`。
`file_type` 不在白名单 → `40002`；`genome_id` 穿越 → `40002`；文件缺失 → `40401`。

旧别名 `GET /download_genome/<genome_id>/<file_type>` 仍可用，行为完全相同。

## 3. 传输：X-Accel / 流式

`common/files.py` 根据 `settings.USE_X_ACCEL` 分流：

| 模式 | 条件 | 行为 |
|---|---|---|
| X-Accel | `USE_X_ACCEL=True`（默认 `not DEBUG`） | 返回空响应 + `X-Accel-Redirect`，由 nginx `internal` location 发字节 |
| 流式 | `USE_X_ACCEL=False`（开发/测试） | Django `FileResponse`，支持单段 `Range` / `206` / `Content-Range` |

v1 下载端点发出的内部 URI：

| 端点 | `X-Accel-Redirect` |
|---|---|
| 公开/个人文件 | `/internal-files/<relative>`，`<relative>` 为相对 `FILE_STORAGE_ROOT` 的路径 |
| 基因组下载 | `/internal-genome/<genome_id>/<filename>` |

响应同时带 `Content-Disposition`（RFC 5987，支持中文文件名）与 `Content-Length`。
nginx 配置见 [../../scripts/nginx_api_v1.snippet](../../scripts/nginx_api_v1.snippet)
与 [../nginx.md](../nginx.md)。

## 4. 非信封文件端点

| 路径 | 内容 | Range |
|---|---|---|
| `/jbrowse/large/<genome>/<file>` | JBrowse 大文件（BAM/CRAM/VCF.GZ/GFF.GZ/BigWig/BEDDB/索引/FA） | 单段 |
| `/static/jbrowse/data/<genome>/<file>` | 同上 | 单段 |
| `/synteny/<source>_to_<target>/work/<file>` | `.anchors`、`.anchors.new`、`.anchors.simple`、`.bed`、`.bed.gz`、`.gff`、`.gff.gz`、`synteny.json` | 否 |
| `/CottonOGD_api/tf_tree/tree/genome/<genome>/{TF,TR}/<name>.treefile` | Newick 文本 | 否 |
| `orthofinder/og/<og>/{sequences,msa,tree}/` | FASTA/Newick（v1 路径但非信封） | 由 `stream_file` 支持 |

安全规则：

- 路径段含 `..`、绝对路径、跨目录 → `400`。
- synteny 文件名只允许单段且扩展名在白名单内；pair 名必须含 `_to_`。
- 生产建议由 nginx 直出，Django 仅作开发回退与 nginx 漏配兜底。

## 5. 部署检查清单

1. `.env` 设置 `FILE_STORAGE_ROOT`（生产示例 `/data/files`），确保 nginx
   worker 用户可读。若该目录不可写/不存在，运行时会回退到
   `<repo>/temp/files`（本机 `/data/web/CottonOGD/OGD/temp/files`），此时
   nginx 的 `/internal-files/` alias 必须指向**回退后的实际目录**。
2. 将 `scripts/nginx_api_v1.snippet` 合入站点 server 块（`/internal-files/`
   的 alias 指向同一 `FILE_STORAGE_ROOT`）。
3. `nginx -t && systemctl reload nginx`。
4. `USE_X_ACCEL` 不显式设置时：`DEBUG=False` 自动开启；显式设 `0` 可强制
   由 Django 流式返回（不推荐用于 1.1TB 基因组）。
5. 用 `curl -sI` 验证下载返回 `X-Accel-Redirect`，且直接请求
   `/internal-files/...` 应从外网 404（`internal` 生效）。
6. 公开文件变更后刷新缓存/前端列表；公开区没有独立上传 API，需由管理端
   入库（`is_public=True`, `owner=None`）并落盘到 `public/`。