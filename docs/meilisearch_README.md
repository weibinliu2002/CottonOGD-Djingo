# CottonOGD Meilisearch 运维手册

> 后端定位：**只负责数据管理（rebuild / 增量 sync / 实时信号）与 API key 管理**。
> 基因搜索路径：前端使用 search-only API key 直连 Meilisearch 实例，不经过 Django。

## 1. 环境变量配置

在运行 Django 的 shell 中设置：

| 变量 | 说明 | 是否必填 |
|---|---|---|
| `MEILISEARCH_URL` | Meilisearch HTTP 地址，如 `http://127.0.0.1:7700` | 否（默认 http://127.0.0.1:7700） |
| `MEILISEARCH_MASTER_KEY` | 主密钥（管理命令 `setup_meili_keys` / `rebuild_index` / `sync_genes` 使用） | **管理命令必填** |
| `MEILISEARCH_FRONTEND_API_KEY` | 前端直连用的 search-only key（分发后写入即可被后端读取） | **前端直连必填** |
| `MEILISEARCH_CURSOR_PATH` | 增量同步游标 JSON 持久化路径 | 否（默认 `$BASE_DIR/data/meilisync_cursor.json`） |

⚠️ `MEILISEARCH_MASTER_KEY` **任何情况不得打印、写入前端、写入日志**。

## 2. API Key 分发流程

### 2.1 第一次生成 search-only key

```bash
# 确保 MASTER_KEY 已在 env
export MEILISEARCH_MASTER_KEY=xxxxxxxxxxxxxxxxx
export MEILISEARCH_URL=http://127.0.0.1:7700
cd /data/web/CottonOGD/OGD/backend
python manage.py setup_meili_keys --json
```

命令会按 `name='frontend-search'` 或 `description='frontend-search'` 匹配：
- 无则创建：`actions=['search']`, `indexes=['genemaster']`, `expires_at=None`；
- 已存在则**复用并打印相同 uid**。

输出中取 `key` 字段，写入运行环境：

```bash
export MEILISEARCH_FRONTEND_API_KEY=xxxxxSearchOnlyKeyxxxxx
```

之后再次执行 `setup_meili_keys` 会跳过创建并显示：

```
skip: MEILISEARCH_FRONTEND_API_KEY 已配置，沿用环境变量值…
```

### 2.2 校验 actions / indexes

```bash
python manage.py setup_meili_keys --json
# 期望 actions=["search"], indexes=["genemaster"]
```

若输出 `key actions/indexes 不符合规范`（exit 3），请删除错误 key 后重新生成：

```bash
curl -H "Authorization: Bearer $MEILISEARCH_MASTER_KEY" \
  -X DELETE "$MEILISEARCH_URL/keys/<uid>"
```

## 3. 同步机制

后端使用 **三级保障** 让 MySQL 的 `genemaster` 与 Meilisearch 的 `genemaster` 一致：

```
 ┌──────────── Django 事务 ────────────┐
 │  GeneMaster.save() / delete()       │─── post_save / post_delete
 └─────────────────────────────────────┘            │ （实时、异常吞掉）
                                                    ▼
 ┌─────────── 定时任务（每 10 分钟） ─────────────┐
 │  python manage.py sync_genes                  │ （以 created_at 为游标，消费删除队列）
 └────────────────────────────────────────────────┘
                     │ 出错 / 重建场景
                     ▼
 ┌────────────── 人工全量重建 ───────────────────┐
 │  python manage.py rebuild_index --confirm     │ （危险：删除索引→重建→全量导入）
 └────────────────────────────────────────────────┘
```

### 3.1 signals 实时同步（零配置启用）

`CottonOGD/apps.py::CottonogdConfig.ready()` 启动时自动注册信号：
- `post_save` → `add_documents([obj])`
- `post_delete` → `delete_document(obj.id)`

所有 Meili 异常写 `django.log` 的 `logger.error`，不会导致 MySQL 事务回滚。

### 3.2 sync_genes 定时任务（推荐 crontab）

```cron
*/10 * * * * /usr/bin/bash -lc 'cd /data/web/CottonOGD/OGD/backend && \
  /usr/bin/python manage.py sync_genes --batch-size 1000 --retry 3 \
  >> data/meilisync.log 2>&1'
```

常用参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--batch-size` | 1000 | 每批 upsert 大小（1-10000） |
| `--retry` | 3 | 每批失败重试次数（1s/2s/4s 指数退避） |
| `--reset-cursor` | off | 游标归零 epoch 并重跑一次全增量（不会删索引） |

游标存储：`$MEILISEARCH_CURSOR_PATH`（默认 `$BASE_DIR/data/meilisync_cursor.json`）：

```json
{
  "indexes": {
    "genemaster": {
      "last_created_at_iso": "2026-01-02T03:04:05+00:00",
      "last_sync_run_at": "2026-01-02T03:10:00+00:00"
    }
  },
  "pending_deletes": ["1234", "1235"]
}
```

> `pending_deletes` 预留字段，当 signals 删除失败或未来要走批量删除时消费。

## 4. 全量重建（危险操作）

```bash
python manage.py rebuild_index --confirm \
  --batch-size 1000 --workers 1
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--confirm` | off | **必填**，不填会 exit(2) 拒绝执行 |
| `--batch-size` | 1000 | 1-10000 |
| `--workers` | 1 | 保留并发能力（当前版本串行），限制 ≤ 4 |

执行顺序：
1. 若索引存在 → 删除并等 task succeeded；
2. `create_index(primaryKey='id')`；
3. `update_settings(searchableAttributes=['geneid','alias'], filterableAttributes=['genome_id'])`；
4. 从 `GeneMaster.objects.all().order_by('pk').iterator(chunk_size)` 逐批 `add_documents`；
5. 结束后再次读取并校验 `index.get_settings()`。

⚠️ **重建期间搜索服务不可用**（索引被删直到重新导入）。建议 100w+ 数据在低峰执行。

## 5. 验证脚本 verify_import.py

```bash
cd /data/web/CottonOGD/OGD/backend
python scripts/verify_import.py --samples 200
```

退出码：

| 退出码 | 含义 |
|---|---|
| 0 | 所有步骤通过 |
| 1 | 至少一步失败 |
| 2 | MySQL 或 Meili 连接错误 |

校验步骤：
- **A**：`COUNT(*)` MySQL vs Meili `numberOfDocuments`（允许 0 差）；
- **B**：基于 PK 偏移随机抽 N 条，按 id 调 `get_document` 比较 `geneid/genome_id/alias`；
- **C**：跨基因组重复 geneid 验证（找到重复最多个数的 geneid，搜索后核对命中数 ≥ 2 / 至少 2 个不同主键文档存在）——若数据库无重复则跳过；
- **D**：取最大基因组 species，构造 `filter = 'genome_id = "<escaped>"'` 过滤搜索，校验所有命中 `genome_id` 都等于该物种名。

> 脚本内部直接 `import CottonOGD.management.commands.rebuild_index` 获取 `INDEX_NAME` 常量。

## 6. 故障排查

### 6.1 任务 task failed / timeout

所有写操作都通过 `wait_for_task` 轮询确认；`failed` 时 management command 会打印：

```
Task#1234(add_documents::import-7) failed: code=invalid_request type=... message=...
```

解决：
- `invalid_request` + `invalid_filters`：`update_settings` 传参拼写错误，检查命令未被改动；
- `invalid_document_id`：确认 `id` 字段为字符串（代码已保证 `str(obj.id)`）；
- `primary_key_already_exists`：索引已创建但主键不同 → 必须 `delete_index` 后重建（即 `rebuild_index --confirm`）。
- `payload_too_large`：调小 `--batch-size`。

### 6.2 主键错了怎么办（primary key 非 id）

Meilisearch 一旦创建索引**无法更改主键**。唯一办法：

```bash
python manage.py rebuild_index --confirm
```

命令会先删索引→重建→再导全量。

### 6.3 search-only key 权限不足（前端 403）

可能 actions 不包含 `search`，或 indexes 限制错。执行：

```bash
curl -sS -H "Authorization: Bearer $MEILISEARCH_MASTER_KEY" "$MEILISEARCH_URL/keys" \
  | python -m json.tool | grep -A20 frontend-search
```

若不符合要求（`actions=['search']`, `indexes=['genemaster']`），删除旧 key 并重新 `setup_meili_keys`。

### 6.4 Meili 不可用（signals 行为）

- signals 吞掉异常，写入 `django.log` 的 `CottonOGD.signals` logger；
- MySQL 写入/删除正常成功，不影响主业务；
- 待 Meili 恢复后跑 `python manage.py sync_genes --reset-cursor` 做一次**全增量**补齐（推荐）；
- 或直接 `rebuild_index --confirm` 从 0 全量覆盖。

### 6.5 sync_genes 游标不对 / 缺失

```bash
python manage.py sync_genes --reset-cursor
```

该命令：
- 游标归零至 epoch；
- 重新按 created_at 扫描所有 GeneMaster（但 **不会删除 Meili 已有文档**，add_documents 幂等覆盖）。

若需要严格一致（含删除修正）仍推荐 `rebuild_index --confirm`。

## 7. 文件清单（交付结构）

```
backend/
├── mysite/settings.py                ← 新增 MEILISEARCH_* 4 个配置（env 读取）
├── CottonOGD/
│   ├── config/meilisearch_config.py   ← 客户端工厂（use_master 开关，延迟 settings import）
│   ├── apps.py                        ← ready() 注册 CottonOGD.signals
│   ├── signals.py                     ← GeneMaster post_save/post_delete 实时同步（吞异常）
│   └── management/commands/
│       ├── setup_meili_keys.py        ← 幂等创建/查询 frontend-search key
│       ├── rebuild_index.py           ← 全量重建索引（危险操作，--confirm）
│       └── sync_genes.py              ← 增量同步 + 游标持久化
└── scripts/
    └── verify_import.py               ← 4 步一致性校验（退出码 0/1/2）
```

文档：`docs/meilisearch_README.md`（本文件）
