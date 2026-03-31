import json
import csv
import os

def parse_index():
    input_file = 'index.json'
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    standardized_records = []
    name_alias_map = {}
    assets_report = []

    for item in raw_data:
        emoji_id = str(item.get('emojiId', ''))
        raw_name = item.get('describe', '').strip()
        # 清理名称，去掉前缀 /
        emoji_name = raw_name.lstrip('/') if raw_name else f"unnamed_{emoji_id}"
        
        # 别名处理 (associateWords)
        aliases = item.get('associateWords', [])
        if not isinstance(aliases, list):
            aliases = [aliases] if aliases else []
        
        # 资源路径处理
        asset_path = ""
        animation_path = ""
        
        assets = item.get('assets', [])
        # 静态资源优先级：Type 0 且不带 _0 的优先
        static_assets = [a for a in assets if a.get('type') == 0]
        if static_assets:
            # 优先找不带 _0 的主图
            main_static = next((a for a in static_assets if "_0" not in a.get('name', '')), static_assets[0])
            asset_path = main_static.get('path', '')
            
        # 动态资源优先级：Type 2 (APNG) > Type 3 (Lottie)
        anim_assets_type2 = [a for a in assets if a.get('type') == 2]
        anim_assets_type3 = [a for a in assets if a.get('type') == 3]
        
        if anim_assets_type2:
            animation_path = anim_assets_type2[0].get('path', '')
        elif anim_assets_type3:
            animation_path = anim_assets_type3[0].get('path', '')

        # 1. 标准化记录
        record = {
            "emoji_id": emoji_id,
            "emoji_name": emoji_name,
            "aliases": aliases,
            "asset_path": asset_path,
            "animation_path": animation_path,
            "category": "qqnt",
            "raw_source": {
                "describe": raw_name,
                "qzoneCode": item.get('qzoneCode'),
                "isHide": item.get('isHide')
            }
        }
        standardized_records.append(record)

        # 2. 名称映射表 (主名称 -> 别名)
        if emoji_name:
            # 如果名称已存在，合并别名
            if emoji_name in name_alias_map:
                existing_aliases = set(name_alias_map[emoji_name])
                existing_aliases.update(aliases)
                name_alias_map[emoji_name] = sorted(list(existing_aliases))
            else:
                name_alias_map[emoji_name] = sorted(list(set(aliases)))

        # 3. 资源清单报表数据
        assets_report.append({
            "emoji_id": emoji_id,
            "emoji_name": emoji_name,
            "asset_path": asset_path,
            "animation_path": animation_path,
            "has_static_asset": "Yes" if asset_path else "No",
            "has_animation_asset": "Yes" if animation_path else "No",
            "category": "qqnt"
        })

    # 输出文件 1: emoji_records.jsonl
    with open('emoji_records.jsonl', 'w', encoding='utf-8') as f:
        for record in standardized_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # 输出文件 2: emoji_records_pretty.json
    with open('emoji_records_pretty.json', 'w', encoding='utf-8') as f:
        json.dump(standardized_records, f, indent=2, ensure_ascii=False)

    # 输出文件 3: emoji_name_alias_map.json
    with open('emoji_name_alias_map.json', 'w', encoding='utf-8') as f:
        json.dump(name_alias_map, f, indent=2, ensure_ascii=False)

    # 输出文件 4: emoji_assets_report.csv
    with open('emoji_assets_report.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["emoji_id", "emoji_name", "asset_path", "animation_path", "has_static_asset", "has_animation_asset", "category"])
        writer.writeheader()
        writer.writerows(assets_report)

    print("Successfully generated all files:")
    print("- emoji_records.jsonl")
    print("- emoji_records_pretty.json")
    print("- emoji_name_alias_map.json")
    print("- emoji_assets_report.csv")

if __name__ == "__main__":
    parse_index()
