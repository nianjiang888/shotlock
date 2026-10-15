# ShotSpec v0.1 字段规范

一份分镜脚本是四层结构：`meta`、`characters`、`scenes`、`shots`。实体在表里定义一次，镜头用 id 引用，不允许在镜头里内联重复定义实体。

## meta

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | string | 否 | 集标题 |
| `episode` | int | 否 | 集数 |
| `target_duration_sec` | float | 否 | 目标时长。填了才会跑 SL009 时长预算 |
| `genre` | string | 否 | 题材 |
| `aspect_ratio` | string | 否 | 画幅，短剧一般 `9:16` |

## characters[]

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 主键，镜头引用它 |
| `name` | string | 是 | 角色名 |
| `appearance` | object | 是 | 外貌定义，见下 |
| `traits` | string[] | 否 | 性格标签 |

`appearance` 建议至少给 `hair`、`outfit`、`age_marker` 三项。校验器只比对四个维度的关键词：发长、发色、服装色、年龄感。写成"气质清冷""看着很疲惫"这类主观描述脚本读不出来，等于没写。

能被识别的关键词见 `shotlock/schema.py` 里的 `APPEARANCE_DIMENSIONS`，可以按需扩充。

## scenes[]

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 主键 |
| `location` | string | 是 | 地点 |
| `time_of_day` | string | 是 | 时间 |
| `lighting` | string | 是 | 光线 |
| `int_ext` | enum | 否 | `INT` / `EXT` / `INT_EXT` |

## shots[]

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 主键，全剧唯一 |
| `scene_id` | string | 是 | 引用 scenes.id |
| `duration_sec` | float | 是 | 时长，秒。范围 1.5 到 25 |
| `shot_size` | enum | 是 | 景别，见下 |
| `camera_move` | enum | 是 | 运镜，见下 |
| `transition_in` | enum | 否 | 入点转场，默认 `CUT` |
| `characters` | object[] | 否 | 出场角色，见下 |
| `dialogue` | object[] | 否 | 台词，见下 |
| `emotion` | enum | 否 | 情绪，默认 `neutral` |
| `action` | string | 是 | 画面动作 |
| `props` | string[] | 否 | 道具 |
| `notes` | string | 否 | 备注，不参与校验 |
| `continuity_override` | object | 否 | 时间或光线的偏离声明，见下 |

### 枚举取值

**shot_size**：`EXTREME_WIDE` `WIDE` `FULL` `MEDIUM` `CLOSE_UP` `EXTREME_CLOSE_UP` `INSERT` `OTS` `TWO_SHOT` `POV`

**camera_move**：`STATIC` `PAN` `TILT` `DOLLY` `TRACK` `CRANE` `HANDHELD` `ZOOM` `FOLLOW` `ORBIT`

**transition_in**：`CUT` `FADE_IN` `FADE_OUT` `DISSOLVE` `WIPE` `MATCH_CUT` `JUMP_CUT` `IRIS`

**emotion**：`neutral` `calm` `tense` `angry` `sad` `joy` `fear` `surprised` `disgusted` `affectionate`

### shots[].characters[]

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 引用 characters.id |
| `screen_dir` | enum | `left` / `center` / `right` / `offscreen`。**对话段落必须填，越轴检测依赖它** |
| `appearance_note` | string | 本镜的外貌临时描述。与角色表互斥会触发 SL004 |
| `holding` | string | 手上拿的东西。用于物件闪现检测 |

### shots[].dialogue[]

| 字段 | 类型 | 说明 |
|---|---|---|
| `speaker` | string | 引用 characters.id，旁白可用 `旁白` / `OS` / `VO` |
| `text` | string | 台词正文，参与语速计算 |
| `subtitle` | string | 字幕文本，省略则同 `text` |

### continuity_override

只有当本镜的时间或光线**确实**偏离场景表定义时才填，例如一场戏从黄昏演到深夜：

```json
"continuity_override": {"time_of_day": "深夜"}
```

填了就会触发 SL005。如果这个字段被用来掩盖生成过程中的漂移，校验会直接把它抓出来——它不是逃生通道。

## 最小可校验示例

```json
{
  "meta": {"title": "片段", "target_duration_sec": 10},
  "characters": [{"id": "c_a", "name": "林晚", "appearance": {"hair": "黑色长发", "outfit": "米色风衣"}}],
  "scenes": [{"id": "s_01", "location": "便利店", "time_of_day": "深夜", "lighting": "冷白顶灯", "int_ext": "INT"}],
  "shots": [
    {"id": "sh_001", "scene_id": "s_01", "duration_sec": 4.0, "shot_size": "WIDE",
     "camera_move": "STATIC", "transition_in": "FADE_IN",
     "characters": [{"id": "c_a", "screen_dir": "center"}], "action": "林晚推门进来"},
    {"id": "sh_002", "scene_id": "s_01", "duration_sec": 6.0, "shot_size": "MEDIUM",
     "camera_move": "STATIC", "transition_in": "FADE_OUT",
     "characters": [{"id": "c_a", "screen_dir": "left"}],
     "dialogue": [{"speaker": "c_a", "text": "还没打烊吧，我找个人。", "subtitle": "还没打烊吧，我找个人。"}],
     "action": "林晚走到台前"}
  ]
}
```
