
# 百度贴吧自动签到脚本 (Baidu Tieba Auto check-in)

[![Baidu Tieba Check-in](https://github.com/twj0/baidutieba_auto-checkin/actions/workflows/main.yml/badge.svg)](https://github.com/twj0/baidutieba_auto-checkin/actions/workflows/main.yml)

这是一个利用 **GitHub Actions** 实现的百度贴吧全自动签到脚本，可以帮助你每天自动完成所有关注贴吧的签到任务，无需自己动手或部署服务器。

## ✨ 主要功能

- **✨ 自动化每日签到**：脚本默认在每天的 UTC 时间 0 点（北京时间上午 8 点）自动运行。
- **✨ 支持多账户**：可以轻松配置多个百度账户，脚本会依次为每个账户执行签到任务。
- **✨ Telegram 结果通知**：每次任务执行完毕后，会将详细的签到总结报告（成功、已签、失败列表等）发送到你的 Telegram Bot，让你对签到结果了如指掌。
- **✨ 无需服务器**：完全基于免费的 GitHub Actions 服务，你只需要拥有一个 GitHub 账户。
- **✨ 配置简单安全**：所有敏感信息（如账户 Cookie、Telegram Token）都存储在 GitHub 的加密 Secrets 中，代码中不包含任何个人隐私。

## 🚀 使用方法

请严格按照以下步骤进行配置：

### 步骤 1：Fork 本仓库

点击本页面右上角的 **Fork** 按钮，将此仓库复制到你自己的 GitHub 账户下。

### 步骤 2：配置加密机密 (Secrets)

这是最关键的一步。你需要将你的个人信息添加到仓库的加密 Secrets 中。

1.  进入你 Fork 后的仓库，点击上方的 **Settings** 标签。
2.  在左侧菜单中，依次选择 **Secrets and variables** -> **Actions**。
3.  点击右上角的 **New repository secret** 按钮，依次创建以下几个 Secret：

| Secret 名称          | 描述                                                                                                                              | 是否必须 |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| `ACCOUNTS_JSON`         | 百度账户 *Cookie* 的 **json** 格式                                       | **是**   |
| `TELEGRAM_BOT_TOKEN` | 你的 Telegram Bot 的 Token。在 Telegram 中向 [@BotFather](https://t.me/BotFather) 发送 `/newbot` 创建机器人即可获取。              | 否       |
| `TELEGRAM_CHAT_ID`   | 你的 Telegram 用户 ID。向 [@userinfobot](https://t.me/userinfobot) 发送 `/start` 即可获取你的 Chat ID。                            | 否       |

**如何获取 `ACCOUNTS_JSON`？**
1. 安装浏览器插件：[cookie editor](https://cookieeditor.org/), 插件商店直接搜索应该也可以搜到。
2. 在浏览器中登录你的[百度贴吧](https://tieba.baidu.com/)。
3. 直接点击插件图标，导出json格式就好了。
### 步骤 3：启用 GitHub Actions

Fork 后的仓库，其 Actions 默认是禁用的，需要你手动启用。

1.  进入你 Fork 后的仓库，点击上方的 **Actions** 标签。
2.  页面上会出现一个提示条，点击 **I understand my workflows, go ahead and enable them** 按钮。
3.  启用后，Actions 将会根据预设的时间表自动运行。

### 步骤 4：验证与运行

你可以通过以下两种方式验证脚本是否正常工作：

1.  **等待自动执行**：脚本默认会在每天北京时间上午 8 点运行。
2.  **手动触发执行**：
    *   在 **Actions** 页面，点击左侧的 **Daily Tieba Sign-in** 工作流。
    *   右侧会出现一个 **Run workflow** 按钮，点击它即可立即触发一次签到任务。

任务完成后，你可以点击运行记录查看详细的日志，同时你的 Telegram 也应该会收到签到总结报告。

## 🔧 自定义配置

### 修改签到时间

如果你想修改自动签到的时间，可以编辑 `.github/workflows/main.yml` 文件。

找到以下这部分代码：

```yaml
on:
  schedule:
    - cron: '0 0 * * *' # UTC 时间 0 点，即北京时间 8 点
```

`cron` 表达式使用 UTC 时间。你可以访问 [crontab.guru](https://crontab.guru/) 这个网站来轻松生成你想要的时间表达式。例如，要修改为北京时间每天凌晨 2 点（即 UTC 时间前一天的 18 点），可以改为 `cron: '0 18 * * *'`。

## 📂 文件结构

- **`main.py`**: 主签到脚本，负责所有核心逻辑。
- **`.github/workflows/main.yml`**: GitHub Actions 的配置文件，定义了任务的触发条件、运行环境和执行步骤。
- **`requirements.txt`**: Python 依赖库列表。



