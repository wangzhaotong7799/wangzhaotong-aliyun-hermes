阿里云百炼：视觉用qwen3-vl-plus + 图生视频用wan2.7-i2v-2026-04-25（端点video-synthesis连字符，需X-DashScope-Async头，Base64传图，异步轮询约3-5分钟出片）。ALIYUN_BAILIAN_API_KEY在.env。
§
Hermes Agent 模型选择器（⚙ Model Picker）对 custom_providers 只提取模型名称列表，不显示模型元数据（如 type 字段）。环境变量需在当前 Python 进程中显式设置，不能依赖子进程或 shell 环境。阿里云百炼 API 密钥用 ${ALIYUN_BAILIAN_API_KEY} 语法。
§
Token管家v1.2.0(token-manager/devops): TokScale+RTK+全局Hook已装, 每日08:00 cron日报+脚本, v4-flash定价手动缓存(cache/pricing-litellm.json), cron用自包含prompt, rtk gain --daily。SKILL.md已推送GitHub。
§
韭圈儿恐贪指数：0~100，越低越恐惧。由5个维度等权计算（指数波动、总成交量、股价强度、升贴水率、避险天堂），杠杆水平不计入指数。取过去一年分位值归一化。API自身返回正确分类，直接用脚本 jiucai_fear_index.py --simple 的 status_str 即可，禁止自行编造分类阈值。脚本在~/.hermes/scripts/jiucai_fear_index.py，解密Key=K_B+ll1, IV=K_A+ll1。
§
铁律第7条「宝塔面板不动原则」：任何时候严禁修改宝塔面板的任何代码文件（/www/server/panel/ 下的源码、前端、配置文件、数据库、模板）。仅限于通过 Web 界面管理。严禁直接编辑面板代码或操作面板 SQLite 数据库。配置修改必须通过宝塔 Web 界面或官方 API。
§
天网增强采集：Agent-Reach v1.4.0+union-search-skill(30+引擎免API)+Scrapling v0.4.8(过Cloudflare)。skill在gold-miner-sky。抖音/小红书用间接采集。
§
膏方V2数据库(PostgreSQL,gaofang_app): su - postgres -c "psql -d gaofang_v2"。路径/workspace/projects/drug-distribution-system/gaofang-v2/。核心表prescription_records(date,patient_name,age,quantity料数,status已取/已邮寄/未取/欠药/已退药,patient_phone,created_at导入时间)。import默认:状态=欠药,已传方=已传方,医助="-",电话允许空。重复prescription_id覆盖更新。date强制=date.today()(导入当日),非Excel处方日期。Gunicorn每日06:00热重启。
§
元宝（Hermes Agent）以「元宝」身份为主人效力——资深运营顾问，AI合伙人。沟通铁律：我是元宝，主人是主人，绝不混淆身份。结论先行佐证在后、克制精准。工作风格：带判断的交付、数据说话（必有环比）、沉默守护。安全红线：只读分析默认状态，写操作需明确确认。输出标准：精简格式化、数据必有趋势判断。
§
飞书 Feishu 集成已配置：App ID=cli_a93fdb2074789bc7，Secret已存。配对用户 ou_b13ee47717bdd2c2627dcdd08c8dda05（用户657799）在 FEISHU_ALLOWED_USERS。凭据备份 ~/.hermes/hermes_config/.env.backup。
§
用户飞书私聊 chat_id 为 oc_10d032f2e5b7b86d660945627d981888，所有 Cron 周报报告已改为此私聊交付（摘要消息+Word文档附件）。三份定时任务：电商周报(05:00周一)、自媒体周报(05:30周一)、CPS联盟营销周报(06:00周一)，均使用 wealth-analyst 技能，通过 md_to_feishu_docx.py 脚本发送 Word 附件。
§
飞书群「my-hermes agent」chat_id=oc_7404e0fa8470ca3e7f04d614b806fdaf。成员：①王海名 open_id=ou_19663774d0e144dffa4e16ce06e5ac22；②用户657799（主人）open_id=ou_b13ee47717bdd2c2627dcdd08c8dda05。可用飞书API查群成员/发私聊。
§
team-architect v1.0.0: 8条铁律(第8条=所有操作先请示)。影墨三大件已补齐，金脉/星光缺独立技能库待主人指示。
§
OpenViking v0.3.14已部署运行中:127.0.0.1:1933,systemd已启。Embedding=硅基流动BAAI/bge-m3(1024维),VLM=Qwen/Qwen3-8B。Hermes memory.provider=openviking。搜索引擎可检索,VL自动生成中文摘要。
§
团队架构铁律：每agent必须有三大件(SKILL+SOUL+MEMORY)+≥5条铁律+独立技能库。17个agent已全部就绪。
§
DeepSeek v4 Flash定价($/M)：缓存命中0.0028,缓存未命中0.14,输出0.28。官网比TokScale多算~36% token。费用CNY=TokScale_USD×1.36×7.14。优先用CNY报告。
§
搬砖大队全流程：编剧1200字铁律→画师通义万相768x1152→音频师情感edge-tts→导演多图切换+BGM 12首。主人说「等我通知再跑」，不能擅自跑新任务。
§
系列名是「夜伴低语」（陪伴的伴）。封面：可灵AI背景+红色大字+白色撕裂边框+黑底。视频第一帧固定封面3秒，故事名用庞门正道标题体。
§
edge_tts情感：Communicate(text,voice,rate=,pitch=) 传原生参数。映射：平静(-15%,-3Hz),恐惧(-5%,+5Hz),愤怒(+20%,+8Hz),悲伤(-20%,-5Hz)。情感版跳过后处理。
§
画师(wanx-v1): 768x1152→1080x1920, ~0.02元/张, 异步轮询。暗黑漫画风：黑白+高对比+红色点缀。带固定风格前缀。
§
hermes-online-notify.service 脚本在 /root/.hermes/scripts/hermes-online-notify.sh，发飞书"元宝已上线 🟢"。中国药典2025：官方 https://2025.chp.org.cn，蒲标网 https://db2.ouryao.com/yd2025/。查中药禁忌和用量用这两个站。主人运营广积德中医医院。
§
Nginx临时目录权限修复(2026-06-02)：/var/lib/nginx/和/var/lib/nginx/tmp/要771(o+x)让www用户遍历。已复发两次，已设cronjob默认每6小时修复（chmod 771 /var/lib/nginx /var/lib/nginx/tmp）。先手动修复后设cron。
§
主人会自己打开浏览器F12 Network面板找API请求并截图配合逆向工程，技术动手能力强。偏好直接给信息而非一步步解释。
§
Daisy Financial Research + stocks skill已装。TUSHARE_TOKEN已配。Daisy的SKILL.md已适配Hermes原生web_search/web_extract。
§
Fund pool (~/.hermes/fund_portfolio.db): 24只基金(银行主题:天弘中证银行515290/001594零分红; A500景顺长城159353/022444为推荐宽基替换标的)。膏方V2统计口径:按created_at非date,患者去重KEY=(name+age+phone),发放=status IN('已取','已邮寄'),5列输出(月份|上传患者数|上传总料数|发放患者数|发放料数)。gaofang-monthly-report skill+cron每月1日08:00推飞书。2025H1:854人/1766料,2026H1:502人/1716料。
§
DeepSeek 峰谷定价(7月中旬起)：高峰9-12点和14-18点2倍价格。所有Cron已避开高峰。主人偏好成本敏感调度，大批量任务/对话建议安排谷时(12-14点或18点后)。
§
膏方权限架构2026-08-06重构(RBAC全动态):角色=super_admin(admin)/pharmacy_admin(yaoju001/002)/leadership(GJD-A/B只读)/director(zj001全组,zj002三门店)/group_leader(店长看全店)/assistant(医助看自己)/doctor(医生只读,data:read+prescription_type:view)。5医生账号2026-08-07:yangxiangyu=杨向钰/congdonghai=丛东海/wangxiaoyong=王小勇/yumingxia=于明霞/wuruiqin=吴瑞琴,密码=用户名+123456;多医生映射表doctor_user_doctors(丛东海→崔玉华+张翠华,于明霞→蒋汶轩);医生默认只显示近90天,查询看全部。剂型/医生永久只读(任何用户含超管,view只控可见性);仅pharmacy_admin可改医助/电话/发货时间/状态/是否传方;其他只能改医助+电话;数量只读。SPECIAL_ACCOUNTS已移除,get_visible_scope()解析。skill:flask-rbac-data-scope
§
Nginx /static/ 设 expires 7d+immutable: 改静态JS/CSS后浏览器缓存7天不更新(曾致复诊页报Unexpected token和数量列空白)。绕法: common.js动态加载已加?v=Date.now(); PWA版本号?v=N需手动升; 改完静态文件提醒主人强刷。page-admin-users.js的getElementById ID须与admin-users.html一致(edit-user-*前缀)。
§
复诊窗口过滤:复诊列表只显示本月+下月上半月窗口(fu1_start≥本月1日且fu3_end≤下月15日),PC和移动端同接口生效;统计/排行接口保留全量不受影响。
§
Hermes环境(2026-08): venv已迁Python 3.12.13(SQLite 3.53.1修WAL bug, 旧venv在venv-py311-backup), rtk-rewrite插件已真正安装。升级坑: 阿里云pip镜像缺upload_date被uv exclude-newer误杀→用官方源装; 装完rm .update-incomplete标记; gateway不能内部restart(Hermes拦截), 用systemd-run独立触发或kill靠Restart=always拉起。
§
膏方网站容量(2026-08): 2核1.8G, gunicorn 4×4=16并发, 在线100-200人, 瓶颈内存,同机跑Hermes+网站+PG, 扩4G。前端坑: 登录异步拉权限被reload打断→permissions null→权限失效(已修)。