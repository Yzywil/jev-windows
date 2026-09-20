# Jev Windows

**让 Jev 做小决策，让本地代码控制动作边界和验证结果。**

[English](README.md) · [开发计划](docs/PLAN.md) · [安全与隐私](SECURITY.md)

这是面向 Windows 的监督式桌面自动化工具，当前为 **0.1.0a1 Alpha**。
不是任意软件都能操作的通用电脑代理，也不以模型自报“完成”作为成功证据。

## 和 Jev-cu 的区别

- 为 Windows 独立实现；借鉴流程，没有复制 Jev-cu 源码。
- 复用 Windows-MCP 0.8.5 的 UI Automation 模块，不启动它的通用 MCP 服务。
- 把“控件＋动作＋调用方参数”组成完整候选，一次 Choice 选择，避免动作与控件错配。
- 指定窗口、精确控件范围、执行前刷新、一次性派发；执行结果不明时停止，不盲目重试。
- 只由本地断言判定成功；默认预览；未知或敏感操作需要逐次确认。

## 先运行不联网的示例

安装 Python 3.12+ 和 uv，在仓库目录执行：

```powershell
uv sync --locked
uv run jev-windows demo
uv run pytest
```

这是内存模拟测试，不代表真实桌面或 Jev API 测试。

## 使用 Windows 后端

```powershell
uv sync --locked --extra windows
uv run jev-windows doctor
uv run jev-windows windows
```

从列表中选择真实窗口句柄和进程名，再读取控件：

```powershell
uv run jev-windows snapshot --window 123456 --executable fixture.exe
```

根据控件的精确名称或 Automation ID 编写任务 JSON，见
[任务示例](examples/fixture-task.json) 和 [任务格式](docs/TASKS.md)。
把 `TYPESAFE_API_KEY` 安全地设置到当前终端环境；不要写入任务文件或提交到 Git。
本工具不会自动读取 `.env`。

```powershell
# 仅预览：会调用付费 API，但不执行界面动作
uv run jev-windows run --task examples/fixture-task.json --window 123456 --share-ui
# 检查任务 scope、grants 和 assertions 后执行
uv run jev-windows run --task examples/fixture-task.json --window 123456 --share-ui --execute
```

`--share-ui` 明确允许发送任务目标和候选控件的名称、ID、角色等文字到 TypeSafe。
不发送截图、整棵界面树或字段值，但控件名称和任务目标本身也可能包含私人信息。
请先用[独立测试窗口](docs/NATIVE_TEST.md)，不要拿敏感文档做实验。

## 首版范围

支持具备相应 UIA Pattern 的按钮调用、文本框赋值、选择项、复选框。
不支持任意坐标点击、画布识别、OCR、剪贴板兜底、管理员窗口、跨窗口工作流。
不同应用的 UIA 支持程度不同；[验证记录](docs/VALIDATION.md) 会区分模拟、真实桌面、
真实 Jev 测试。没有测量的数据不作为速度、费用或准确率承诺。

MIT 开源。独立社区项目，与 TypeSafe、Microsoft、OpenAI 或 Windows-MCP 无隶属关系。
