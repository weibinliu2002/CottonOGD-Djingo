# CottonOGD API v1

后端所有业务接口统一挂在 `/CottonOGD_api/api/v1/`。本目录是**唯一契约来源**：
代码改动后先更新这里，再同步前端与部署。

| 文档 | 内容 |
|---|---|
| [endpoints.md](endpoints.md) | 全量端点：方法、认证、参数、非信封端点 |
| [migration-map.md](migration-map.md) | 旧路径 → v1 路径、字段/认证变化、已删除端点 |
| [auth.md](auth.md) | 认证模型、JWT / 匿名会话 / 第三方登录 |
| [files.md](files.md) | 文件树、上传下载、X-Accel、nginx 分流 |
| [errors.md](errors.md) | 错误码、HTTP 映射、响应示例 |
| [openapi.yaml](openapi.yaml) | `manage.py spectacular` 生成的机器可读契约 |

在线查看（需后端运行）：

- Swagger UI：`/CottonOGD_api/api/v1/docs/`
- OpenAPI 3：`/CottonOGD_api/api/v1/schema/`

## 1. 统一信封

**所有 v1 JSON 接口**（`CottonOGD/api/**`）都返回同一外层结构：

```json
{ "code": 0, "message": "ok", "data": { } }
```

- 成功：`code = 0`，HTTP 200（创建类端点也可能 201）。
- 失败：`code` 为非零整数业务码，`data` 为 `null` 或补充信息（如可用选项列表）。
- HTTP 状态码 = `code // 100`（`40001 → 400`，`40401 → 404`，`50401 → 504`）。
- 错误码清单见 [errors.md](errors.md)。

分页端点使用：

```json
{
  "code": 0, "message": "ok",
  "data": {
    "items": [],
    "pagination": {"total": 0, "limit": 20, "offset": 0, "has_more": false}
  }
}
```

部分分析端点直接用业务字段承载结果（如 `count`、`rows`、`pairs`），
以 [endpoints.md](endpoints.md) 与在线 OpenAPI 为准；**外层信封不变**。

> 非信封端点：二进制/文本文件（JBrowse、Synteny work 文件、基因组下载、
> OrthoFinder FASTA、TF 树、OAuth 回调跳转）直接返回字节流或重定向。

## 2. URL 命名规范

1. 结构：`/CottonOGD_api/api/v1/<domain>/<resource>[/<action>]/`。
2. 全部小写 kebab-case；禁止下划线拼接（旧 `go_annotation` 型不再出现）。
3. 集合资源用复数（`pairs/`、`orthogroups/`），单目标资源用单数。
4. action 只使用受控词表：`search, detail, summary, annotation, enrichment,
   extract, convert, map, design, distribution, statistics, density, tree,
   pairs, regenerate, download, upload, move, chat`。
5. 同一 action 跨域同义：`detail` 永远是详情，`enrichment` 永远是富集。
6. GET = 读取；POST = 复杂查询/分析。参数等价的端点同时接受 GET/POST
   （服务端从 query string 或 body 读取同名参数）。

## 3. 认证

| 范围 | 认证 |
|---|---|
| 业务数据域（meta/search/genes/…/conversion） | 公开，匿名可访问 |
| `files/my/*`、`auth/me`、`auth/password/*`、`auth/methods`、`auth/bind-*` | 必须已登录（JWT 或会话） |
| `ai/chat/` | 必须持有匿名/登录会话 |
| `files/public/*`、`files/genome/*`、`primer/design`、`blast/search` | 公开 |
| `auth/register|login|refresh|…` | 公开；会忽略无效 Bearer |

认证方式、Token 生命周期与第三方登录见 [auth.md](auth.md)。

```http
Authorization: Bearer <access>
```

匿名会话创建后也会写入 `auth_token` HttpOnly Cookie，AI 对话可直接复用。

## 4. 版本与兼容

- 旧路径（`/CottonOGD_api/<view>/`、`/api/*`）**已删除，不再双挂载**。
  未命中的 GET 会落到 SPA `index.html`（200），POST 返回 405；这不是接口。
- 前端迁移对照见 [migration-map.md](migration-map.md)。
- 破坏性变更必须升级 `/v2/`；v1 内只做向后兼容的字段新增。

## 5. 重新生成 OpenAPI

```bash
cd /data/web/CottonOGD/OGD/backend
source venv/bin/activate
python manage.py spectacular --file docs/api/openapi.yaml --validate
```

`SPECTACULAR_SETTINGS` 位于 `mysite/settings.py`；端点描述取自视图 docstring。
新增/修改端点时同步更新 `endpoints.md`，并重新生成 `openapi.yaml`。