# ima_sync — IMA 巡航脚本 · 版本备份

本目录是 **IMA 巡航运行脚本的版本备份副本**（纳入 git 版本控制，防 .hermes 误删/损坏丢失）。

## 运行位 vs 备份位

| 脚本 | 运行位（cron 实际调用） | 备份位（本目录） |
|------|------------------------|------------------|
| `ima_patrol.py` | `~/.hermes/scripts/ima_patrol.py` | `ima_sync/ima_patrol.py` |
| `ima_relogin.sh` | `~/.hermes/scripts/ima_relogin.sh` | `ima_sync/ima_relogin.sh` |

## ⚠️ 使用约定

- **改代码只改运行位**（`~/.hermes/scripts/`），改完**同步 copy 一份到本目录再 commit**，保持两份一致。
- 本目录副本仅作版本归档/复盘参考，**cron 不从本目录运行**。
- 掉线排查与重登流程见主仓库设计文档 `aes_workbench_design.md` v2.23。
