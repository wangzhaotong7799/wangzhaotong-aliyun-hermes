# 🎵 BGM曲库清单

> 更新于：2026-05-15
> 来源：主人自行下载至 `horror dark ambient/`
> 工作目录：`audio/`（软链接）

## 全部曲目（12首）

| # | 文件名 | 大小 | 类型 |
|:-:|:-------|:----:|:-----|
| 1 | `leberch-dark-horror-509729.mp3` | 3.6MB | 黑暗恐怖 |
| 2 | `leberch-dark-horror-510070.mp3` | 4.4MB | 黑暗恐怖 |
| 3 | `leberch-ambient-horror-518292.mp3` | 4.6MB | 氛围恐怖 |
| 4 | `leberch-horror-512450.mp3` | 3.7MB | 恐怖配乐 |
| 5 | `leberch-horror-suspense-ambient-375929.mp3` | 3.5MB | 悬疑氛围 |
| 6 | `atlasaudio-horror-ambience-512255.mp3` | 2.9MB | 恐怖环境音 |
| 7 | `everything_is_dead-dark-ambient-516343.mp3` | 11MB | 死寂氛围 |
| 8 | `everything_is_dead-dark-ambient-soundscape-493696.mp3` | 3.1MB | 死寂氛围 |
| 9 | `lnplusmusic-scary-horror-dark-music-372674.mp3` | 2.9MB | 恐怖黑暗音乐 |
| 10 | `sigmamusicart-horror-394969.mp3` | 2.4MB | 恐怖配乐 |
| 11 | `universfield-dark-shamanic-horror-516353.mp3` | 2.4MB | 黑暗仪式感 |
| 12 | `universfield-tense-horror-background-174809.mp3` | 2.9MB | 紧张背景 |

## 添加新BGM

主人下载新文件后，执行以下命令创建软链接：

```bash
cd /root/wangzhaotong-hermes/horror-pipeline/audio
for f in /root/wangzhaotong-hermes/horror-pipeline/horror\ dark\ ambient/*.mp3; do
  base=$(basename "$f")
  [ ! -f "$base" ] && ln -s "$f" "$base" && echo "链接: $base"
done
```
