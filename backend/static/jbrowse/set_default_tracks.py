#!/usr/bin/env python3
"""
为 JBrowse config.json 添加 defaultSession，使 GO/KEGG tracks 默认显示。

对每个 config.json：
  - 检查 tracks 中是否包含 GO/KEGG 相关 trackId
  - 如果有，在 defaultSession 中添加这些 track 为默认开启
  - GFF track 始终默认开启

用法：
  cd /path/to/backend/static/jbrowse
  python3 set_default_tracks.py          # 预览模式（不写入）
  python3 set_default_tracks.py --apply  # 实际写入
"""

import json
import glob
import os
import sys

# 需要默认显示的 track 关键字（除了 GFF 始终包含）
GO_KEGG_KEYWORDS = ['biological_process', 'cellular_component', 'molecular_function', 'kegg']

def should_show_by_default(track_id: str) -> bool:
    """判断 track 是否应默认显示"""
    if track_id == 'GFF':
        return True
    return any(kw in track_id for kw in GO_KEGG_KEYWORDS)

def update_config(config: dict, tracks_by_id: dict, genome_name: str = '') -> list:
    """更新 config 的 defaultSession，将所有 tracks 设为默认显示"""
    tracks = config.get('tracks', [])
    # 默认显示所有 track
    default_track_ids = [t['trackId'] for t in tracks if 'trackId' in t]

    # 构建 defaultSession
    assembly_name = ''
    if config.get('assemblies'):
        assembly_name = config['assemblies'][0].get('name', genome_name)

    config['defaultSession'] = {
        "name": assembly_name,
        "views": [
            {
                "id": "linearGenomeView",
                "type": "LinearGenomeView",
                "tracks": [
                    {
                        "type": tracks_by_id.get(tid, {}).get('type', 'FeatureTrack'),
                        "configuration": tid,
                        "displays": [
                            {
                                "type": "LinearBasicDisplay",
                                "configuration": f"{tid}-LinearBasicDisplay"
                            }
                        ]
                    }
                    for tid in default_track_ids
                    if tid in tracks_by_id
                ]
            }
        ]
    }

    return default_track_ids

def main():
    apply = '--apply' in sys.argv
    config_files = sorted(glob.glob('data/**/config.json', recursive=True))

    if not config_files:
        print('未找到 config.json 文件')
        return

    changed = 0
    for config_file in config_files:
        genome_name = os.path.basename(os.path.dirname(config_file))
        if genome_name == 'data':
            continue

        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Build lookup
        tracks_by_id = {t['trackId']: t for t in config.get('tracks', []) if 'trackId' in t}

        default_tracks = update_config(config, tracks_by_id, genome_name)
        changed += 1
        print(f'{"[APPLY]" if apply else "[PREVIEW]"} {genome_name}: 默认显示 {default_tracks} (全部 {len(default_tracks)} 个 track)')

        if apply:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

    print(f'\n共 {changed} 个基因组含 GO/KEGG track')
    if not apply:
        print('添加 --apply 参数以实际写入文件')

if __name__ == '__main__':
    main()
