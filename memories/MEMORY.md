阿里云百炼：视觉用qwen3-vl-plus + 图生视频用wan2.7-i2v-2026-04-25（端点video-synthesis连字符，需X-DashScope-Async头，Base64传图，异步轮询约3-5分钟出片）。ALIYUN_BAILIAN_API_KEY在.env。
§
Hermes Agent 模型选择器（⚙ Model Picker）对 custom_providers 只提取模型名称列表，不显示模型元数据（如 type 字段）。环境变量需在当前 Python 进程中显式设置，不能依赖子进程或 shell 环境。阿里云百炼 API 密钥用 ${ALIYUN_BAILIAN_API_KEY} 语法。
§
Token管家技能: token-manager(devops/)。TokScale+RTK已就绪，全局Hook已装。含每日08:00 cron日报任务+配套脚本+多智能体自助安装指引。SKILL.md已推送GitHub。
§
数据质量铁律加固(2026-05-04)：三份周报Cron只采2026年数据、标注data_year、严禁改年份。猎财SOP新增年份验证闸门——剔除<2026数据，篡改即中断。天网输出新增collected_at/source_publish_date/data_year字段。
§
铁律第7条「宝塔面板不动原则」：任何时候严禁修改宝塔面板的任何代码文件（/www/server/panel/ 下的源码、前端、配置文件、数据库、模板）。仅限于通过 Web 界面管理。严禁直接编辑面板代码或操作面板 SQLite 数据库。配置修改必须通过宝塔 Web 界面或官方 API。
§
天网增强采集(累计集成)：① Agent-Reach v1.4.0(微博/微信/B站/V2EX/雪球/YouTube/GitHub) ② union-search-skill(百度/搜狗/360/头条等30+引擎免API) ③ Scrapling v0.4.8(过Cloudflare自适应反爬框架)。天网skill已升级v1.3，新增方法D(Scrapling)。天网在gold-miner-sky SKILL.md。抖音/小红书直接API需Cookie/TikHub Token，当前用间接采集(搜外部报道)。
§
膏方V2导入规则：状态默认「欠药」，是否传方默认「已传方」，医助默认为"-"（允许为空），电话号码允许为空。遇到重复代煎号则覆盖更新（保留复诊/审计字段），不跳过。列表排序用户坚持按 id 降序。
§
膏方V2编辑保存修复：shipping_time空串写入PostgreSQL Date字段导致InvalidDatetimeFormat。修复方法——后端api/v1/prescriptions.py中DATE_FIELDS空串转None，前端page-prescriptions.js发送null而非''，then回调检查result.error。改完需重启gaofang-v2-fusion.service。
§
元宝（Hermes Agent）以「元宝」身份为主人效力——资深运营顾问，AI合伙人。沟通铁律：我是元宝，主人是主人，绝不混淆身份。结论先行佐证在后、克制精准。工作风格：带判断的交付、数据说话（必有环比）、沉默守护。安全红线：只读分析默认状态，写操作需明确确认。输出标准：精简格式化、数据必有趋势判断。
§
膏方V2导入Excel是广积德系统导出的「代煎导出」格式：处方日期、处方编号、患者姓名/性别/年龄、处方模板、代煎料型/方型、料数、医生姓名、医助、代煎状态、支付/收款状态、代煎克重、饮片/加工费用、患者手机号、快递地址。门店/推荐人忽略。
§
飞书 Feishu 集成已配置完成：App ID=cli_a93fdb2074789bc7，APP Secret 已存。配对用户 ou_b13ee47717bdd2c2627dcdd08c8dda05（用户657799）已加入 FEISHU_ALLOWED_USERS。凭据备份在 ~/.hermes/hermes_config/.env.backup。Gateway 当前运行中，飞书 websocket 已连接。
§
用户飞书私聊 chat_id 为 oc_10d032f2e5b7b86d660945627d981888，所有 Cron 周报报告已改为此私聊交付（摘要消息+Word文档附件）。三份定时任务：电商周报(05:00周一)、自媒体周报(05:30周一)、CPS联盟营销周报(06:00周一)，均使用 wealth-analyst 技能，通过 md_to_feishu_docx.py 脚本发送 Word 附件。
§
飞书群「my-hermes agent」chat_id=oc_7404e0fa8470ca3e7f04d614b806fdaf。成员：①王海名 open_id=ou_19663774d0e144dffa4e16ce06e5ac22；②用户657799（主人）open_id=ou_b13ee47717bdd2c2627dcdd08c8dda05。可通过飞书API查群成员列表和发私聊。
§
team-architect 技能已建（v1.0.0），含8条铁律，重点是第8条「所有操作必须请示」——任何系统配置/文件/外部操作改动前必须先问主人。附references/user-work-rules.md集中存放主人工作铁则。影墨小队三大件（SKILL+SOUL+MEMORY）已全部补齐，每个agent有独立技能库（scripts/references/templates）。金脉小队和星光小队缺少独立技能库，星光小队MEMORY.md为0KB空文件，主人已知晓但尚未指示补全。
§
OpenViking v0.3.14已部署并运行中:127.0.0.1:1933,systemd已启。Embedding=硅基流动BAAI/bge-m3(1024维),VLM=Qwen/Qwen3-8B。Hermes memory.provider=openviking。工作区/workspace/openviking_workspace。旧memory_store.db 31条事实已全部迁移完成(文件系统写入+自动索引),搜索引擎可检索,VL自动生成中文摘要。
§
团队架构铁律：每个 agent 必须有独立三大件（SKILL.md+SOUL.md+MEMORY.md）+ 铁律（≥5条）+ 独立技能库（scripts/ / references/ / templates/）。建队必须按 team-architect 技能走架构优先流程，全部验收通过才能开工。已补齐金脉小队4人 + 星光小队10人 + 影墨小队3人，共17个agent全部就绪。
§
DeepSeek v4 Flash定价($/M)：缓存命中0.0028,缓存未命中0.14,输出0.28。官网比TokScale多算~36% token。费用CNY=TokScale_USD×1.36×7.14。优先用CNY报告。
§
Gunicorn 卡死根治 + 膏方网站优化(2026-05-23)：CDN自托管到/static/lib/ + Nginx直服首页/静态文件 + gzip压缩。Gunicorn加--max-requests 1000 --max-requests-jitter 100防worker卡死，每日06:00 cron HUP热重启（cronjob 5495db19311f, 脚本gunicorn-daily-reload.sh）。
§
搬砖大队全流程就绪(2026-05-15首跑成功)：编剧1200字铁律+画师通义万相wanx-v1(768x1152,~0.02元/张,20-60s,固定黑白+红风格前缀)+音频师情感edge-tts(冷静-15%/-3Hz,恐惧-5%/+5Hz,悲伤-20%/-5Hz,尖锐+10%/+10Hz,跳过后处理)+导演多场景图切换。BGM库12首。用户要求「等我通知再跑」，不擅自启动。
§
系列名是「夜伴低语」（陪伴的伴），不是夜半低语。封面图上也写的是夜伴低语。所有代码/技能/输出统一用夜伴低语。封面设计：可灵AI生成图做背景，红色大字+白色撕裂边框+黑底。视频第一帧固定展示封面3秒。故事名用庞门正道标题体叠加在封面上。
§
edge_tts情感方案：SSML被escape()阻断，正确方案是 edge_tts.Communicate(text, voice, rate=, pitch=) 直接传原生rate/pitch参数。情绪映射：平静(-15%,-3Hz)、恐惧(-5%,+5Hz)、愤怒(+20%,+8Hz)、悲伤(-20%,-5Hz)。FFmpeg后处理(volume+aecho+equalizer)会破坏情感，情感版必须跳过后处理。
§
画师已接入通义万相 wanx-v1，尺寸768x1152(缩放至1080x1920)。固定暗黑漫画风：黑白粗线条+高对比+红色点缀。工具 scripts/wanx_image_gen.py，异步轮询约30-60秒出图，~0.02元/张。Prompt必须带固定风格前缀。
§
主人说「等我通知再跑」——搬砖大队全流程需等主人明确指示再执行，不能擅自跑新任务。
§
hermes-online-notify.service 脚本在 /root/.hermes/scripts/hermes-online-notify.sh，发飞书"元宝已上线 🟢"。历史bug见skill/Hermes Agent技能库。中国药典2025在线数据库：官方 https://2025.chp.org.cn，蒲标网 https://db2.ouryao.com/yd2025/。查中药禁忌和用量用这两个站。主人运营广积德中医医院，需要查药典。
§
膏方V2 504修复(2026-06-02)：根因是拼音搜索先SQL分页再Python过滤导致分页错误+线程耗尽。三项改动：①prescriptions.py中拼音搜索先取全部ID做拼音匹配再分页取完整数据；②Gunicorn workers/threads 2→4；③Nginx proxy_read_timeout 60s→120s。已推送drug-distribution-system master分支。
§
Nginx临时目录权限修复(2026-06-02)：/var/lib/nginx/和/var/lib/nginx/tmp/要771(o+x)让www用户遍历。已复发两次，已设cronjob默认每6小时修复（chmod 771 /var/lib/nginx /var/lib/nginx/tmp）。先手动修复后设cron。
§
Token管家 cron 故障修复(2026-06-09)：三个根因—①deepseek-v4-flash不在LiteLLM定价库中，TokScale报JSON parse failed，已手动加入缓存（输入$0.14/M、缓存命中$0.0028/M、输出$0.28/M）；②SKILL.md 30K+字符加载到cron上下文导致agent无响应，已改用自包含prompt(无skills加载)；③rtk gain误用累计参数，已改为rtk gain --daily。修复后TokScale无警告正常运行，定价缓存已更新到~/.config/tokscale/cache/pricing-litellm.json。token-manager技能已升级v1.2.0。