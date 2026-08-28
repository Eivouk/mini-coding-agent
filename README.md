# Mini Coding Agent

一个不使用 Agent 框架、从零实现核心循环的简化编程智能体。

## 它能做什么

用户给出编程任务后，模型可以自主选择本地工具：

- `list_files`：查看工作区文件
- `read_file`：读取 UTF-8 文本文件
- `write_file`：创建或替换文本文件
- `run_command`：运行测试或程序

程序负责维护对话、解析模型的工具调用、在本地执行工具、返回执行结果，直到模型给出最终答案或达到最大轮数。

## 安装

建议使用 Python 3.10 或更高版本：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 配置

复制配置模板，然后只在本地 `.env` 中填写 Key。`.env` 已被 Git 忽略，不会上传到仓库：

```powershell
Copy-Item .env.example .env
```

火山方舟示例配置如下：

```text
AGENT_API_KEY=你的 API Key
AGENT_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
AGENT_MODEL=deepseek-v4-flash-ga-260731
```

也可以改用系统环境变量；系统环境变量的优先级高于 `.env`。

## 运行

建议准备一个单独的演示目录，让 Agent 只在该目录工作：

```powershell
python -m mini_agent "创建一个 Python 计算器并为它编写单元测试，然后运行测试" --workspace .\demo
```

## 测试

自动测试不需要 API Key，也不会产生模型调用费用：

```powershell
python -m unittest discover -s tests -v
```

## 准备演示任务

仓库提供了一个故意带错误的计算器模板。先复制它，避免演示过程修改模板：

```powershell
Copy-Item .\demo_template .\demo_workspace -Recurse
python -m unittest discover -s .\demo_workspace -v
```

初始测试会失败。然后让 Agent 完成真实修复：

```powershell
python -m mini_agent "修复计算器的除法功能，使全部测试通过。不要修改测试文件，完成后运行测试验证。" --workspace .\demo_workspace
```

## 核心设计

`CodingAgent.run()` 是整个项目的核心。每一轮它都会：

1. 将对话和工具定义发送给模型。
2. 如果模型请求工具，解析参数并在本地执行。
3. 把工具结果加入对话，再次询问模型。
4. 如果模型不再调用工具，就把文本作为最终结果。
5. 达到最大轮数时强制停止，避免无限循环。

文件工具拒绝绝对路径和工作区外路径；命令有超时和输出长度限制，并拦截部分明显危险的命令。
