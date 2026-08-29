Mini Coding Agent

一、Git仓库

https://github.com/Eivouk/mini-coding-agent

二、项目简介

本项目不依赖Agent框架，自行实现核心工具循环，维护对话历史、解析并执行工具调用，直至完成或达到轮数上限。

三、运行方法

环境要求：Python 3.10+。Windows PowerShell：

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env

在.env中填写API Key、接口地址和模型名称，准备演示工作区：

Copy-Item .\demo_gradebook_template .\demo_gradebook_workspace -Recurse
.\.venv\Scripts\python.exe -m unittest discover -s .\demo_gradebook_workspace -v

样例故意保留缺陷，初始3项测试中2项失败；Agent的19项测试均通过。运行Agent修复副本：

.\.venv\Scripts\python.exe -m mini_agent "修复学生成绩统计项目，使全部测试通过。不要修改测试文件，完成后运行测试验证。" --workspace .\demo_gradebook_workspace

离线测试：

.\.venv\Scripts\python.exe -m unittest discover -s tests -v

四、特色功能

1. Agent循环、工具解析和终止条件均自行实现。
2. 支持查看、读取、写入、精确编辑文件和执行命令。
3. edit_file仅替换唯一匹配内容，降低误改风险。
4. 命令结果结构化返回，模型可根据测试失败继续修复。
5. 文件访问限制在工作区；命令具有超时、输出截断和部分危险命令拦截。
6. 最大轮数防止无限循环，临时API故障进行有限重试。
7. 提供多文件修复演示和19项离线测试。

本项目是教学用途的轻量Agent，不是操作系统级沙箱。演示使用独立工作区，API Key仅通过未跟踪的.env或环境变量提供。
