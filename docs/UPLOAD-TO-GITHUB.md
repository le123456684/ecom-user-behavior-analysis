# 上传到 GitHub · 操作清单

> 按顺序执行即可。全程约 10 分钟。
> 命令里的 `<你的用户名>` 需要替换成你自己的 GitHub 用户名。

---

## 第 0 步：准备工作（只做一次）

### 0.1 注册 GitHub 账号

如果没有账号，去 https://github.com/signup 注册。
**用户名建议**：`名字拼音+数字`，例如 `gengjiale`、`gengjiale2026`。
（不要用 `xiaoming123456` 这类，HR 看到会觉得随意）

### 0.2 安装 Git

检查是否已装：

```bash
git --version
```

若提示找不到命令，去 https://git-scm.com/download/win 下载安装，一路默认即可。

### 0.3 配置身份（只做一次，全局生效）

```bash
git config --global user.name "耿佳乐"
git config --global user.email "1926991780@qq.com"
git config --global core.quotepath false   # 让中文文件名正常显示，不转义
```

> `user.email` 建议用你 GitHub 注册邮箱，这样提交记录会正确关联到你的账号。

---

## 第 1 步：在 GitHub 上建一个空仓库

1. 打开 https://github.com/new
2. 填写：
   - **Repository name**：`ecom-user-behavior-analysis`
   - **Description**：`电商用户行为分析：漏斗 / 留存 / 类目机会点，零依赖端到端数据分析项目`
   - **Public**（必须选公开，否则 HR 打不开）
   - ❌ **不要**勾选 `Add a README file`
   - ❌ **不要**勾选 `.gitignore` 和 `license`（我们已经有了）
3. 点 **Create repository**

创建后会看到一个空仓库页面，里面有一段命令。**先别复制**，按下面第 2 步来。

---

## 第 2 步：把本地项目推上去

打开终端（Windows 用 Git Bash），进入项目目录：

```bash
cd "C:/Users/liyan/WorkBuddy/2026-09-23-15-53-35/outputs/ecom-user-behavior-analysis"
```

然后依次执行：

```bash
# ① 初始化仓库
git init

# ② 把文件加入暂存区
git add .

# ③ 看一下将要提交什么（重点确认没有 data/*.csv 和 *.db）
git status

# ④ 提交
git commit -m "feat: 电商用户行为分析项目初始化

- 30天/516,322条行为流水的端到端分析链路
- 六个分析任务：日活趋势/漏斗/路径/留存/类目机会点/加购未购买
- 零第三方依赖（Python 标准库 + SQLite），克隆即可运行
- 交付物：自包含 HTML 分析报告 + 可交互看板
- 记录4个真实口径陷阱及修正方案"

# ⑤ 关联远程仓库（替换 <你的用户名>）
git branch -M main
git remote add origin https://github.com/<你的用户名>/ecom-user-behavior-analysis.git

# ⑥ 推送
git push -u origin main
```

### 第 ⑥ 步会要求登录

**推荐方式：使用 Personal Access Token（PAT）**

1. 打开 https://github.com/settings/tokens
2. 点 **Generate new token** → **Generate new token (classic)**
3. 填写：
   - Note：`本地开发机`
   - Expiration：`90 days`
   - 勾选 **`repo`**（整个大项）
4. 点 **Generate token**，**立刻复制这串 token**（只显示一次！）
5. 推送时：
   - `Username:` 输入你的 GitHub 用户名
   - `Password:` **粘贴 token**（不是账号密码）

> ⚠️ token 等于密码，不要发给任何人，不要写进代码里。
> 提示 "Support for password authentication was removed" 就是因为你输了密码而不是 token。

---

## 第 3 步：验证上传成功

刷新仓库页面 https://github.com/<你的用户名>/ecom-user-behavior-analysis

**必须确认这几点：**

| 检查项 | 预期 |
|---|---|
| README 是否自动渲染在首页 | ✅ 应该看到标题、徽章、核心结论 |
| 文件数量 | 24 个文件 |
| `data/` 目录 | 只有 `.gitkeep`，**没有 22MB 的 CSV** |
| 是否有 `ecom.db` | ❌ 不应该有 |
| 是否有 `LICENSE` | ✅ MIT License |

---

## 第 4 步：让报告在线可看（关键一步，别跳过）

GitHub 只渲染 Markdown，**不会自动渲染 HTML**。HR 点 `report.html` 只会看到源码。
必须开启 GitHub Pages，让报告变成可点击的在线网页。

1. 进入仓库 → **Settings**（顶部导航）
2. 左侧找到 **Pages**
3. **Source** 选 `Deploy from a branch`
4. **Branch** 选 `main`，文件夹选 `/ (root)`，点 **Save**
5. 等 1–2 分钟，刷新页面，顶部会出现网址：
   `https://<你的用户名>.github.io/ecom-user-behavior-analysis/`

**然后测试这两个链接能否直接打开：**

- 分析报告：`https://<你的用户名>.github.io/ecom-user-behavior-analysis/report.html`
- 交互看板：`https://<你的用户名>.github.io/ecom-user-behavior-analysis/dashboard.html`

> 能打开就成功了。这两个链接是你可以直接写进简历、发给 HR 的。

---

## 第 5 步：回到 README，把在线链接补上

拿到 Pages 网址后，编辑 `README.md`，在最上方加一行：

```markdown
🔗 **在线预览**：[分析报告](https://<你的用户名>.github.io/ecom-user-behavior-analysis/report.html) ·
[交互看板](https://<你的用户名>.github.io/ecom-user-behavior-analysis/dashboard.html)
```

然后提交更新：

```bash
git add README.md
git commit -m "docs: 补充在线预览链接"
git push
```

---

## 第 6 步（可选，但很加分）：给 README 加截图

HR 不一定点链接，但一定会看 README 首页。放一张报告截图能显著提升印象。

1. 浏览器打开 `report.html`，截图（建议截「核心结论」那一段）
2. 图片存到项目里新建的 `docs/` 目录，命名 `report-preview.png`
3. README 里加：
   ```markdown
   ![分析报告预览](docs/report-preview.png)
   ```
4. 提交推送

---

## 常见问题

### Q1：`git push` 报 `remote origin already exists`

```bash
git remote remove origin
git remote add origin https://github.com/<你的用户名>/ecom-user-behavior-analysis.git
```

### Q2：不小心把 22MB 的 CSV 提交上去了

```bash
git rm -r --cached .
git add .
git commit -m "chore: 移除误提交的数据文件"
git push
```

`.gitignore` 已经配好了，之后不会再被加进来。

### Q3：推送后想在别的电脑继续改

```bash
git clone https://github.com/<你的用户名>/ecom-user-behavior-analysis.git
cd ecom-user-behavior-analysis
python 01_generate_data.py   # 数据文件不在仓库里，重新生成即可
```

### Q4：仓库想改名

GitHub 仓库名可以随时改（Settings → 最上方 Rename），旧链接会自动跳转。

### Q5：想让仓库更「活」一点

后续可以在 `README.md` 的「待改进」里挑一项继续做，每做一项就提交一次。
有持续提交记录的仓库，比一次性推上去更有说服力。

---

## 完成后你应该有

- ✅ 一个公开的 GitHub 仓库地址
- ✅ 两个可直接打开、可发给 HR 的在线链接（报告 + 看板）
- ✅ 一份能写进简历的项目描述（README 里的「核心结论」可直接改写）
- ✅ 对 4 个数据口径陷阱的实战理解（面试必被追问，见 README「踩坑记录」）
