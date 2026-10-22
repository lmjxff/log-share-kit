# Security / 安全说明

Log Share Kit uses best-effort pattern matching. It is not a secret scanner, compliance certification, or guarantee that output is safe to publish. Always inspect generated reports.

日志分享助手使用尽力而为的模式匹配，不能保证完整识别敏感信息。请在分享前检查生成报告。

If a rule leaks a sensitive value, reproduce it with **synthetic data**. Open an issue with the command, expected output, actual output, and Python version. Do not attach the original log or a real credential. For a vulnerability requiring private disclosure, use GitHub's private vulnerability reporting if the repository offers it; otherwise ask the maintainer for a private channel without revealing details publicly.

发现脱敏遗漏时，请用**虚构数据**复现，附上命令、期望输出、实际输出和 Python 版本，不要上传原始日志或真实凭据。需要私下披露的漏洞，如仓库提供 GitHub 私密漏洞报告入口，可使用该入口；否则先向维护者索取私密渠道，不公开漏洞细节。

If a real credential has already been published, revoke or rotate it at the issuing service. Redacting a later copy does not undo the earlier disclosure.

真实凭据已被公开时，应到签发服务撤销或轮换。后续文件脱敏不会消除此前泄露。
