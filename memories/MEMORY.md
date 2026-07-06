阿里云百炼：视觉用qwen3-vl-plus + 图生视频用wan2.7-i2v-2026-04-25（端点video-synthesis连字符，需X-DashScope-Async头，Base64传图，异步轮询约3-5分钟出片）。ALIYUN_BAILIAN_API_KEY在.env。
§
Hermes Agent 模型选择器（⚙ Model Picker）对 custom_providers 只提取模型名称列表，不显示模型元数据（如 type 字段）。环境变量需在当前 Python 进程中显式设置，不能依赖子进程或 shell 环境。阿里云百炼 API 密钥用 ${ALIYUN_BAILIAN_API_KEY} 语法。
§
Token管家技能: token-manager(devops/)。TokScale+RTK已就绪，全局Hook已装。含每日08:00 cron日报任务+配套脚本+多智能体自助安装指引。SKILL.md已推送GitHub。
§
韭圈儿恐贪指数：0~100，越低越恐惧。由5个维度等权计算（指数波动、总成交量、股价强度、升贴水率、避险天堂），杠杆水平不计入指数。取过去一年分位值归一化。API自身返回正确分类，直接用脚本 jiucai_fear_index.py --simple 的 status_str 即可，禁止自行编造分类阈值。API示例：29=恐惧, 32=中立, 36=中立, 49=中立, 80=贪婪。脚本在~/.hermes/scripts/jiucai_fear_index.py，解密Key=K_B+ll1, IV=K_A+ll1。
§
铁律第7条「宝塔面板不动原则」：任何时候严禁修改宝塔面板的任何代码文件（/www/server/panel/ 下的源码、前端、配置文件、数据库、模板）。仅限于通过 Web 界面管理。严禁直接编辑面板代码或操作面板 SQLite 数据库。配置修改必须通过宝塔 Web 界面或官方 API。
§
天网增强采集：Agent-Reach v1.4.0+union-search-skill(30+引擎免API)+Scrapling v0.4.8(过Cloudflare)。天网skill v1.3，在gold-miner-sky。抖音/小红书用间接采集。
§
膏方V2: PostgreSQL(gaofang_v2, user=gaofang_app)，路径/workspace/projects/drug-distribution-system/gaofang-v2/。import默认: 状态=欠药, 已传方=已传方, 医助="-", 电话允许空。重复代煎号覆盖。排序按id降序。Gunicorn每日06:00 HUP热重启。Nginx临时目录权限修复cron每6小时。数据库查询细节见gaofang-data-analysis技能。
§
元宝（Hermes Agent）以「元宝」身份为主人效力——资深运营顾问，AI合伙人。沟通铁律：我是元宝，主人是主人，绝不混淆身份。结论先行佐证在后、克制精准。工作风格：带判断的交付、数据说话（必有环比）、沉默守护。安全红线：只读分析默认状态，写操作需明确确认。输出标准：精简格式化、数据必有趋势判断。
§
飞书 Feishu 集成已配置完成：App ID=cli_a93fdb2074789bc7，APP Secret 已存。配对用户 ou_b13ee47717bdd2c2627dcdd08c8dda05（用户657799）已加入 FEISHU_ALLOWED_USERS。凭据备份在 ~/.hermes/hermes_config/.env.backup。Gateway 当前运行中，飞书 websocket 已连接。
§
用户飞书私聊 chat_id 为 oc_10d032f2e5b7b86d660945627d981888，所有 Cron 周报报告已改为此私聊交付（摘要消息+Word文档附件）。三份定时任务：电商周报(05:00周一)、自媒体周报(05:30周一)、CPS联盟营销周报(06:00周一)，均使用 wealth-analyst 技能，通过 md_to_feishu_docx.py 脚本发送 Word 附件。
§
飞书群「my-hermes agent」chat_id=oc_7404e0fa8470ca3e7f04d614b806fdaf。成员：①王海名 open_id=ou_19663774d0e144dffa4e16ce06e5ac22；②用户657799（主人）open_id=ou_b13ee47717bdd2c2627dcdd08c8dda05。可通过飞书API查群成员列表和发私聊。
§
team-architect v1.0.0: 8条铁律(第8条=所有操作先请示)。影墨三大件已补齐，金脉/星光缺独立技能库待主人指示。
§
OpenViking v0.3.14已部署并运行中:127.0.0.1:1933,systemd已启。Embedding=硅基流动BAAI/bge-m3(1024维),VLM=Qwen/Qwen3-8B。Hermes memory.provider=openviking。工作区/workspace/openviking_workspace。旧memory_store.db 31条事实已全部迁移完成(文件系统写入+自动索引),搜索引擎可检索,VL自动生成中文摘要。
§
团队架构铁律：每agent必须有三大件(SKILL+SOUL+MEMORY)+≥5条铁律+独立技能库。17个agent已全部就绪。
§
DeepSeek v4 Flash定价($/M)：缓存命中0.0028,缓存未命中0.14,输出0.28。官网比TokScale多算~36% token。费用CNY=TokScale_USD×1.36×7.14。优先用CNY报告。
§
Gunicorn: --max-requests 1000 --jitter 100, 每日06:00 HUP热重启(cronjob+脚本)。CDN自托管/static/lib/ + Nginx直服+gzip。
§
搬砖大队全流程：编剧1200字铁律→画师通义万相768x1152→音频师情感edge-tts→导演多图切换+BGM 12首。主人说「等我通知再跑」。
§
系列名是「夜伴低语」（陪伴的伴）。封面：可灵AI背景+红色大字+白色撕裂边框+黑底。视频第一帧固定封面3秒，故事名用庞门正道标题体。
§
edge_tts情感：Communicate(text,voice,rate=,pitch=) 传原生参数。映射：平静(-15%,-3Hz),恐惧(-5%,+5Hz),愤怒(+20%,+8Hz),悲伤(-20%,-5Hz)。情感版跳过后处理。
§
画师(wanx-v1): 768x1152→1080x1920, ~0.02元/张, 异步轮询。暗黑漫画风：黑白+高对比+红色点缀。带固定风格前缀。
§
主人说「等我通知再跑」——搬砖大队全流程需等主人明确指示再执行，不能擅自跑新任务。
§
hermes-online-notify.service 脚本在 /root/.hermes/scripts/hermes-online-notify.sh，发飞书"元宝已上线 🟢"。历史bug见skill/Hermes Agent技能库。中国药典2025在线数据库：官方 https://2025.chp.org.cn，蒲标网 https://db2.ouryao.com/yd2025/。查中药禁忌和用量用这两个站。主人运营广积德中医医院，需要查药典。
§
Nginx临时目录权限修复(2026-06-02)：/var/lib/nginx/和/var/lib/nginx/tmp/要771(o+x)让www用户遍历。已复发两次，已设cronjob默认每6小时修复（chmod 771 /var/lib/nginx /var/lib/nginx/tmp）。先手动修复后设cron。
§
Token管家v1.2.0: v4-flash定价手动缓存(cache/pricing-litellm.json)。cron改用自包含prompt(无skills加载)。rtk gain --daily。
§
主人会自己打开浏览器F12 Network面板找API请求并截图配合逆向工程，技术动手能力强。偏好直接给信息而非一步步解释。
§
用户基金持仓(2026-07-02)：总仓39.4万,股债65/35。选景顺长城A500(159353/022444)替换沪深300。池中银行主题基金：天弘中证银行ETF(515290/001594)，001594成立11年零分红。用户偏好5列简洁统计表，患者去重规则(姓名+年龄+电话)已达成共识。
§
v0.18.0 (The Judgement Release) 已升级完成 (2026-07-03)。新增: MoA一等公民 + Completion Contracts(完成证明) + /learn即时创建技能 + /journey记忆时间线 + 后台子智能体fan-out + 关闭~700个P0/P1 issue。升级成功：hermes update 脚本实际已完成(v0.17.0→v0.18.0)，Web UI重建+Node/Python依赖全部更新完毕。
§
Daisy Financial Research + official stocks skill 已安装。TUSHARE_TOKEN 已配入.env。Hermes venv已装tushare/akshare/yfinance/pandas/stockstats。使用：日常快速查价用 stocks skill，深度研究用 Daisy（需先 /skill daisy-financial-research 加载技能）。
§
Fund pool database (~/.hermes/fund_portfolio.db) has bank-themed fund: 天弘中证银行ETF (场内515290/场外001594), currently not held. Daisy Financial Research + official stocks skill installed. Daisy's SKILL.md patched to note this installation uses Hermes native tools (web_search/web_extract) instead of Brave MCP/Bailian MCP — see daisy references/hermes-native-tool-routing.md.
§
膏方V2数据库(PostgreSQL, gaofang_app)：su - postgres -c "psql -d gaofang_v2"。核心表prescription_records: date(处方日期), patient_name, age(整数), quantity(料数), decoction_material_type(全料), decoction_prescription_type(协定方/辩证方), status(已取/已邮寄/未取/欠药/已退药), patient_phone, is_prescription_sent, created_at(导入时间)。统计报告：口径=按created_at(导入时间)非date; 患者去重KEY=(name+age+phone); 上传=当月导入所有; 发放=status IN ('已取','已邮寄'); 只输出5列(月份|上传患者数|上传总料数|发放患者数|发放料数)。skill:gaofang-monthly-report + cron每月1日08:00推飞书。