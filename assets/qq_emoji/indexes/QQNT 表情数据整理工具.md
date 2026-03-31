# QQNT 表情数据整理工具

本项目旨在对 QQNT 客户端下载的 `index.json` 表情索引文件进行数据清洗、标准化和结构化处理，产出一套可直接用于 AI 检索、表情包管理系统或机器人开发的干净数据。

## 1. 输入文件
*   `index.json`: 原始 QQNT 表情索引文件。

## 2. 输出文件说明

| 文件名 | 格式 | 说明 |
| :--- | :--- | :--- |
| `index_schema_report.md` | Markdown | 原始数据的结构分析报告，包含字段映射、缺失值统计等。 |
| `emoji_records.jsonl` | JSONL | 标准化后的表情记录，每行一条 JSON，适合程序批量读取。 |
| `emoji_records_pretty.json` | JSON | 美化后的 JSON 数组，包含所有标准化字段，便于人工查看。 |
| `emoji_name_alias_map.json` | JSON | 表情主名称与别名的映射表，方便后续检索。 |
| `emoji_assets_report.csv` | CSV | 资源清单报表，列出每个表情的静态/动态资源路径及存在状态。 |
| `parse_index.py` | Python | 用于生成上述所有文件的处理脚本。 |

## 3. 数据整理逻辑

### 3.1 字段映射
*   `emoji_id`: 映射自原始 `emojiId`。
*   `emoji_name`: 映射自原始 `describe`，去掉了前缀 `/`。若原始名称为空，则自动生成 `unnamed_{id}`。
*   `aliases`: 映射自原始 `associateWords`。
*   `asset_path`: 静态资源路径。优先选择 `type: 0` 且文件名不含 `_0` 的 PNG 图片。
*   `animation_path`: 动态资源路径。优先选择 `type: 2` (APNG)，若无则选择 `type: 3` (Lottie JSON)。
*   `category`: 统一标记为 `qqnt`。
*   `raw_source`: 保留了原始的 `describe`、`qzoneCode` 和 `isHide` 字段供追溯。

### 3.2 处理细节
*   **去重**: 确保每个 `emoji_id` 唯一。
*   **编码**: 所有输出文件均强制使用 **UTF-8** 编码。
*   **清洗**: 自动清理名称前后的空白字符及特殊前缀。

## 4. 脚本运行环境
*   Python 3.x
*   无需第三方依赖（仅使用标准库 `json`, `csv`, `os`）。

### 运行方式
将 `index.json` 放在脚本同级目录下，执行：
```bash
python3 parse_index.py
```

## 5. 注意事项
*   **缺失名称**: 原始数据中有 35 条记录缺失 `describe` 名称，脚本已将其标记为 `unnamed_{id}`，建议后续人工补充。
*   **别名数据**: 当前原始数据中的 `associateWords` 均为空，因此生成的别名列表目前为空数组。
*   **资源路径**: 脚本仅整理路径字符串，不校验物理文件是否存在。
