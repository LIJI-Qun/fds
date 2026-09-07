# FDS Chemistry 验证算例报告

**目录**：`F:\DESK\1FireDynamicsSimulation\SHENBBAO\Verification\Chemistry`  
**输入卡数量**：41 张 `.fds`；另有 18 组点火延迟/EDC 参考 CSV 与 Cantera 汇总数据。  
**依据**：仓库 `Manuals/FDS_Verification_Guide/FDS_Verification_Guide.tex` 中 *Ignition Delay verification with Cantera*、*Mixing with detailed chemistry*、*Combustion Load Balancing* 章节，以及目录内输入卡、化学机理库和参考 CSV。  
**运行环境**：FDS 6.10.1 Windows 可执行文件；实跑结论只代表该版本和本机编译环境。

## 1. 目录算例分类

| 类别 | 数量 | 代表输入卡 | 主要验证内容 |
|---|---:|---|---|
| 详细机理定容点火延迟 | 18 | `ign_delay_Methane_grimech30_T{900,1000,1100,1200}K_Phi{0.6,1.0,1.4}`；`ign_delay_Methane_Smooke...`；`ign_delay_Propane_USC...` | FDS 详细化学机理、CVODE、温度和 OH 演化与 Cantera 对照 |
| EDC 单 CFD 步混合-化学耦合 | 5 | `EDC_OneCFDStep_Methane_grimech30_Zeta*` | 固定混合时间、单个 CFD 步内的详细机理反应、不同初始未混合分数 |
| EDC 多 CFD 步耦合 | 5 | `EDC_MultiCFDStep_Methane_grimech30_Zeta*` | 跨多个 CFD 步的混合/化学算子、温度/OH 及元素守恒 |
| 详细机理化学负载均衡 | 2 | `EDC_load_bal_methane_smooke_serial/parallel` | 24 网格 MPI 化学负载均衡、通信等待和结果一致性 |
| 两步快速/Arrhenius 负载均衡 | 6 | `load_bal_methane_2step_fast_*`、`load_bal_propane_2step_arrhenius_*` | 6 网格串并行下的快速反应和有限速率化学负载平衡 |

这些案例不是完整火灾实验 Validation。点火延迟属于与 Cantera 的代码 Verification/交叉基准；负载均衡案例验证并行实现和性能；EDC 案例验证混合-化学耦合离散实现。

## 2. 统一物理示意图

```text
初始燃料/空气 + T0, p0
          |
          v
  +---------------------+
  | EDC 混合 (tau_mix)  |  zeta0
  +---------------------+
          |
          v
  +---------------------+
  | 详细机理 ODE/CVODE  | ---> T, OH, 物种, 元素质量
  +---------------------+
          |
   FDS 输出 <-> Cantera 基准
```

负载均衡算例在相同化学过程外增加：

```text
24 或 6 个 MPI 网格 -> 每进程 chemistry/FIRE 时间 -> 负载重分配 -> 总耗时与壁温一致性
```

## 3. 典型算例详细分析

### 3.1 `ign_delay_Methane_grimech30_T1100K_Phi1p0`

**问题描述与验证目的。** 这是定容、近似绝热、均匀甲烷/空气混合物的自燃问题，初温 1100 K、当量比 1.0、标准压力。反应由 GRI-Mech 3.0 详细机理控制，主要观察温度急升和 OH 自由基峰值。目标是验证 FDS 读取 FDS 格式详细机理、CVODE 化学积分、热化学耦合及点火延迟，而不是验证空间火焰结构。

**模型。** `&CATF` 引入 `Methane_grimech30.fds`；`&COMB ODE_SOLVER='CVODE'`，`ODE_MIN_ATOL=1e-15`、`ODE_REL_ERROR=1e-9`、`ZZ_MIN_GLOBAL=1e-15`；关闭辐射、重力、分层和噪声，`SIMULATION_MODE='DNS'`。反应物和中间基元（如 OH、H、C2H2）由机理文件定义。

**网格与计算。** 计算域为 `XB=0..1, 0..0.2, 0..1 m`，`IJK=5,1,5`，网格尺寸约 `0.2 m x 0.2 m x 0.2 m`；中部通过 `OBST`+`HOLE` 形成 0.2 m 见方的反应腔。`T_END=10 s`，时间步由 `RAMP_TIME='t'` 按 Cantera 参考时间点逐渐放大，`LOCK_TIME_STEP=T`，设备输出间隔极小以解析点火瞬态。

**边界条件。** 外部表面使用 `DEF`、`ADIABATIC=T`，辐射关闭；没有入口、出口和速度场，因而是定容均匀反应器。`HOLE` 区域初始化混合物，周围障碍物只用于包围反应区，不引入固体传热。

**工况参数。** 输入初始 `Y_O2=0.22014124`、`Y_CH4=0.05518667`，`T0=826.85°C=1100 K`，`Phi=1.0`，背景组分由机理库处理；监测 OH、温度、O2、CH4、元素 C/H/O/N、压力、比内能和全域元素质量积分。

| 项目 | 设置/判据 |
|---|---|
| 机理 | `Methane_grimech30.fds`（GRI-Mech 3.0） |
| ODE | CVODE，绝对容差 `1e-15`，相对容差 `1e-9` |
| 点火指标 | 温度快速上升、OH 增长；可用首次 `T>=1500 K` 或最大 `dT/dt` 定义 |
| 参考 | `cantera_ignition_delay.csv` 中同温度/当量比列 |

本次未直接运行该 GRI 卡的原因见第 5 节；同机理同格式的 `Methane_Smooke` 案例已运行验证流程。

### 3.2 `ign_delay_Methane_Smooke_T1100K_Phi1p0`

**问题描述与验证目的。** 与 3.1 相同的定容点火延迟框架，改用 Methane_Smooke 详细机理，用于检验不同机理文件的读取和反应速率实现。目录中的其他独立机理卡还包括 Methane_TianfengLu、Ethylene_TianfengLu、Propane_USC、Propane_Z66 和 nHeptane_Chalmers。

**模型。** CVODE 详细化学 ODE；`RADIATION=F`、绝热默认表面、`SIMULATION_MODE='DNS'`、`STRATIFICATION=F`，没有流动输运。输入卡直接跟踪 OH 和温度，参考 CSV 是 Cantera 计算结果。

**网格与计算。** `IJK=5,1,5`、`XB=0..1,0..0.2,0..1 m`，中心 0.2 m 反应区，`T_END=1 s`、`DT=1e-4 s`、`LOCK_TIME_STEP=T`；每个 CFD 步都以固定小步解析详细机理。

**边界条件。** 外壳为绝热 `DEF` 表面，辐射、重力和速度扰动关闭；无质量通量边界，故温度和组分变化完全来自定容化学反应。

**工况参数与实跑结果。** `T0=826.85°C`、`Phi=1.0`，初始化 `Y_O2=0.22014124`、`Y_CH4=0.05518667`。FDS 6.10.1 成功结束；末时刻 `T=2537.91 K`、`Y_OH=1.2982e-2`。以首次 `T>=1500 K` 定义的时间为 `0.8891 s`，配套 Cantera 数据约 `0.88998 s`，温度和 OH 曲线可逐点比较。这个结果说明机理读取、CVODE 和基本热化学耦合路径是可运行的。

### 3.3 `EDC_OneCFDStep_Methane_grimech30_taumix0p001`

**问题描述与验证目的。** 在一个 CFD 时间步内，把甲烷/空气混合与详细 GRI-Mech 3.0 化学耦合，固定 `tau_mix=0.001 s`，并改变 `Zeta`（初始未混合分数）形成 5 个工况。目标是验证 FDS EDC 的混合-化学 ODE 是否在单步中给出正确的温度、OH、元素质量和总质量。

**模型。** `INITIAL_UNMIXED_FRACTION` 表示混合前状态比例，`FIXED_MIX_TIME=0.001/0.0001/0.001/0.01/0.1 s` 为系列参数；`ODE_SOLVER='CVODE'`，高精度容差；无辐射、无重力、DNS、绝热。机理为 `Methane_grimech30.fds`。

**网格与计算。** `IJK=5,1,5`，`1 x 0.2 x 1 m` 外域；`OBST` 包围、`HOLE` 开出中心 `0.2 x 0.2 x 0.2 m` 反应区。单步案例 `T_END=0.1 s`、`DT=0.1 s`、锁定步长；通过 `WRITE_CVODE_SUBSTEPS=T` 输出化学子步。

**边界条件。** 外壳为绝热障碍物，没有入口/出口或浮力，所有变化来自局部混合和详细化学。中心初始温度按文件标题给定 900/1000/1100/1200 K 系列，`Phi=0.6/1.0/1.4` 和 `Zeta=0..1` 组合成工况矩阵。

**工况参数表。**

| 参数 | 系列值 |
|---|---|
| 初温 | 900、1000、1100、1200 K |
| 当量比 | 0.6、1.0、1.4（GRI 系列） |
| `Zeta` | 0、0.25、0.5、0.75、1.0 |
| `tau_mix` | `1e-5`、`1e-4`、`1e-3`、`1e-2`、`1e-1 s` |
| 输出 | T、OH、H、O2、CH4、C2H2、压力、C/H/O/N 元素质量、总质量 |

判据是 FDS 与 Cantera 曲线在单步时间轴上的温度/OH 一致，且 C/H/O/N 元素质量积分守恒。不同 `tau_mix` 应呈现混合时间越短、反应越快的合理趋势。

### 3.4 `EDC_MultiCFDStep_Methane_grimech30_Zeta0p5`

**问题描述与验证目的。** 该组将 EDC 详细化学耦合从单个 CFD 步扩展到 `T_END=20 s` 的多步计算，选择 `Zeta=0.5`，验证混合状态在多个 CFD 步之间传递、化学子步与主时间步衔接，以及长时间积分后的元素守恒。

**模型。** GRI-Mech 3.0 + CVODE；`INITIAL_UNMIXED_FRACTION=0.5`、`FIXED_MIX_TIME=0.01 s`、`ODE_REL_ERROR=1e-9`；`WRITE_CVODE_SUBSTEPS=T`。其余设置为 DNS、绝热、无辐射、无重力。

**网格与计算。** `IJK=5,1,5`、`1 x 0.2 x 1 m`；`T_END=20 s`、`DT=0.01 s`、锁定时间步。设备同时输出中心点和全域积分，便于区分局部化学演化与总量守恒。

**边界条件。** 反应区由障碍物/孔洞限定，外边界没有流动和换热；所有组分变化是 EDC 混合与机理反应的结果。初始中心混合物为输入卡给定的 O2/CH4 质量分数，背景气体来自 CATF 机理。

**工况参数和判据。** 系列共 5 个 `Zeta` 值（0、0.25、0.5、0.75、1.0），每个都提供 `_soln.csv`。判据包括 FDS/参考温度、OH 历程，C/H/O/N 质量积分的相对误差，以及改变 CFD 步数后最终状态的一致性。与单步案例相比，该组更能暴露算子分裂、时间步锁定和元素漂移问题。

### 3.5 `EDC_load_bal_methane_smooke_parallel/serial`：详细机理负载均衡

**问题描述与验证目的。** 三维球体绕流/火焰场中采用 Methane_Smooke 详细机理和 EDC，比较 `DO_CHEM_LOAD_BALANCE=F` 的 serial 基准与 parallel/负载均衡配置。主要验证 MPI 进程间化学工作量重分配、通信等待减少、总耗时改善，以及负载均衡前后物理结果一致。

**模型。** EDC + CVODE，`FIXED_MIX_TIME=0.01 s`，详细 Methane_Smooke 机理；`DO_CHEM_LOAD_BALANCE` 在对照卡中开关不同。辐射关闭，采用 ULMAT 压力求解器；燃烧器为甲烷质量通量边界，球体为导热固体。

**网格与计算。** 实际启用 24 网格配置：基础 `IJK=16,16,8`、子域 `2 x 2 x 1 m`，`MULT DX=2,DY=2,DZ=1,K_UPPER=5` 生成 24 个 MPI 网格，整体 `4 x 4 x 6 m`；`T_END=5 s`。输入卡还保留 1、2、6 网格注释配置，用于不同并行规模对比。

**边界条件。** XMIN/XMAX、YMIN/YMAX、ZMAX 为 OPEN，底部 burner 位于 `z=0.2..0.4 m`，甲烷 `MASS_FLUX=0.06442 kg/(m2 s)`，球体中心 `(0,0,2)`、半径 1 m、`N_LEVELS=3`，球壁材密度 100、导热 1、比热 1。

**工况参数和判据。** 背景 `N2/O2/H2O/CO2` 质量分数为 `0.762470/0.230997/0.005941/0.000591`；燃烧器表面另给 `HRRPUA=3200 kW/m2` 注释值。官方指南报告详细 Methane_Smooke 24 网格案例负载均衡约 2.2 倍加速，且三处壁温与未均衡结果一致。性能指标必须在同硬件、同 MPI 进程数和同编译选项下比较，不能仅凭单次运行时间下结论。

### 3.6 `load_bal_propane_2step_arrhenius_parallel/serial` 与 `load_bal_methane_2step_fast_*`

**问题描述与验证目的。** 这两组用同一球体火焰几何，分别测试两步丙烷 Arrhenius 和两步甲烷快速反应在 6 网格串行/并行条件下的化学负载均衡。目的不是验证化学机理本身，而是比较有限速率/快速 ODE 对 FIRE、通信和总耗时的贡献。

**模型。** 丙烷组使用两步有限速率（`A=5e2/8e3`、`E=0`、反应级数 1.75 与 CO 氧化）；甲烷组使用两步快速反应和 FDS-Euler ODE。负载均衡组设置 `DO_CHEM_LOAD_BALANCE=T`，serial 对照关闭。

**网格与计算。** 基础网格 `IJK=32,16,16`、`XB=-2..2,-2..0,0..2 m`，`MULT DY=2,DZ=2` 生成 6 个网格/进程；`T_END=5 s`，辐射和分层关闭，ULMAT 求解压力。

**边界条件。** 四个侧面和顶面 OPEN；底部 1 m² burner 甲烷或丙烷质量通量约 `0.06442/0.06355 kg/(m2 s)`；中心球体半径 1 m、导热固体表面。

**工况参数和判据。** 官方指南给出的典型趋势为：两步丙烷 Arrhenius 中 FIRE 约占总计算 20%，负载均衡加速约 1.2 倍；快速甲烷中 FIRE 占比很小，负载均衡基本没有收益。应同时比较 `*_serial` 与 `*_parallel` 的 wall temperature、HRRPUV 和总质量，确认性能变化没有改变物理结果。

## 4. 网格、边界和参数汇总表

| 算例组 | 网格与计算 | 边界条件 | 主要工况 |
|---|---|---|---|
| 定容点火延迟 | `5x1x5`，`1x0.2x1 m`，`T_END=1~10 s`，`DT=1e-4 s` 或 Cantera ramp | 绝热、无辐射、无流动 | 机理、T0、Phi 变化 |
| EDC 单步 | `5x1x5`，`T_END=0.1 s`，`DT=0.1 s`，CVODE 子步输出 | 障碍物+中心孔洞，绝热定容 | `tau_mix`、Zeta、Phi、T0 |
| EDC 多步 | `5x1x5`，`T_END=20 s`，`DT=0.01 s` | 同上 | Zeta=0~1，固定 `tau_mix=0.01 s` |
| 详细机理负载均衡 | 24 个 `16x16x8` 子网格，`4x4x6 m`，`T_END=5 s` | 五面 OPEN，球体+底部 burner | Methane_Smooke，CVODE，串/并行 |
| 两步反应负载均衡 | 6 个 `32x16x16` 子网格，`4x4x2 m` 总体，`T_END=5 s` | 五面 OPEN，球体+burner | 丙烷 Arrhenius或甲烷快速反应 |

## 5. 输入卡检查

### 5.1 已确认的问题

1. **详细机理卡的 `DEVC` 分隔符问题。** 多数 `EDC_OneCFDStep_*` 和 `EDC_MultiCFDStep_*` 中存在类似 `XYZ=... QUANTITY=...`、`SPATIAL_STATISTIC=... ID=...` 的缺逗号写法，例如 `EDC_OneCFDStep_Methane_grimech30_taumix0p001.fds` 第 32、34–38 行。FDS 6.10.1 读入 CATF 后在 `DEVC number 8` 处报 `ERROR(101)`，因此这些卡当前不能直接完成运行。建议在副本中补充逗号后重新测试；本报告没有修改原始卡。
2. **相对路径依赖。** `CATF OTHER_FILES='../../Utilities/...` 只有从 `Verification/Chemistry` 目录启动，或保持对应目录层级时才能解析。直接把卡复制到其他目录会产生 `CATF file not found`。
3. **机理库引用一致性。** 输入卡中的 `SPEC_ID='OH'`、`'H'`、`'C2H2'` 等必须存在于 CATF 机理。FDS 会对 HOCN、HNCO、NCO、AR、C3H7、C3H8、CH2CHO、CH3CHO 等无预定义物性物种给出 warning；这属于详细机理物种属性需要由机理库提供的兼容性风险，不等同于化学方程错误。
4. **`HRRPUA` 行的格式风险。** 部分负载均衡卡把 `&SURF ... / HRRPUA=3200 kJ/s/m2` 写在 namelist 终止符之后，`HRRPUA` 只会被当作注释/自由文本而不是 SURF 参数。燃料质量通量仍有效，但若希望由表面直接定义 HRR，应将 `HRRPUA` 放到 `/` 之前并使用数值单位（如 `HRRPUA=3200.`）。

### 5.2 未发现的结构性问题

- 41 张卡均有 `&HEAD` 和显式 `&TAIL`。
- 已抽查的 `CATF` 路径、`SPEC_ID`、`ELEM_ID` 和设备输出对象与对应模型一致。
- 注释中的 1/2/6 网格是负载均衡对照配置，不是同时启用的重叠网格；实际运行只启用未注释的网格。
- `Zeta`、`Phi` 和 `tau_mix` 文件名与标题/初始化参数大体一致，但批处理时仍应读取输入卡而不要只依赖文件名。

## 6. 实跑结果与复现说明

在 `Verification/Chemistry` 目录实际运行：

- `ign_delay_Methane_Smooke_T1100K_Phi1p0.fds`：成功，末温度约 2537.91 K；首次 `T>=1500 K` 为 0.8891 s，与 Cantera 约 0.88998 s。
- `EDC_OneCFDStep_Methane_grimech30_taumix0p001.fds`：读取详细机理后在 `DEVC number 8` 处失败，原因是输入卡设备参数分隔符不完整。
- `EDC_MultiCFDStep_Methane_grimech30_Zeta0p5.fds`：同类 `DEVC` 格式问题，未进入时间积分。
- `ign_delay_Methane_grimech30_T1100K_Phi1p0.fds`：同类设备格式问题，未进入时间积分。

复现命令示例：

```powershell
Set-Location 'F:\DESK\1FireDynamicsSimulation\SHENBBAO\Verification\Chemistry'
$fds='C:\Program Files\firemodels\FDS6\bin\fds.exe'
& $fds .\ign_delay_Methane_Smooke_T1100K_Phi1p0.fds
```

详细机理 EDC 卡应先在副本中修复逗号，再从上述目录运行，确保 `CATF` 相对路径有效。输出应与 `cantera_ignition_delay.csv`、各 `_soln.csv` 比较；点火延迟建议同时报告温度阈值、OH 峰值/拐点和最大温升速率，负载均衡则报告 FIRE、COMM、TOTAL 时间及壁温最大差。

