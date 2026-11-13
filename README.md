# ESP32-C3 智能桌面小车

一个从硬件装配、固件烧录到 3D 接线可视化的个人全栈工程项目。以 **ESP32-C3 SuperMini** 为主控，手工搭建黄铜笼式车身，自研 Python 烧录工具与 Three.js 交互式 3D 接线场景，并用参数化 CAD 完成机身建模。

## 项目亮点

- **全流程自主完成**：器件选型、焊接装配、接线核对、固件烧录、工具开发与文档沉淀
- **自研一键烧录工具**：自动识别乐鑫 USB 端口、校验固件镜像头、调用 esptool 完成烧录，支持自检 / 擦除 / 设备监听
- **3D 接线可视化**：单文件 Three.js 应用，把 27 条接线（安全设计版 42 条）结构化，支持点击高亮、逐条核对、双视图与移动端
- **参数化机身设计**：基于 build123d 按图纸标注建模，闭合残差 0.157 mm，导出 STEP / STL 直接用于加工
- **工程化诊断能力**：通过 Windows PnP 定位 USB 枚举问题，结合 strapping 引脚约束完成低风险电气设计

## 项目结构

```
桌面机器人/
├── index.html              # Three.js 单文件 3D 接线/装配场景（约 1300 行）
├── flash_robot.py          # ESP32-C3 一键烧录 + 连接自检工具
├── flash_robot.bat         # Windows 双击入口
├── cad/
│   ├── frame.py            # build123d 参数化黄铜框架建模
│   ├── brass-frame.step    # 机身 CAD 模型（STEP）
│   ├── brass-frame.stl     # 机身 3D 打印模型（STL）
│   └── brass-frame.json    # 顶点/边长/闭合残差测量数据
├── source/                 # 原始框架尺寸图与接线图
└── HANDOFF.md              # 完整工程交接文档（接线表、诊断过程、设计决策）
```

## 硬件清单

| 模块 | 器件 |
|---|---|
| 主控 | ESP32-C3 SuperMini |
| 电机 | N20 蜗轮蜗杆减速电机 ×2（3 V / 25 rpm） |
| 传动 | 64T 钢齿轮驱动轮 ×2 |
| 电机驱动 | 双路电机驱动模块（MXD1618H） |
| 显示 | 0.96" OLED（SSD1315，I2C） |
| 音频 | MAX98357 I2S 功放 + 腔体扬声器 |
| 电源 | 18350 电芯 ×2、1S 保护板、Type-C 充电模块、P-MOS 高侧开关 |
| 机身 | 1 mm 黄铜棒笼式结构 |

## 快速开始

### 3D 接线场景

```powershell
# 单文件网页，通过本地 HTTP 服务打开
python -m http.server 8000
# 浏览器访问 http://127.0.0.1:8000/index.html
```

- 接线视图：器件摊开，点击侧栏导线逐条核对，两端显示引脚标签
- 装配视图：整机装配形态，可旋转、缩放、透明模式
- 支持 `?mode=safe` 查看低风险参考接法（42 条线）

### 固件烧录工具

```powershell
python flash_robot.py          # 自检 + 烧录
python flash_robot.py --check  # 只自检，不写入
python flash_robot.py --erase  # 烧录前全片擦除
```

工具会自动扫描乐鑫原生 USB Serial/JTAG（VID 303A），校验固件镜像 magic（`0xE9`）与 4 MB 大小后，按 DIO / 40 MHz 参数写入。

### 参数化 CAD

```powershell
pip install build123d
python cad/frame.py
```

修改 `frame.py` 顶部标注尺寸即可重新生成框架模型与测量报告。

## 技术栈

- **嵌入式**：ESP32-C3、ESP-IDF 固件、I2C / I2S、esptool
- **语言**：Python、HTML / JavaScript（Three.js）
- **CAD**：build123d（OCCT 内核）
- **工具**：Git、Windows PnP 诊断、串口调试、万用表

## 固件说明

运行固件基于第三方开源 ESP-IDF 项目（达文西 / 小水滴桌面机器人），为编译后的二进制产物，受版权与体积限制**不随本仓库分发**，可按工程文档中的版本号获取对应固件后，使用 `flash_robot.py` 烧录。仓库内代码与设计均为本人原创。

## 作者

许世杰 — 嵌入式方向本科生，求职嵌入式软件 / 研发工具类实习。
