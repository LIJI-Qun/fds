# FDS Species 验证算例报告

**目录**：`F:\DESK\1FireDynamicsSimulation\SHENBBAO\Verification\Species`  
**依据**：FDS Verification Guide 的 *Species and Combustion*、*Condensation* 章节；目录内 `.fds`、CSV 参考数据；FDS 6.10.1（本机 `fds.exe`）实跑结果。  
**范围**：本目录共 67 张输入卡。本文先按物理/数值功能分类，再选取 10 组代表算例展开。这里的“Verification”是代码与解析解、守恒式或人为构造基准的一致性检查；FED/FIC、燃烧产物和冷凝模型同时涉及工程模型能力，但本目录的测试本身不是实验 Validation。

## 1. 算例分类

| 类别 | 代表文件 | 主要检查内容 |
|---|---|---|
| 气体物性与湿度 | `species_props`、`humidity`、`favre_test` | 分子量、黏度、导热系数、比热、湿度及 Favre 平均 |
| 物种输运、通量与守恒 | `mass_balance_gas_volume`、`mass_balance_reac(_2)`、`mass_flux_comparison`、`mass_flux_wall_*` | 物种源项、边界进出通量、控制体质量平衡和符号约定 |
| 物种有界性 | `bound_test_1`、`bound_test_2` | 反应后质量分数非负、总和为 1，多反应限制反应物处理 |
| EDC/混合控制反应 | `reactionrate_EDC_*`、`reactionrate_lumped_two_air*`、`reactionrate_series_reaction` | 固定混合时间、燃料限制/氧限制、串联/并联及 lumped species |
| Arrhenius 有限速率 | `reactionrate_arrhenius_*`、`reactionrate_fast_slow` | 零阶、二阶、1.75 阶、可逆反应、Jones–Lindstedt、CVODE 对比 |
| 产物收率、化学计量和 HRRPUV | `methane_flame_*`、`propane_flame_*`、`multiple_reac_*`、`hrrpuv_reac_*`、`pvc_combustion` | simple/primitive/lumped 表示，燃料收率，各反应 HRRPUV 叠加 |
| 混合分数/火焰结构 | `burke_schumann`、`ramp_chi_r` | Burke–Schumann 混合分数、温度、焓和反应区 |
| 暴露剂量 | `FED_FIC`、`FED_FIC_SMIX`、`FED_CO_HCN`、`FED_moving` | CO/HCN/NOx/低氧/刺激性气体的 FED/FIC 及移动人员积分 |
| 气相冷凝/蒸发 | `condensation_1`、`condensation_2`、`condensation_3` | 相变质量、潜热、压力和冷凝相辐射等效性 |
| 壁面冷凝/沉积 | `wall_cond` | 固体导热、壁面冷凝热通量、沉积质量、气-固能量耦合 |

## 2. 统一判读方法与示意图

反应类算例应同时检查物种质量分数、温度、压力、反应源项及化学子步数；守恒类算例检查 `储存量 = 初始量 + 边界净通量 + 反应源项`。对每个 CSV，建议以最大绝对误差和归一化误差报告：

`epsilon_abs=max|FDS-reference|`，`epsilon_rel=max|FDS-reference|/max(|reference|,1e-12)`。

```text
初始混合物/边界通量
          |
          v
  +------------------+
  | 对流输运 + 反应  | ---> 物种源项、T、P、HRRPUV
  | (或相变/壁面沉积)|
  +------------------+
          |
   质量/能量/剂量积分
```

## 3. 代表算例详细分析

### 3.1 `species_props`：混合物气体物性

**问题与验证目的。** 定义三个虚构组分，分别给出成倍增加的分子量、黏度、导热系数和比热，在五个互不相连的小域中设置纯组分和不同体积分数混合物。该算例验证 FDS 对混合气体 `MU`、`K`、`CP` 的混合规则，而不是验证真实气体数据库。

**模型。** 理想气体物性混合；`SIMULATION_MODE='DNS'`，无反应、无流动。组分 1 作为背景气体，组分 2、3 为跟踪组分。

**网格与计算。** 5 个网格，每个 `IJK=4,1,4`，尺寸 `0.4 x 0.1 x 0.4 m`，约 0.1 m 网格；`T_END=0.02 s`、`DT=0.01 s`。计算只推进两个时间步，物性在均匀单元中应保持不变。

**边界条件。** 未设置实体障碍物和边界通量，外边界为默认开放环境；无重力、反应和辐射耦合。五个小域通过 `INIT` 独立指定组分，互不发生输运。

**工况参数。** SPEC1：`MW=10`、`mu=1e-5 kg/(m s)`、`k=0.01 W/(m K)`、`cp=1 kJ/(kg K)`；SPEC2 和 SPEC3 分别为 2 倍和 3 倍。测试状态为纯 SPEC1、纯 SPEC3、SPEC2/SPEC3 等体积分数、三组分等体积分数及 0.6/0.3/0.1 体积分数。

| 项目 | 设置/结果 |
|---|---|
| 设备 | 5 个 `VISCOSITY`、5 个 `CONDUCTIVITY`、5 个 `SPECIFIC HEAT` |
| 实跑结果 | `MU=[1e-5,3e-5,1.5857864e-5,2.1757052e-5,1.6435859e-5]`；`K` 同比例；`CP=[1,3,1.6666667,2.3326663,1.8]` |
| 判据 | 与 `species_props.csv` 各时刻一致；本次 FDS 6.10.1 正常完成 |

### 3.2 `bound_test_1` / `bound_test_2`：物种有界性修正

**问题与验证目的。** `bound_test_1` 设置两个独立反应 F1+A1→2P1、F2+A2→2P2；`bound_test_2` 增加 F1 参与的第三个反应，故同一燃料跨两个“空气组”，专门检验 boundedness correction 在竞争/共享反应物时仍不产生负质量分数。

**模型。** 冻结速度、无噪声、关闭抑制；有限步推进反应 ODE，FDS 的限制反应物和物种有界性修正算法。所有物种生成焓设为零，隔离热化学影响。

**网格与计算。** 两个算例均为 `IJK=4,1,4`、`1 x 1 x 1 m` 单域，`T_END=1 s`、`DT=0.1 s`，每 0.1 s 输出体积平均体积分数。

**边界条件。** 无障碍、无质量通量边界；`GVEC` 默认，`FREEZE_VELOCITY=.TRUE.`，因此体系仅发生局部反应，不存在输运造成的质量变化。

**工况参数。** Case 1 初始 F1=0.3、F2=0.1、A1=0.2、A2=0.4；理论上 A1 限制 R1、F2 限制 R2。Case 2 初始 F1=0.1、F2=0.4、A1=0（背景）、A2=0.2，R1 过量空气而 R2/R3 过量燃料，F1 同时参与 R1/R3。

| 检查量 | 期望/实跑末值（Case 1） |
|---|---|
| `F1,F2,A1,A2` | `0.1, 0, 0, 0.3` |
| `P1,P2` | `0.3, 0.2` |
| `SUM LUMPED MASS FRACTIONS` | 1.0，CSV 全程保持有界 |

Case 2 应重点查看 F1 在共享反应路径中的非负性和 `P1/P2/P3` 的总和；该算例不提供实验意义上的产率验证。

### 3.3 `mass_flux_comparison` 与 `mass_balance_reac`：通量和反应质量平衡

**问题与验证目的。** 前者在 1 m 高处放置表面质量通量，比较 `MASS FLUX`、`MASS FLUX WALL`、`TOTAL MASS FLUX WALL` 以及 `MASS FLUX Z` 的定义、面积积分和符号。后者用 8 个复制网格和丙烷 burner 检查反应源项、燃烧器输入和四个开放侧边界的物种通量是否闭合。

**模型。** `mass_flux_comparison` 为无反应物种 N-heptane 的定常通量；`mass_balance_reac` 为 LES、UGLMAT 压力求解器、丙烷一步燃烧（soot yield 0.015），并对 PROPANE/O2/N2/H2O/CO2/SOOT 同时积分。

**网格与计算。** `mass_flux_comparison`：`1 x 1 x 5 m`，`IJK=20,20,100`（约 0.05 m），`T_END=50 s`，极小设备输出步长用于捕捉 ramp。`mass_balance_reac`：基础网格 `5 x 5 x 5 m`、`IJK=20^3`，`MULT` 复制为 `10 x 10 x 10 m` 的 8 个网格，`T_END=20 s`、`CFL_MAX=0.5`。

**边界条件。** 通量对比算例底部 `BLOW` 速度 -1 m/s、顶部 OPEN，样品表面 `MASS_FLUX(1)=0.01 kg/(m2 s)` 按 10–30 s ramp。质量平衡算例四侧 OPEN，底部 burner 面积 `1.5 x 1.5 m`，`HRRPUA=2000 kW/m2`，0–10 s ramp；顶部未设置出口设备，侧面通量负责统计边界交换。

**工况参数和判据。** 通量对比参考 CSV 在 10–30 s 理想总质量流量约 `0.0016 kg/s`，其余时间为零；不同设备量应在符号修正后重合。质量平衡判据为全域物种质量变化与 burner 源项、边界 `TOTAL MASS FLUX WALL` 的代数和相等，`MASS_FILE=.TRUE.` 提供独立质量记录。注意 `IOR=+1/+2/-1/-2` 是按外法向定义，改符号会把正确结果误判为泄漏。

### 3.4 `reactionrate_EDC_flim_2step`：固定混合时间串联反应

**问题与验证目的。** 均匀 CH4/O2 混合物按 CH4+1.5O2→CO+2H2O、CO+0.5O2→CO2 两步反应，验证 EDC/fuel-limited 模型在固定 `tau_mix`、串联中间产物和限制反应物切换时的物种演化。

**模型。** `&COMB FIXED_MIX_TIME=0.05 s`，无限快化学由混合时间控制；关闭抑制和重力，反应源项由最小反应物浓度限制。

**网格与计算。** `IJK=4,1,4`、`0.1 x 0.025 x 0.1 m`，`T_END=1 s`、`DT=0.01 s`；体积平均输出 O2、CH4、CO、CO2、H2O。

**边界条件。** 无障碍、无入口/出口通量，`GVEC=0`，初始均匀场保持定容反应器条件；`SUPPRESSION=.FALSE.`。

**工况参数及结果。** 初始 `Y_CH4=0.1`、`Y_O2=0.8`，背景 N2。实跑 1 s：`Y_O2=0.40107365`、`Y_CH4≈2.5e-10`、`Y_CO≈1.9e-26`、`Y_CO2=0.27433137`、`Y_H2O=0.22459498`，与目录 `reactionrate_EDC_flim_2step_soln.csv` 的趋势一致。判据是反应物不为负、串联产物按时间先 CO 后 CO2、质量分数总和约为 1。

### 3.5 `reactionrate_arrhenius_1p75order_2step`：有限速率非线性 ODE

**问题与验证目的。** 以丙烷两步氧化为例，第一步总反应级数 1.75（丙烷 0.1、O2 1.65），第二步 CO 氧化含 O2、CO、H2O 三个浓度指数，检验 Arrhenius 有限速率、多反应耦合和非线性化学 ODE。

**模型。** FDS 有限速率公式 `r=A exp(-E/RT) ΠY^a`；本卡使用人为 `A=5e2/8e3`、`E=0` 的参数以便得到可重复基准，并与 `_cvode` 版本对比 ODE 求解器差异。

**网格与计算。** `IJK=8,8,8`，`0.1 m` 立方域，网格约 0.0125 m；`T_END=10 s`、`DT=0.05 s`，体积平均输出 5 个物种。

**边界条件。** `GVEC=0`、`INITIAL_UNMIXED_FRACTION=0`，无障碍、无流入流出；初始均匀混合物在定容条件下反应。

**工况参数及结果。** 初始 `Y_O2=0.219`、`Y_C3H8=0.06`、其余为 N2。10 s 实跑：`Y_O2=0.03806`、`Y_C3H8=0.00953`、`Y_CO=0.00384`、`Y_H2O=0.08248`、`Y_CO2=0.14509`。应以 `reactionrate_arrhenius_1p75order_2step_soln.csv` 做逐点误差，不把人为 A/E 当作真实燃烧机理。

### 3.6 `reactionrate_arrhenius_equilibrium`：可逆反应和平衡

**问题与验证目的。** 三个反应组成丙烷→CO→CO2 且 CO2 可逆分解的封闭体系，用于验证真实 Arrhenius 参数、可逆反应、化学平衡以及化学子步控制。

**模型。** 三步 `A/E` 分别为 `1e12/125520`、`3.4e13/167360`、`8.1e8/167360`；`MAX_CHEMISTRY_SUBSTEPS=1000`、`ODE_REL_ERROR=1e-7`，同时提供默认积分器与 CVODE 卡；关闭辐射。

**网格与计算。** `IJK=4,1,4`，`0.1 x 0.025 x 0.1 m`；`TMPA=350 K`；`T_END=4 s`、`DT=2.5e-4 s`，设备输出物种、温度、压力和化学子迭代数。

**边界条件。** 默认 LINER 表面导热系数为 0、无辐射、无重力和无流动，体系为近似绝热定容均匀反应器。

**工况参数及结果。** 初始 `Y_O2=0.218851`、`Y_C3H8=0.060321`、N2=0.720828。4 s 实跑：温度约 `2548 K`、压力约 `385.5 kPa`、`Y_C3H8≈7.4e-14`、`Y_CO2≈0.1180`、`Y_CO≈0.03984`、`Y_H2O≈0.09858`、`Y_O2≈0.02274`；化学子迭代设备末值约 5。CSV 的最终平衡组成和能量/压力变化是主要判据。

### 3.7 `methane_flame_simple` 与 primitive/lumped 对比：产物收率

**问题与验证目的。** 1 m³ 封闭空间内燃烧 100 kW 甲烷火源 5 s，指定 CO yield=0.1，记录 CO2/H2O/CO 总质量；`simple`、`primitive`、`lumped` 三种反应表示应得到相同产物质量。这是化学计量、收率映射和 lumped species 展开的直接验证。

**模型。** simple chemistry 一步反应；primitive species 显式列出反应物/产物；lumped species 通过 AIR/PRODUCTS 组合展开。均关闭 suppression，材料物性为人为值。

**网格与计算。** `IJK=10,10,20`，`1 x 1 x 2 m`（约 0.1 m）；`T_END=10 s`、`DT=0.01 s`，`MASS_FILE=.TRUE.`，0.5 s 输出。

**边界条件。** 0.4 x 0.4 m、0.1 m 高 burner obstruction，`HRRPUA=625 kW/m2`，5.0 s 熄灭；未显式设 OPEN 的外边界构成封闭腔体，便于累计全部产物。

**工况参数及判据。** 甲烷 MLR `0.002 kg/s`、总量 `0.01 kg`；理论产物为 CO2 `0.0259 kg`、H2O `0.0225 kg`、CO `0.0010 kg`。比较三个输入卡的质量积分曲线，末值误差应小于后处理允许的时间步/舍入误差。

### 3.8 `burke_schumann`：混合分数与火焰状态

**问题与验证目的。** 15 个沿 x 方向排列的 0.1 m 小网格分别初始化 0～1 的甲烷质量分数，检查 lumped AIR/PRODUCTS 的化学计量、混合分数 `Z`、温度、焓、HRRPUV 和物种分布是否符合 Burke–Schumann 预混/非预混极限关系。

**模型。** `AIR=N2+O2`、`PRODUCTS=CO2+H2O+N2`，lumped components only；一步甲烷反应，`HEAT_OF_COMBUSTION=4667.17685 kJ/kg`，`RADIATIVE_FRACTION=0`。

**网格与计算。** 每个小域 `IJK=4,4,4`，尺寸 `0.1 x 0.1 x 0.1 m`，x 方向总长约 2.9 m；`T_END=0.02 s`、`DT=0.01 s`。每个小域均输出体积平均 `T、rho、h、HRRPUV、P、Z` 及 O2/CH4/H2O/CO2/N2。

**边界条件。** `STRATIFICATION=.FALSE.`、`GVEC=0`、冻结速度、关闭辐射和 suppression；默认 LINER 仅作透明背景，避免壁面换热干扰解析化学关系。

**工况参数及判据。** x=0～2.9 m 依次采用 `Y_CH4=0,0.1,...,1.0`（输入卡末端可见 0.4～1.0 段），检查 `Z` 单调性、化学计量点附近 HRRPUV 峰值、燃料/氧气耗尽和产物生成。该算例是数值/模型关系验证，不代表有浮力火焰空间分辨率验证。

### 3.9 `FED_FIC`：毒性气体暴露积分

**问题与验证目的。** 四个 2 m³ 区域分别设置 O2/CO2/CO、窒息剂、刺激性气体及全部污染物，验证设备量 `FED`（Fractional Effective Dose）和 `FIC`（Fractional Irritant Concentration）的浓度-时间积分、CO2 过度通气因子及物种组合逻辑；`FED_FIC_SMIX` 进一步验证 SMIX/lumped 表示。

**模型。** 官方指南给出的 CO、HCN、NOx、低氧和刺激性气体经验剂量公式；输入浓度用质量分数初始化，设备按体积分数/ppm 内部换算。无燃烧、无流动，剂量随时间线性或按公式积分。

**网格与计算。** `IJK=20,5,5`，`8 x 2 x 2 m`，网格约 0.4 m；`T_END=100 s`、`DT=0.1 s`、`DT_DEVC=0.1 s`。

**边界条件。** 三个内部障碍物 `x=2,4,6 m` 将四区隔开；无质量通量和反应，外边界默认封闭/无输运，保证每个设备所在区域浓度恒定。

**工况参数及实跑结果。** 四区质量分数直接列在输入卡；例如第一域 O2/CO2/CO 为 0.10806110/0.05215865/0.00313658。100 s 实跑：`FED(O2,CO2,CO)=0.598997`、`FED(Asphyxiants)=0.972562`、`FED(Irritants)=0.008251`、`FED(All)=0.512979`；FIC 刺激性约 `0.856321`、全部约 `0.428246`。应与官方/目录参考值（约 0.5994、0.9740、0.00826、0.51369、0.8574、0.4287）按版本和舍入比较。

示意：`CO/O2/HCN/NOx/刺激性气体浓度 -> 浓度-时间积分 -> FED/FIC`。

### 3.10 `condensation_2` 与 `wall_cond`：冷凝、沉积和能量守恒

**问题与验证目的。** `condensation_2` 在低温 1 m³ 箱内使气相水雾冷凝，检查潜热、质量和压力；`wall_cond` 关闭气相成核，仅让水蒸气在固体壁面冷凝，检查壁面热传导、沉积和气-固能量耦合。

**模型。** 水蒸气作为 aerosol，分别采用平均直径 `1e-5 m` 和 `1e-6 m`；关闭沉降、热泳、重力和辐射。`wall_cond` 使用 1 mm 固体层、显式导热和表面冷凝。

**网格与计算。** `condensation_2`：`IJK=5^3`、`1 m³`、`T_END=10 s`、`DT=0.01 s`。`wall_cond`：`IJK=3^3`、`1 m³`、`T_END=20000 s`、`DT=0.5 s`，设备每 500 s 输出。

**边界条件。** `condensation_2` 默认表面温度 100°C、换热系数 0，外边界不引入流动；初始环境 `TMPA=-100°C`。`wall_cond` 外表面为默认 WALL，`TMP_INNER=20°C`、`BACKING='INSULATED'`、换热系数 10，`NUCLEATION_SITES=0` 明确禁止气相冷凝。

**工况参数及结果。** `condensation_2` 初始水蒸气质量分数 0.01，官方预期约 99.9% 冷凝、温升 36°C、压力升约 21 kPa；实跑末值温度 `36.50°C`、`Y_H2O_COND=0.009992`、压力相对值约 `21.36 kPa`。`wall_cond` 初始 `Y_H2O=0.05`，壁材 `rho=1000 kg/m³`、`k=100 W/(m K)`、`cp=1 kJ/(kg K)`；实跑约达到气/壁 `32°C`、压力降 `20.2 kPa`、壁面沉积约 `0.0108 kg`。

## 4. 输入卡静态检查与问题清单

1. **已实跑通过。** `species_props`、`bound_test_1`、`reactionrate_EDC_flim_2step`、`reactionrate_arrhenius_1p75order_2step`、`reactionrate_arrhenius_equilibrium`、`FED_FIC`、`condensation_2` 在 FDS 6.10.1 均以 `STOP: FDS completed successfully` 结束，说明当前版本语法和主要对象引用可解析。
2. **`&TAIL` 风格。** `1_step_2_step_compare.fds`、`condensation_3.fds`、`FED_moving.fds`、`multiple_reac_hrrpua.fds`、`multiple_reac_n_simple.fds`、`species_props.fds` 未显式写 `&TAIL`。FDS 当前版本允许 EOF 结束（`species_props` 已实跑通过），这属于可维护性/旧版本兼容风险，不是确定运行错误；建议复制到新项目时补齐 `&TAIL/`。
3. **物种引用。** 反应卡的 `SPEC_ID_NU`、`SPEC_ID_N_S` 与 `N_S` 长度需保持一致；已抽查的 EDC、1.75 阶和 equilibrium 卡一致。任何改名（如 `WATER VAPOR_COND`）都必须同步设备和 slice 输出。
4. **lumped species。** `AIR`、`PRODUCTS`、`SMIX` 算例依赖组成顺序和体积分数；不要把 primitive species 的质量分数直接当作 lumped species 的体积分数。`LUMPED_COMPONENT_ONLY=.TRUE.` 仅用于组件，不应误设到需独立输运的 fuel 上。
5. **质量通量符号。** `mass_balance_reac` 和 `mass_flux_comparison` 的 `IOR` 为外法向约定；跨域边界统计必须成对设置正负方向，避免把出口记为负源项。
6. **FED/FIC 单位。** 输入卡注释同时给出 mol/mol 与 g/g；FED 公式使用 ppm/体积分数。修改初始浓度时，应先完成摩尔分数到质量分数换算，并用设备输出反算确认。
7. **冷凝设置。** `DEPOSITION=.FALSE.`、`GRAVITATIONAL_SETTLING=.FALSE.`、`THERMOPHORETIC_SETTLING=.FALSE.` 是验证隔离条件，工程算例若打开这些开关，不能继续使用本报告的解析预期值。
8. **数值尺度。** equilibrium 的 `DT=2.5e-4 s`、`MAX_CHEMISTRY_SUBSTEPS=1000` 是为刚性反应服务；直接放大时间步可能得到化学子步失败或平衡偏差。LES 质量平衡算例应确保设备积分盒覆盖全部 `MULT` 网格。

## 5. 复现与后处理建议

在 Species 目录运行：

```powershell
$fds='C:\Program Files\firemodels\FDS6\bin\fds.exe'
& $fds .\species_props.fds
& $fds .\reactionrate_EDC_flim_2step.fds
```

将生成的 `*_devc.csv` 与同目录参考 CSV 或 `FDS_verification_dataplot_inputs.csv` 中的映射进行逐列比较；报告中的实跑结果是本机 6.10.1、Windows、默认编译选项下得到的代表值，换版本后应重新记录版本号、最大误差和是否出现 chemistry warning。

