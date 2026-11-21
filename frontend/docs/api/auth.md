# 认证与账号

v1 认证由 `CottonOGD/common/auth.py` 统一解析，服务层
`CottonOGD/server/auth/service.py` 实现业务规则。受保护端点使用
`@require_user`，会话端点使用 `@require_session`，失败统一返回 `40101` 信封
（而不是 DRF 默认的 403/401 响应体）。

## 1. 三种主体

| 主体 | 来源 | 典型用途 |
|---|---|---|
| `jwt` | `Authorization: Bearer <access>` | 登录用户：个人文件、账号管理 |
| `session` | Cookie `auth_token`（或 `X-Auth-Token`） | 匿名会话：AI 对话历史 |
| `anonymous` | 无凭据 | 公开业务接口 |

解析顺序：SimpleJWT → Redis 会话 `auth_token:<token>` → Cookie。
公开端点会忽略无效/过期 Bearer，不会因为旧 token 残留而 401。

## 2. JWT

| 项 | 值 |
|---|---|
| 算法 / 头 | SimpleJWT 默认；`Authorization: Bearer <token>` |
| access 有效期 | 15 分钟 |
| refresh 有效期 | 7 天 |
| 签发 | `POST /v1/auth/login/`（或兼容端点 `POST /v1/auth/token/`） |
| 刷新 | `POST /v1/auth/refresh/`（或 `/v1/auth/token/refresh/`） |

登录成功 `data`：

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "user": {
    "id": 12, "username": "alice", "email": "a@example.com",
    "email_verified": true
  }
}
```

刷新成功 `data`：`{"access": "...", "refresh": "..."}`。刷新失败一律
`40101`（不区分「不存在 / 过期 / 格式错误」）。

> 邮箱未验证时 `is_active=False`：SimpleJWT 不会为未激活用户签发 token，
> 登录阶段也会返回 `40301`（邮箱未验证）。

## 3. 注册与邮箱验证

```http
POST /CottonOGD_api/api/v1/auth/register/
{"email":"a@example.com","username":"alice","password":"...","confirm_password":"..."}
```

规则：

- 邮箱/用户名不区分大小写查重，冲突 `40901`。
- 密码 ≥ 8 位且同时包含字母与数字，否则 `40002`。
- 注册后 `is_active=False`，发送验证邮件；再次发送需等 60 秒（`42901`）。
- 验证：`POST /v1/auth/verify-email/ {"key": "<邮件里的 key>"}`。
- 邮件中的链接走 allauth `/accounts/confirm-email/<key>/`；生产 nginx 只反代
  `/CottonOGD_api/`，因此实际链接使用 `/CottonOGD_api/accounts/...` 双挂载
  （见 `server/auth/adapters.py` 的 `PUBLIC_ACCOUNTS_PREFIX`）。

## 4. 登录与锁定

```http
POST /CottonOGD_api/api/v1/auth/login/
{"email":"a@example.com","password":"..."}
```

- `email` 与 `username` 二选一；同时提供 → `40002`；都不提供 → `40001`。
- 密码错误 → `40101`（不暴露账号是否存在）。
- 未验证邮箱 → `40301`。
- 连续失败触发 allauth 限流（5 次/15 分钟/登录标识，10 次/分钟/IP），
  后续请求 → `40302`。

## 5. 密码

| 端点 | 说明 |
|---|---|
| `POST auth/forgot-password/` | `{email}`；发送重置邮件。邮箱不存在时返回 `40101`（防枚举） |
| `POST auth/reset-password/` | `{uidb36, key, new_password}`；token 无效 `40002` |
| `POST auth/password/change/` | 登录后 `{new_password}`；成功发送通知邮件 |
| `POST auth/set-password/` | 登录后为第三方注册用户设置本地密码 |

密码强度规则与注册一致；不满足返回 `40002`。

## 6. 当前用户与账号管理

| 端点 | 认证 | 返回 |
|---|---|---|
| `GET auth/me/` | 登录 | 用户字段 + `bound_third_party_accounts` |
| `DELETE auth/me/` | 登录 | 删除账号，返回 `{deleted:true,email}` |
| `GET auth/methods/` | 登录 | 可用登录/绑定方式 |
| `POST auth/bind-third-party/` | 登录 | `{provider,uid}`；未连接 `40401`，属于他人 `40002` |
| `POST auth/unbind-third-party/` | 登录 | 仅剩一个第三方账号时 `40003` |

## 7. 匿名会话

```http
POST /CottonOGD_api/api/v1/auth/session/
```

返回 `{uuid, token}`，同时写入 HttpOnly Cookie `auth_token`（7 天，`SameSite=Lax`）。
`DELETE /v1/auth/session/` 注销并清除 Cookie。AI 对话用该会话做历史上限隔离：
登录用户按 `user:<id>`，匿名按 `session_uuid`。

## 8. 第三方登录（OAuth）

allauth 负责 provider 流程，回调端点保留在根路径：

| provider | 回调 |
|---|---|
| Google | `GET /accounts/google/login/callback/` |
| ORCID | `GET /accounts/orcid/login/callback/` |

回调成功签发 SimpleJWT，302 跳转到前端回调页并附带 token；失败 302 回登录页
并带 `error` 参数。具体 client id/secret 通过 `.env` / allauth 配置注入，
**不写入仓库**。

## 9. 权限矩阵

| 端点组 | 匿名 | 登录 | 会话 |
|---|:---:|:---:|:---:|
| `meta` `search` `genes` `annotations` `expression` `sequences` `blast` `structure` `primer` `genome` `synteny` `variants` `gwas` `conversion` `orthofinder` `ppi` | ✅ | ✅ | ✅ |
| `files/public/*`、`files/genome/*` | ✅ | ✅ | ✅ |
| `files/my/*` | ❌ `40101` | ✅（owner 隔离） | ❌ |
| `auth/me`、`auth/methods`、`auth/password/*`、`auth/bind-*` | ❌ | ✅ | ❌ |
| `ai/chat/` | ❌ | ✅ | ✅ |
| `ai/tools/` | ✅ | ✅ | ✅ |

文件 owner 校验失败按**资源不存在**处理（`40401`），不暴露他人文件存在性。