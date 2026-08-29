# Mini Coding Agent

一个不依赖 Agent 框架、自行实现核心工具循环的简化编程智能体。

## 它能做什么

用户给出编程任务后，模型可以自主选择本地工具：

- `list_files`：查看工作区文件
- `read_file`：读取 UTF-8 文本文件
- `write_file`：创建或替换文本文件
- `edit_file`：精确替换文件中唯一匹配的文本
- `run_command`：运行测试或程序

程序负责维护对话、解析模型的工具调用、在本地执行工具、返回执行结果，直到模型给出最终答案或达到最大轮数。

## 安装

建议使用 Python 3.10 或更高版本。以下命令适用于 Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 配置

复制配置模板，在本地 `.env` 中填写模型服务配置。`.env` 已加入 `.gitignore`，默认不会被 Git 跟踪；请勿强制提交：

```powershell
Copy-Item .env.example .env
```

配置项如下：

```text
AGENT_API_KEY=你的 API Key
AGENT_BASE_URL=兼容接口地址
AGENT_MODEL=支持工具调用的模型名称
AGENT_MAX_STEPS=20
```

模型服务需兼容 Chat Completions 工具调用格式。也可以使用系统环境变量，其优先级高于 `.env`。

## 测试

自动测试不需要 API Key，也不会产生模型调用费用：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 端到端示例

仓库提供一个包含已知缺陷的多文件成绩统计样例，用于复现“读取项目、分析测试、精确修改源码、运行验证”的完整过程。复制样例可以避免修改原始模板：

```powershell
Copy-Item .\demo_gradebook_template .\demo_gradebook_workspace -Recurse
.\.venv\Scripts\python.exe -m unittest discover -s .\demo_gradebook_workspace -v
```

该样例故意保留已知缺陷，因此初始三项测试中有两项失败；这不是 Agent 项目自身测试失败。运行 Agent 修复副本：

```powershell
.\.venv\Scripts\python.exe -m mini_agent "修复学生成绩统计项目，使全部测试通过。不要修改测试文件，完成后运行测试验证。" --workspace .\demo_gradebook_workspace
```

正常情况下，Agent 会读取源码与测试、精确编辑两个源码文件并主动运行测试，最终三项测试全部通过。仓库中的计算器模板仅作为更小的辅助样例保留。

## 核心设计

`CodingAgent.run()` 是整个项目的核心。每一轮它都会：

1. 将对话和工具定义发送给模型。
2. 如果模型请求工具，解析参数并在本地执行。
3. 把工具结果加入对话，再次询问模型。
4. 如果模型不再调用工具，就把文本作为最终结果。
5. 达到最大轮数时强制停止，避免无限循环。

文件工具拒绝绝对路径和工作区外路径；`edit_file` 只在旧文本恰好出现一次时修改。命令有超时和输出长度限制，并用退出码提供结构化状态，同时拦截部分明显危险的命令。

本项目是教学用途的轻量 Agent，不是操作系统沙箱。`run_command` 的当前目录被设为工作区，但进程级隔离仍应由容器或虚拟机提供。因此请只把独立、可恢复的目录交给 Agent。
