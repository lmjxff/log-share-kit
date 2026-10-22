# Log Share Kit · 日志分享助手

**将本地日志整理成脱敏后的排障报告，方便发给同事、提交 GitHub Issue 或向社区提问。**

[English documentation](README.md) · [完整示例报告](examples/report.md) · [贡献指南](CONTRIBUTING.md)

这是一个完全在本地处理日志的命令行工具：隐藏常见凭据及身份信息，提取 Java 异常链，输出 Markdown、JSON 或纯文本。运行时只使用 Python 标准库，无需账号、API Key、服务端或 AI 服务。

## 适用场景

- 提问或提交工单前，先整理日志中的常见敏感信息。
- 阅读 Java 包装异常及其最深层、实际记录下来的 `Caused by`。
- 将 `Suppressed` 分支与主异常链分开，避免混淆。
- 在同一报告中用一致占位符替换相同敏感值，保留关联线索。

当前为 `0.1.0` 早期版本。脱敏基于规则，**可能漏掉敏感信息，分享前请检查报告**。最深层可见异常是日志证据，不能直接证明业务根因。

## 环境要求

- Windows、macOS 或 Linux，Python **3.10 及以上**。
- 可使用 Git 克隆源码，也可以直接从 GitHub 下载仓库 ZIP 并解压。

## 快速开始：不安装也能运行

克隆源码并运行内置的虚构示例：

```bash
git clone https://github.com/lmjxff/log-share-kit.git
cd log-share-kit
python -m logshare examples/demo.log -o report.md
```

用 Markdown 阅读器打开 `report.md` 即可。内置日志全部为虚构示例，包含一条以 `NumberFormatException` 为最深层原因的异常链、一条独立的资源关闭异常，以及后续另一条 `NullPointerException`。可直接查看[生成后的示例报告](examples/report.md)。

如果下载的是 ZIP，请跳过 `git clone` 和 `cd`，直接在解压后包含 `pyproject.toml` 的目录运行最后一条命令。

Windows 如果使用 Python Launcher，可将 `python` 替换为 `py -3`；macOS/Linux 上也可能需要使用 `python3`。

## 安装命令行入口（可选）

在下载后的源码目录执行：

```bash
python -m pip install .
logshare examples/demo.log -o installed-report.md
```

这会安装当前目录中的项目，并生成 `logshare` 命令。安装阶段可能下载构建工具，日志处理本身不联网。本版本尚未发布到 PyPI，请使用源码目录安装，不要用 `pip install log-share-kit` 代替以上命令。

建议需要隔离环境时先创建虚拟环境：

```bash
python -m venv .venv
```

PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活，macOS/Linux 使用 `source .venv/bin/activate` 激活，再执行 `python -m pip install .`。

## 命令与参数

```text
logshare INPUT [-o OUTPUT] [--format {markdown,json,text}]
         [--encoding ENCODING] [--redact-key KEY]
         [--redact-file FILE] [--force]
```

在源码目录中，以下示例的 `logshare` 均可替换为 `python -m logshare`。

| 参数 | 说明 |
| --- | --- |
| `INPUT` | 日志路径；使用 `-` 表示从标准输入读取。 |
| `-o`、`--output` | 输出到 UTF-8 文件；不指定则打印到标准输出。父目录需要预先存在。 |
| `--format markdown` | 默认格式：异常摘要、待补充问题背景和完整脱敏日志。 |
| `--format json` | 便于脚本处理的 JSON 报告，结构版本为 1。 |
| `--format text` | 仅输出脱敏日志，不包含报告框架。 |
| `--encoding` | 输入编码，默认 `utf-8-sig`，兼容有 BOM 和无 BOM 的 UTF-8。 |
| `--redact-key KEY` | 补充需要隐藏值的字段名，可重复传入。字段名按字面匹配，不区分大小写。 |
| `--redact-file FILE` | UTF-8 文本文件，每行一个额外需要隐藏的完整文本值，忽略空行。 |
| `--force` | 覆盖已存在的输出文件。仍然禁止覆盖输入日志或额外脱敏值文件，包括硬链接别名。 |
| `--version`、`--help` | 查看版本、命令帮助。 |

### 输出 JSON 或纯文本

```bash
logshare application.log --format json -o report.json
logshare application.log --format text -o sanitized.txt
```

JSON 包含 `schema_version`、`tool_version`、`line_count`、`redactions`、`exceptions` 和 `sanitized_log`。异常节点包含异常类型、脱敏后的消息、原始行号、实际记录的栈帧、原因及 Suppressed 分支；顶层事件另含 `deepest_observed_cause`。报告不保存“原始值到占位符”的映射，也不写入输入文件名。

### 从管道读取

macOS/Linux：

```bash
cat application.log | logshare - -o report.md
```

PowerShell 7 中显式使用 UTF-8 管道输出：

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
Get-Content -Raw -Encoding UTF8 .\application.log | logshare - -o report.md
```

通常直接传日志文件路径更方便，可以避开不同终端的管道编码差异。

### 处理旧编码中文日志

```bash
logshare application.log --encoding gb18030 -o report.md
```

读取采用严格解码，编码不匹配时会报错，不会静默替换乱码。输出文件始终为 UTF-8。

### 增加业务字段和额外脱敏文本

```bash
logshare application.log --redact-key tenantId --redact-key managerUuid -o report.md
logshare application.log --redact-file local.secrets -o report.md
```

例如 `local.secrets` 可以按下面的格式填写，这里仅使用虚构值：

```text
example-private-project
example-internal-host.test
```

该文件是**字面文本列表，不是正则表达式配置**；区分大小写，保留每行前后空格。真实值只放在本地未跟踪文件中。仓库的 `.gitignore` 已忽略 `*.secrets`、`.env*`、原始 `*.log` 和 `reports/`，仅显式保留虚构示例日志。不要把真实凭据直接写在命令行参数中。

## 脱敏效果与覆盖范围

```text
处理前：
email=developer@example.test password="example-only-value" peer=203.0.113.42

处理后：
email=<LSK_EMAIL_1> password="<LSK_SECRET_1>" peer=<LSK_IP_1>
```

内置规则识别：

- 常见密码、token、API Key、客户端密钥、短信验证码和票据字段。
- Bearer/Basic 鉴权值、Cookie 头及带引号的 Cookie 字段。
- JWT 形态文本、部分常见服务商 token 形态、完整 PEM 私钥块。
- URL 中的用户名和密码，例如 `scheme://user:password@host`。
- 常见邮箱、中国大陆手机号、有效 IPv4/IPv6 地址。

同一报告内，同类别的相同原始值会得到相同占位符；不同报告之间重新编号。脱敏统计表示匹配次数，不代表人数或唯一凭据数。跨行内容替换后保留换行数量，使异常行号仍对应原始日志。

## 如何阅读异常报告

每个异常事件会列出：

1. 从外层包装异常到内部原因的可见链路。
2. 最深层可见原因及该原因的第一个可见栈帧。
3. 单独展示的 `Suppressed` 分支。
4. 原始日志行号，以及报告末尾的完整脱敏日志。

工具不会执行日志里的代码，不连接数据库，也不读取项目源码。它不能自动推断“此前被吞掉的异常导致后续失败”。非堆栈行会结束当前事件，因此被截断或交错打印的堆栈可能拆成多个事件。支持类名以 `Exception`、`Error`、`Throwable` 结尾的常见 Java 异常；特殊命名和 JSON 包裹、转义后的堆栈暂不解析。非 Java 日志仍可脱敏，只是不生成 Java 异常摘要。

## 限制与数据处理

- 摘要最多收录 200 个异常头，包含原因和 Suppressed 分支。超出时 JSON 的 `summary_truncated` 为 `true`，Markdown 也会提示；完整脱敏日志仍保留。
- 每份日志输入、标准输入和额外脱敏值文件最大 **20 MiB**，大日志请先截取故障时间段。
- 日志在内存中处理，只写指定输出文件或标准输出；不包含遥测和网络客户端。
- 规则无法覆盖所有凭据、境外号码、住址、客户标识、主机名、编码数据或残缺私钥。请补充字段或字面值，并检查输出。
- 请求路径、时间戳、类名、SQL 和业务数据可能保留。生成脱敏报告不等于完全匿名，也不自动获得对外公开权限。
- 不要用 `> application.log` 将输出重定向回输入文件：终端会在程序启动前截断文件。建议使用 `-o` 获得覆盖保护。
- 退出码：`0` 成功，`2` 参数、文件、编码或大小错误，`130` 用户按键中断。错误信息避免回显原始日志字节和私有路径。

## 开发与测试

```bash
python -m unittest discover -s tests -v
python -m logshare examples/demo.log -o examples/report.md --force
```

测试覆盖脱敏遗漏、带引号的值、鉴权头、自定义规则、原始行号、主原因与 Suppressed 分支分离、UTF-8 与旧编码、标准输入、输入大小、Markdown 围栏和覆盖保护。新增用例请使用虚构数据。详见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。

## 开源许可

使用 [MIT License](LICENSE)。
