# Contributing / 参与贡献

Small fixes and synthetic regression cases are welcome. Before starting a larger feature, open an issue describing the problem and a concrete example.

欢迎提交小范围修复与虚构的回归用例。较大功能请先用 Issue 描述实际问题和示例。

## Local development / 本地开发

Python 3.10+ is required. Run from the repository root:

```bash
python -m unittest discover -s tests -v
python -m logshare examples/demo.log -o examples/report.md --force
```

The runtime uses only the standard library. Keep it offline and avoid adding dependencies without a clear need. Update both README files when command behavior changes.

运行时只使用标准库，请保留本地离线处理。命令行为变化时，同步更新中英文 README。

## Regression cases / 回归用例

- Use invented values, `example.test` domains, and documentation IP addresses.
- Never submit actual logs, credentials, tokens, customer information, or private paths.
- For redaction fixes, assert that the sensitive input is absent from every output format.
- For parser fixes, cover cause chains, suppressed branches, and unrelated events.
- Explain the observable behavior before and after your change in the pull request.

- 使用虚构值、`example.test` 域名和文档用途 IP。
- 不提交真实日志、凭据、token、客户信息或私有路径。
- 脱敏修复需检查各输出格式不包含对应原始敏感值。
- 解析修复需覆盖原因链、Suppressed 分支及不同事件的边界。
- PR 中说明修改前后的实际行为。
