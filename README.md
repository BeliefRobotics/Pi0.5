# BeliefRobotics Pi0.5 本地推理部署

Windows＋WSL2 的 Ke 版 Pi05 第 **3000 步**模型整合包，支持在另一台电脑本地安装和推理，无需开放远程连接。

**版本说明：**2026-10-27 北京时间 12:04 查询时，训练已完成 3590 步、仍在运行，最新完整 checkpoint 为 3000 步。此发布没有将未完成的训练参数冒充 4000 步模型。

## 下载与安装

从 [Release：第 3000 步 Windows 整合包](https://github.com/BeliefRobotics/Pi0.5/releases/tag/pi05-3000-windows-20261027) 下载所有 `.zip.partNNN` 分卷、`bundle-index.json` 和 `restore_bundle.ps1`，放在同一个目录。模型约 6.3 GB，采用分卷以符合 GitHub 单附件大小限制。

在该目录打开 PowerShell，运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\restore_bundle.ps1
```

脚本会校验每个分卷、合并 ZIP，再校验整包。完整解压 ZIP 后，阅读包内 `00_使用说明.md`，按顺序操作：

1. 安装 Windows NVIDIA 驱动和 WSL2 Ubuntu（首次需要管理员运行 `wsl --install -d Ubuntu-24.04`，重启并完成 Ubuntu 用户设置）。
2. 双击 **`01_install.cmd`**：校验文件，安装到 WSL 的 `~/pi05/ckpt3000`，联网下载锁定依赖。
3. 双击 **`02_start.cmd`**：等待加载和首次编译，直到显示 `READY`。
4. 双击 **`03_test.cmd`**：生成测试预测，结果保存到 `results`。
5. **`04_diagnose.cmd`** 导出环境检查；**`05_stop.cmd`** 停止本包推理进程。

也可下载本仓库源码，在仓库目录运行以下脚本，自动取得该版本的分卷并还原 ZIP：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\download_release.ps1
```

Git 仓库只保存部署代码和说明。**GitHub 的 “Source code.zip” 不含权重和 Python 运行时，不能替代 Release 整合包。**目标电脑安装时需要联网下载运行依赖；无需登录训练服务器或另行下载基础模型。

## 使用要求

- Windows x64、WSL2 Ubuntu、NVIDIA GPU。建议 **24 GB 显存、至少 32 GB 内存**，WSL 分配约 24 GB 内存。
- RTX 3090 通常是 24 GB；以 `nvidia-smi` 检测结果为准。12–16 GB 显存尚未验证，关闭预分配也不能保证能够运行。
- 建议预留约 50 GB 磁盘空间，包含下载分卷、ZIP、解压文件、WSL 模型副本及依赖缓存。
- 打包的 Python 3.11.17 已在 WSL 进行运行检查；模型原实现已在 Linux RTX 4090 24 GB 上实测，目标 Windows GPU 环境尚未做完整模型实测。

## 下发任务与接口

启动成功后，在解压目录打开 PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\send_task.ps1 -Task '抓取瓶子'
```

公开包默认使用 **合成空白图像和训练统计平均状态**，只验证加载和接口，不代表真实机器人场景或抓取效果。公开发布不含现场录制图像。

传入自己的真实观测文件：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\send_task.ps1 -Task '抓取瓶子' -ObservationFile .\my_observation.json -OutputFile .\prediction.json
```

接口为 `POST http://127.0.0.1:8796/v1/infer`，请求包含 `task` 与 `observation`。观测包含 12 维状态、头部 JPEG Base64、右腕 JPEG Base64。返回 `actions[50][12]`、生成的子任务和推理耗时。字段及关节顺序见 [完整使用说明](deploy/windows/00_使用说明.md)；运行后也可打开 `http://127.0.0.1:8796/docs`。

## 已验证与尚未完成

原实现使用已录制的真实训练样本在 RTX 4090 上验证：50×12 有限动作输出；6 次热推理的纯模型中位数约 **247 ms**，服务器本机 HTTP 调用中位数约 **297 ms**。这些不是独立测试集抓取成功率，也不是 Windows 或 3090 的实测速度。

模型使用 50 Hz 的动作时间步，50 帧覆盖 1 秒。当前约 0.3 秒的推理耗时不保证每 0.2 秒完成一次新预测。

**本包只提供推理：没有机器人运动下发、RTC 前缀引导、机械约束或独立硬件故障停止。**输出明确标记 `executed=false`、`control_ready=false`、`rtc_enabled=false`。前 10 维为绝对关节位置（rad），左夹爪为归一化开合；右夹爪是训练合成字段，不是实际右手指令。不能把预测数组未经控制层校验直接发送给机械臂。

## 来源与许可

Ke/OpenPI 源码固定在提交 `385d0e8330397ecfa29e9b675042b424c4d5386c`，原 Apache-2.0 许可证见 [UPSTREAM_LICENSE.txt](UPSTREAM_LICENSE.txt)。Python 运行时保留原许可证。第三方代码及基础模型仍适用其原有授权条款，本整合包不改变这些授权。

凭据不随仓库或整合包发布。
