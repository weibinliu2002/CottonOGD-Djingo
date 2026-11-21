# 错误码

v1 所有错误使用同一信封，错误码为整数，**HTTP 状态 = `code // 100`**。
服务层（`CottonOGD/server/**`）只抛 `common.errors.ServiceError` 子类；
API 层由 `@v1_api` 统一捕获并序列化，不允许视图自行拼错误 JSON。

## 1. 响应格式

```json
{
  "code": 40401,
  "message": "Orthogroup OG0000001 not found",
  "data": null
}
```

`data` 在需要提示可选值时会带补充信息，例如：

```json
{
  "code": 40401,
  "message": "synteny not precomputed for A -> B",
  "data": {"pairs": [{"source": "A", "target": "C"}]}
}
```

## 2. 错误码表

| code | HTTP | 异常类 | 含义 | 典型触发 |
|---|---:|---|---|---|
| `40001` | 400 | `ValidationError` | 参数缺失 / 类型错误 | 缺 `gene_ids`、`gene_ids` 不是数组、空列表 |
| `40002` | 400 | `InvalidValueError` | 参数取值非法 / 格式错误 | 非法坐标、路径穿越、未知 `mode`、密码强度不足 |
| `40003` | 400 | `PreconditionError` | 业务前置条件不满足 | 解绑最后一个第三方账号、邮箱未验证 |
| `40101` | 401 | `AuthenticationError` | 未认证 / 会话无效 | 缺少或伪造 Bearer、refresh 无效、密码错误 |
| `40102` | 401 | `TokenExpiredError` | JWT 过期 | access token 超时 |
| `40301` | 403 | `PermissionDeniedError` | 无权限 / 资源非本人 | 删除他人文件、未验证邮箱登录 |
| `40302` | 403 | `AccountLockedError` | 账号锁定 | 连续登录失败达到上限 |
| `40401` | 404 | `NotFoundError` | 资源不存在 | 未知 OG / 文件 UUID / STRING 映射为空 |
| `40901` | 409 | `ConflictError` | 冲突 | 同目录同名文件已存在 |
| `41301` | 413 | `ServiceError` | 请求体过大 | 超出上传限制 |
| `41501` | 415 | `UnsupportedMediaError` | 上传类型不支持 | 非 multipart 上传 |
| `42901` | 429 | `RateLimitedError` | 限流 | 验证邮件重发冷却、登录频率限制 |
| `50001` | 500 | `ServiceError` | 内部错误 | 未捕获异常（生产不返回 traceback） |
| `50201` | 502 | `UpstreamError` | 上游失败 | STRING / Meilisearch / LLM 不可用 |
| `50301` | 503 | `ConfigurationError` | 服务未配置 | 缺少外部工具或密钥 |
| `50401` | 504 | `UpstreamTimeoutError` | 外部工具超时 | STRING 请求超时、子进程超时 |

## 3. 框架异常映射

`@v1_api` 对未主动转换的异常统一处理：

| 来源 | 映射 |
|---|---|
| `django.http.Http404` | `40401` |
| DRF `APIException` 且 HTTP 400 | `40001`（`message` 保留原 `detail`） |
| DRF `APIException` 且 HTTP 404 | `40401` |
| 其他 DRF `APIException` | `code = http_status * 100` |
| 其他 `Exception` | `50001`；`DEBUG=True` 时 `data.traceback` 附带堆栈 |

## 4. 客户端处理建议

- 先判断 HTTP 状态做粗分类，再用 `code` 做精确分支；不要解析 `message`。
- `40101` / `40102`：清除本地 access，尝试 `POST /v1/auth/refresh/`；
  刷新失败则回到登录页。
- `42901`：读取 `message` 中的冷却提示，禁用按钮等待后重试。
- `40401` 且 `data` 含候选列表时，可直接渲染为可选项（如 synteny 可用基因组对）。
- 未知新错误码：按 HTTP 状态兜底，记录 `code` 以便排查。

## 5. 新增错误码

1. 在 `CottonOGD/common/errors.py` 增加常量与（必要时）异常子类；
2. 保证 `code // 100` 是有意义的 HTTP 状态；
3. 更新本文件与 `scripts/nginx_api_v1.snippet` 无关，但需重新生成 `openapi.yaml`；
4. 不要在 `api/**` 中手写 `{"code": ...}` 响应。