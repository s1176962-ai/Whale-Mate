# Project Collaboration Guidelines

This reference is stored in docs. Its automatically discovered scope covers only docs and its subdirectories. When working across the project, explicitly read this file and the [development guide](DEVELOPMENT.md).

- Application code lives in `learning_platform/` and tests in `tests/`. Run commands from the repository root.
- Use Python 3.10+, UTF-8 and four-space indentation. Follow existing module responsibilities and Ruff configuration.
- Update relevant tests, the [specification](specification.md) and the [changelog](CHANGELOG.md) when changing behavior.
- Validate according to the change. For code changes, run `python -m unittest discover -s tests -v` and Ruff checks where needed.
- Do not commit real accounts, passwords, API keys, personal learning records, backups or local configuration. Use temporary test data.
- Keep ordinary registrations at the student role and enforce administrator permissions through the service layer.
- Store documentation in docs and archives in docs/archive. Update the index and relative links when adding or moving documents.
- Preserve existing user changes and avoid overwriting unrelated files. See the [contribution guide](CONTRIBUTING.md) for the workflow.

---

# 项目协作约定

本文件作为项目协作参考集中保存在 docs；自动发现的作用域仅覆盖 docs 及其子目录。操作整个项目时请主动阅读本文件及 [开发规范](DEVELOPMENT.md)。

- 应用代码位于 `learning_platform/`，测试位于 `tests/`；运行命令均从仓库根目录执行。
- 使用 Python 3.10+、UTF-8 和 4 空格缩进，遵循现有模块职责与 Ruff 配置。
- 修改行为时同步相关测试、[需求规格](specification.md)和[变更记录](CHANGELOG.md)。
- 按改动范围验证；代码改动运行 `python -m unittest discover -s tests -v`，必要时运行 Ruff 检查。
- 不提交真实账户、密码、API 密钥、个人学习记录、备份和本机配置；测试使用临时数据。
- 保持普通注册的 student 权限，管理员操作通过服务层权限校验。
- 文档集中保存在 docs，归档保存在 docs/archive；新增或移动文档后更新索引和相对链接。
- 保留用户现有修改，不覆盖无关文件；贡献流程见 [贡献指南](CONTRIBUTING.md)。
