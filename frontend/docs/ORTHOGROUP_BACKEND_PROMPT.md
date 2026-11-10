# Orthogroup 详情页后端接口补充提示词

> 本文是一份**自包含**的后端开发提示词，可直接复制给后端开发（或 LLM）执行，
> 用于补齐 iCotton Orthogroup 详情页目前缺失 / 无数据的后端端点。
> 对应前端页面：`/tools/orthogroup/:og_code`（OrthogroupDetailView）。

---

## 现状（实测结论，dev 与 prod 后端一致）

| 端点 | 当前行为 | 判定 |
| --- | --- | --- |
| `GET /CottonOGD_api/orthofinder/sequence/<og_code>` | HTTP 200，真实 FASTA 文本（如 OG0000044 ≈ 103KB） | ✅ 正常 |
| `GET /CottonOGD_api/orthofinder/tree/<og_code>` | HTTP 404 `{"error":"file not found: <og>.treefile"}`（OG0000001/2/10/1000/10000 均 404） | ⚠️ 后端未生成/部署 treefile |
| `GET /CottonOGD_api/orthofinder/msa/<og_code>` | HTTP 200 但 `Content-Type: text/html`，body 是前端 SPA `index.html` | ❌ 后端根本没有 `msa/` 路由，请求落到静态服务器兜底 |

**归因**：前端渲染管线、orthofinder 代理、Sequence 均正常；问题是后端缺 `msa/` 路由、且各 OG 的 `.treefile` 未生成。

---

## 提示词正文

```
你是一位资深 Django + DRF 后端工程师。请为 CottonOGD（iCotton）的 orthofinder
应用补齐 Orthogroup 详情页所需的后端端点。

# 背景
前端已上线"单个 Orthogroup 详情页"（路由 /tools/orthogroup/<og_code>），
分 MSA / 基因树 / 序列 三个数据区。序列端点已正常工作，现需你补齐另外两条：
  - MSA 端点（当前根本无路由，请求被静态服务器兜底成 SPA HTML）
  - 基因树端点所需的 .treefile 文件（当前全部 404 file not found）

# 通用约定（沿用现有 orthofinder 端点）
- 路由前缀：/CottonOGD_api/orthofinder/
- 鉴权：与现有 orthofinder 端点（sequence/、tree/）完全一致
  （前端用 Bearer token 或同站 auth_token cookie 调用，已接好；失效会重登录重放）。
- og_code 形如 OG0000001（字符串，前端直接拼进 URL path）。
- 成功响应：纯文本直接返回（不要套 {code,message,data} 信封，
  前端 axios 拦截器已对文本类接口做 unwrap）。
- 资源不存在 / 尚未生成：返回 HTTP 404。
  不要返回 200 + 空内容，也不要返回非 2xx 的 {"error":...} 包装文本。

# 需新增 / 修复的端点

## 1. MSA（多序列比对）
- 新增路由：GET /CottonOGD_api/orthofinder/msa/<og_code>
- 成功（200）：Content-Type: text/plain; charset=utf-8，返回该 OG 全部成员的
  蛋白/核酸比对 FASTA（或 clustal 亦可）。必须以 '>' 开头，否则前端视为未就绪。
- 未就绪：HTTP 404（前端捕获后展示"该模块暂未就绪"）。

## 2. 基因树（treefile 生成与部署）
- 现有路由 GET /CottonOGD_api/orthofinder/tree/<og_code> 已实现，但目前
  返回 404 {"error":"file not found: <og>.treefile"}。
- 任务：为各 Orthogroup 生成 .treefile（newick 格式），并部署到 tree/ 端点
  读取的路径下，使请求返回 HTTP 200 的纯文本 newick 树。
- 成功（200）：Content-Type: text/plain，返回 newick 字符串。
- 确实无树可生成时：HTTP 404（前端静默隐藏该面板）。

# 联调验证
1. 取已知有成员的 OG（如 OG0000001、OG0000044）请求 msa/ 与 tree/：
   - msa/ 应返回 200 + 以 '>' 开头的 FASTA 文本；
   - tree/ 应返回 200 + newick 文本（而非 404 file not found）。
2. 取不存在 / 尚未生成的 OG：
   - msa/ 与 tree/ 均返回 HTTP 404（前端显示"该模块暂未就绪"，不报错不白屏）。
3. 鉴权：未登录 / token 失效时，行为应与现有 sequence/ 端点一致。

# 无需改动
- sequence/ 端点已正常，不要改动它。
- 前端代码已就位（降级逻辑、i18n 文案均写好），本任务仅涉及后端。
```

---

## 前端侧已做的配套处理（供参考，无需后端改动）

- `src/api/index.ts`：`getOrthogroupMsa` 现会校验返回文本是否以 `>` 开头，
  否则（如拿到 SPA 兜底 HTML）按"未就绪"返回空，避免把 HTML 当 MSA 渲染。
- 详情页在三处 HTTP 失败时统一显示 `og_module_not_ready`
  （"该模块暂未就绪（后端接口待补充）"），不会白屏或抛错。
