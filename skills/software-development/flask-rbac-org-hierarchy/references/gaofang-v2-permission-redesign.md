# 膏方V2 权限架构改造 — 现状盘点 + 目标架构（2026-08 进行中）

## 项目位置
`/workspace/projects/drug-distribution-system/gaofang-v2/`（Flask + PostgreSQL，库 `gaofang_v2`）

## 检索提示（本项目实测）
项目内搜代码用 terminal grep，不要用 search_files（本会话 search_files 对含 yizhu001 的文件返回 0，terminal grep 正常）：
```bash
cd /workspace/projects/drug-distribution-system/gaofang-v2 && grep -rn "关键词" --include="*.py" . | grep -v venv38
```
venv38 是项目虚拟环境目录，必须排除。

## 当前权限现状（改造前基线）
- 认证：JWT HS256 24h，token 内带 `user_id / username / roles`
- 角色表 roles：1=admin 系统管理员, 2=assistant 医助, 3=pharmacy, 4=yaoju 药局
- 23 个用户：admin, cw001 何梅, yaoju001 王绪军, yaoju002 王朝彤, yizhu001~017（医助，full_name 为中文姓名）, GJD-A 赖总, GJD-B 杨院
- **数据归属关键**：处方表 `prescription_records.assistant` 字段存**医助姓名**（曹莹莹/李庆荣…），非 username → 行级过滤需靠 姓名 ↔ `users.full_name` 关联
- 权限控制两套并存：
  * 用户/角色管理接口：标准 RBAC `@permission_required('user:create/read/update/delete')`（api/v1/auth.py, api/v1/roles.py）
  * 复诊模块：硬编码 `SPECIAL_ACCOUNTS=['yizhu001','GJD-A','GJD-B']` 看全部，普通医助看自己（api/v1/follow_up_management.py，`_get_assistant_info` 用 payload roles + user.full_name/username 过滤）
  * app.py 备份/恢复/打印：硬编码 `'admin' in g.roles` / `'pharmacy'/'yaoju'/'药局'`

## 目标架构（主人 2026-08-06 提供，细节未确认）
```
超级管理员（全权限）
└── 药局管理员（全数据，可管用户/角色）
    ├── 领导层（看全部数据，只读为主？）
    ├── 总监A → 小组1+2+3+4+5（全部）
    ├── 总监B → 小组3+4
    ├── 总监C → 小组1+2+5
    ├── 组长×5 → 本组数据
    └── 组员 → 自己名下数据
```
核心：**角色（功能权限）× 小组（行级数据范围）双层模型**。

## 动工前待确认（4问，2026-08-06 已抛出，等主人答复）
1. 组长能看什么？本组全部 or 仅自己名下
2. 组员能看什么？仅自己 or 本组
3. 领导层定位：看全部数据，只读？
4. 现有 23 用户如何分 5 组；GJD-A/B 是总监还是领导层；cw001 归属

## 建议实现路径（待确认后）
1. 新表 `groups(id, name)` + `users.group_id`；总监级多组范围用关联表 `director_groups` 或 `users.visible_group_ids`
2. 数据归属：处方 `assistant` 姓名 ↔ `users.full_name` → 用户 group_id → 组范围
3. 统一鉴权：token 增加组信息；业务接口改为「角色 + 组范围」动态过滤，替换硬编码 SPECIAL_ACCOUNTS 与字符串角色判断
4. 改完 Gunicorn 重启 + 清 __pycache__（见 SKILL.md 陷阱）
