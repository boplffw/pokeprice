# 宝可梦卡价簿

自动追踪宝可梦卡牌价格，全部运行在 GitHub 上，不需要自己的电脑开着。

- **每天自动更新**：GitHub Actions 每天北京时间 22:00 从 [Pokémon TCG API](https://pokemontcg.io) 抓取 TCGplayer（美元）和 Cardmarket（欧元）价格
- **网页界面**：GitHub Pages 托管，手机电脑都能看，含走势图和涨跌幅
- **价格提醒**：触发提醒时自动开一个 Issue，GitHub 会发邮件通知你

## 一次性设置

1. **开启 Actions 写权限**：仓库 Settings → Actions → General → 最下方 Workflow permissions 选 **Read and write permissions** → Save
2. **开启网页**：Settings → Pages → Source 选 **Deploy from a branch**，Branch 选 `main`，文件夹选 `/docs` → Save。几分钟后网页地址会显示在这个页面顶部（形如 `https://你的用户名.github.io/仓库名/`）
3. **先跑一次**：Actions → 左侧「更新卡价」→ Run workflow → Run workflow
4. （可选）在 [dev.pokemontcg.io](https://dev.pokemontcg.io) 免费申请 API Key，到 Settings → Secrets and variables → Actions → New repository secret，名称填 `POKEMONTCG_API_KEY`

## 日常使用

| 想做什么 | 怎么做 |
|---|---|
| 看价格 | 打开网页 |
| 关注新卡 | 网页上搜索 → 点「关注」（会复制卡牌 ID 并打开 Actions 页面）→ Run workflow，选「关注卡牌」，粘贴 ID，可填提醒价 |
| 修改提醒 | 再次「关注卡牌」同一个 ID，填新的提醒价 |
| 取消关注 | Run workflow，选「取消关注」，填 ID |
| 立即更新 | Run workflow，保持「更新价格」 |

也可以直接在 GitHub 网页上编辑 `watchlist.json`，保存后会自动运行一次。

## 注意

- 只收录国际版（英文）卡牌，搜索请用英文卡名
- 价格数据源每天更新一次，所以一天跑一次就够了
- 只要价格还在提醒线外，每天都会开一个新的提醒 Issue；不想再收到就修改或清空提醒价
- 如果仓库长期没有活动，GitHub 可能会暂停定时任务，到 Actions 页面重新启用即可

## 文件说明

- `tracker.py`：抓取价格的脚本
- `watchlist.json`：关注列表
- `docs/index.html`：网页界面
- `docs/data.json`：历史价格数据（由 Actions 自动维护）
- `.github/workflows/update.yml`：定时任务
