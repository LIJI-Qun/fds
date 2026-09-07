# FDS Fires 验证算例报告

**目录**：`F:\DESK\1FireDynamicsSimulation\SHENBBAO\Verification\Fires`  
**范围**：25 张 FDS 输入卡、配套 CSV、`couch.ssf` 和 `simple_test.ini`。  
**依据**：本目录输入卡与 CSV；`Manuals/FDS_Verification_Guide/FDS_Verification_Guide.tex` 的 constant-gamma、tunnel、温度下限、HoC 等章节。  
**重要说明**：此目录混合了严格的数值 Verification（守恒关系、几何面积积分、温度下界、热化学量）和功能/教学演示（沙发燃烧、喷雾燃烧、simple test）。后者可检查 FDS 功能链路，但没有同等强度的解析解或实验曲线，不能称为完整模型 Validation。

## 1. 算例分类

| 类别 | 数量 | 文件 | 验证/检查目标 |
|---|---:|---|---|
| 固体燃尽和几何更新 | 13 | `box_burn_away1`–`11`、`box_burn_away_2D`、`box_burn_away_2D_residue` | `BURN_AWAY`、`VARIABLE_THICKNESS`、固-气质量转移、残渣、薄板附加质量、二维处理 |
| 指定燃烧器通量/面积 | 1 | `circular_burner` | 圆形 VENT、`RADIUS`、`SPREAD_RATE` 与表面燃料质量通量的面积积分 |
| 热化学热值 | 2 | `HoC_Ideal`、`HoC_NonIdeal` | CO/soot 次要产物下 `IDEAL` 对有效燃烧热和燃料质量流率的修正 |
| 火灾能量守恒/物性 | 3 | `fire_const_gamma`、`tunnel_const_gamma`、`tunnel_linear_cp` | 恒定比热比、封闭火灾的焓/压力变化、受热一维流与温度相关比热 |
| 扩散火焰数值下界 | 3 | `tmp_lower_limit_default`、`tmp_lower_limit_dt_p001`、`tmp_lower_limit_simple` | 2D 甲烷-空气火焰中最小温度不低于环境温度及时间步敏感性 |
| 喷雾/液体燃烧器 | 1 | `spray_burner` | 拉格朗日 n-heptane 液滴、喷嘴、蒸发/燃烧、固体衬板热响应 |
| 软体家具火灾 | 1 | `couch` | 多层 upholstery 热解、`BURN_AWAY`、点火粒子与室内开口 |
| 基础火灾演示 | 1 | `simple_test` | 标准丙烷 burner、开口、温度/速度和热通量输出链路 |

## 2. 物理路径和常用判据

```text
燃料表面/固体/液滴
        |  质量通量、热解或蒸发
        v
燃料蒸气 + 氧气 --> 气相燃烧 --> HRRPUV、T、CO2、H2O、soot
        |                         |
        |                         +--> 辐射/对流到壁面
        v
守恒量：固体损失 + 燃料注入 = 气相储存 + 边界流出 + 残渣
```

对本目录的严格测试，推荐用以下量检验：

| 物理量 | 建议残差/判据 |
|---|---|
| 固体燃尽 | `m_solid(0)-m_solid(t)-m_fuel,released(t)-m_residue(t)` 接近 0 |
| 圆形燃烧器 | `mdot = MASS_FLUX x A(t)`；初始 `A=pi R^2`，再按 spread rate 更新 |
| 恒定 gamma 火灾 | FDS 的相对焓/压力与由燃料注入、生成物 cp/cv、压力功推导的解析值比较 |
| 温度下界 | `min(T_domain) >= TMPA`（数值舍入量级除外） |
| HoC | 在指定 HRR 下，`mdot_fuel=Qdot/HOC_effective`，IDEAL/NonIdeal 的比值须符合产物收率修正 |

## 3. 代表算例详细分析

### 3.1 `box_burn_away1`：三维泡沫块完全燃尽

**问题描述与验证目的。** 一个 0.4 m 立方泡沫块置于六面 1100°C 热边界中，热解为甲烷并逐步删除燃尽的固体。初始质量可直接由 `0.4^3 x 20 = 1.28 kg` 得到。该案例验证网格化实体的 `VARIABLE_THICKNESS` 与 `BURN_AWAY`、固体热解和释放燃料气体的质量积分，而非真实泡沫材料火灾。

**模型。** 一维固相导热、单步温控热解、甲烷气体释放；泡沫 `rho=20 kg/m3`、`k=0.2 W/(m K)`、`cp=1.0 kJ/(kg K)`、`HEAT_OF_REACTION=800 kJ/kg`、`REFERENCE_TEMPERATURE=200°C`，`NU_SPEC=1`。`BURN_AWAY=T` 在局部材料耗尽时去除实体面。

**网格与计算。** 基础网格 `IJK=10,10,10`、`XB=-0.3..0.7,-0.4..0.6,0..1 m`，`MULT DX=DY=1, I_UPPER=J_UPPER=1` 形成 4 个 1 m³网格，总范围 `[-0.3,1.7] x [-0.4,1.6] x [0,1] m`。`T_END=30 s`、`DT=0.01 s`；泡沫块位于 `0.3..0.7 m` 三方向，边长 0.4 m。

**边界条件。** 六个计算域外侧 VENT 都为 `HOT`，`TMP_FRONT=1100°C`，即热驱动来自辐射和表面对流耦合；没有 OPEN 排气边界。输出墙面温度、甲烷质量通量，以及 z=0.5 m 的温度、密度、甲烷质量分数切片。

**工况参数与判据。** `DEVC` 对全域 `DENSITY, SPEC_ID='METHANE'` 作体积积分，记录释放后留在气相的燃料质量。应把泡沫初始 1.28 kg 与固体表面密度积分、燃料气体累计量和可能的边界质量通量一起检查。若仅比较末时刻气相燃料质量，会遗漏燃烧或局部积累，因此必须用 `MASS_FILE`/固体质量输出建立完整平衡。

| 参数 | 值 |
|---|---|
| 泡沫几何/初始质量 | `0.4 x 0.4 x 0.4 m` / `1.28 kg` |
| 热解产物 | 100% methane (`NU_SPEC=1`) |
| 热边界 | 六面 `1100°C` |
| 计算 | 4 网格、每网格 `10^3`，30 s、0.01 s |
| 主要输出 | `Mass fuel`、质量通量、壁温、T/rho/Y_CH4 |

### 3.2 `box_burn_away10`、`box_burn_away_2D`、`box_burn_away_2D_residue`：几何、二维和残渣扩展

**问题描述与验证目的。** `box_burn_away10` 在基本块上连接 0.01 m 厚、0.6 m x 0.6 m 的平板，检查薄附着构件和实体删除的质量归属；`_2D` 使用 `IJK=10,1,10` 的单层 y 网格，检查二维等效燃尽；`_2D_residue` 让一半泡沫生成甲烷、一半生成固体残渣，检验 `NU_SPEC=0.5`、`NU_MATL=0.5` 的分流质量守恒。

**模型。** 都采用热解-固相导热-可变厚度-燃尽模型。残渣版本定义 `RESIDUE`（`rho=100 kg/m3`、`k=10 W/(m K)`、`cp=1 kJ/(kg K)`、`emissivity=1`），`STRETCH_FACTOR=1` 阻止人为几何伸缩混入质量判断。

**网格与计算。** `box_burn_away10` 的网格和时间步与基础 3D 算例相同。二维两例为 `1 x 0.4 x 1 m` 的单 y 单元域，10 x 1 x 10 网格，30 s、0.01 s。二维算法等价于在 y 方向拉伸的体积，不能把二维质量直接和三维 1.28 kg 一一比较。

**边界条件。** `_2D` 使用 `TMP_FRONT=1500°C` 的默认 HOT 边界，`_2D_residue` 为 1100°C；两者设置 `AUTO_IGNITION_TEMPERATURE=15000°C`，目的是抑制气相甲烷燃烧，只测固体到气相的质量转移。`CLIP MAXIMUM_DENSITY` 分别为 100 和 10 kg/m3，避免封闭燃料气体累积触发默认密度截断。

**工况参数及判据。** 残渣版本 `BULK_DENSITY=10 kg/m3`，固体初始可燃质量为 `10 x 0.064=0.64 kg`，理论上燃料和残渣各占 0.32 kg（需按最终残余固体和气相/释放燃料共同核验）。输出 `Mass fuel`、`Mass solid`、HRR、表面密度、燃烧速率和净热通量。该组尤其能发现 `NU_MATL`、`MATL_ID`、`BULK_DENSITY` 或二维体积缩放错误。

### 3.3 `circular_burner`：圆形燃烧器面积和燃料质量流率

**问题描述与验证目的。** 在多网格域底部定义半径 0.5 m 的圆形 propane burner，表面燃料质量通量 0.02 kg/(m2 s)，并设 `SPREAD_RATE=0.05 m/s`。该案例验证圆形 VENT 几何裁剪、面积随时间扩张及燃料质量流率，而不是验证自由火焰高度。

**模型。** Propane simple chemistry、soot yield 0.015；边界燃料质量通量经 `TAU_MF=0.01 s` 平滑建立，气相燃烧计算 HRR/烟炱。

**网格与计算。** 基础网格 `IJK=20,20,20`、`XB=-1..0,-1..0,0..1 m`，`MULT` 在 x/y/z 各复制一次，共 8 个 1 m³子域、总 `2 x 2 x 2 m`；网格约 0.05 m。`T_END=20 s`，HRR 输出间隔 0.1 s。

**边界条件。** ZMAX 与四侧 OPEN，底面只有 circular VENT。圆形切割 VENT 还给出矩形范围 `[-0.6,0.6]`、中心 `(0,0,0)`、`RADIUS=0.5 m`；不应按外接方形面积计算。

**工况参数及理论检查。** 初始圆面积 `A0=pi(0.5)^2=0.7854 m2`，初始理想燃料流量 `0.02 x A0=0.01571 kg/s`。如果扩张半径不受域/指定 VENT 裁剪限制，`R(t)=0.5+0.05t`，`mdot(t)=0.02*pi*R(t)^2`；实际后期必须按生成的 VENT 面积和网格截断判断。将 `circular_burner_hrr.csv` 的燃料质量流量、HRR 与 `circular_burner.csv` 对比是标准后处理方式。

### 3.4 `HoC_Ideal` 与 `HoC_NonIdeal`：有效燃烧热修正

**问题描述与验证目的。** 40 kW 甲烷火源采用 10% soot 和 10% CO yield，给定 50,000 kJ/kg 热值。比较 `IDEAL=.TRUE.` 与 `.FALSE.`，检查 simple chemistry 是否针对进入 CO/soot 的碳及不完全氧化产物调整有效燃烧热，进而调整为维持指定 HRR 所需的燃料通量。

**模型。** 简化一步甲烷燃烧、指定 CO/soot 收率，`REAC HEAT_OF_COMBUSTION=50000 kJ/kg`；表面以 `HRRPUA=1000 kW/m2`、面积 `0.2 x 0.2=0.04 m2` 指定火源，故总 HRR=40 kW；`TAU_Q=0.1 s` 平滑启动。

**网格与计算。** 两卡均为 `IJK=10,10,10`、`1 m³`、`T_END=4 s`。网格约 0.1 m，目标是读取质量流量而非网格收敛。

**边界条件。** 底面中心 VENT 放置 FIRE，未设置额外障碍或明确 OPEN 边界，属于局部短时热化学量测试。

**工况参数和官方预期。** `IDEAL=.FALSE.` 时，预期质量通量约 `0.0008 kg/(m2 s)`；`IDEAL=.TRUE.` 时 FDS 降低有效 HOC，预期约 `0.000877 kg/(m2 s)`。应从 HRR/MASS 输出取稳态区间并检查两者比值；不能把这两个值误用为材料热解质量通量。

### 3.5 `fire_const_gamma`：封闭火灾的焓和压力守恒

**问题描述与验证目的。** 初始 20°C 空气的 `4 x 4 x 8=128 m3` 封闭绝热箱中，底部 1 m² propane 火源以 `HRRPUA=1000 kW/m2` 燃烧 20 s，检查 `CONSTANT_SPECIFIC_HEAT_RATIO=.TRUE.` 的能量方程、燃料注入压力功、焓和压力变化。官方说明中的“1000 MW”与输入卡实际 1000 kW/m² x 1 m² 不一致，报告和复现应以输入卡为准，即 1 MW。

**模型。** constant-gamma 近似、simple propane chemistry、soot yield 0.05、辐射关闭、燃烧抑制关闭；默认表面绝热且 `emissivity=0`、`h=0`，把热损失从守恒式中隔离。

**网格与计算。** `IJK=16,16,32`，`XB=-2..2,-2..2,0..8 m`，网格 0.25 m；`T_END=30 s`、`DT=0.01 s`。火源 0–1 s 上升，1–20 s 恒定，20–21 s 关闭。

**边界条件。** 1 m²底部 VENT 为 FIRE，其他面为绝热默认 `AD`，无 OPEN 出口；故压力和总焓会在域内累积。设备输出全域相对体积积分焓 `dH_FDS` 和相对平均压力 `dP_FDS`。

**工况参数及判据。** 按 `Qdot` 时间积分得到输入能量，再扣除燃料注入/参考焓项；以 constant-gamma 下空气和产物的 cp/cv 得出预期 `Delta H`、`Delta p`。应比较 `fire_const_gamma.csv` 曲线，而不是只比单一末值；火源停止后封闭域的守恒量应保持平台。

### 3.6 `tunnel_const_gamma` 与 `tunnel_linear_cp`：受热一维流和 cp 模型

**问题描述与验证目的。** 在极细直通道中以 XMIN 1 m/s 吹入空气，在 1 mm 长局部体积施加 `HRRPUV=251330 kW/m3`，检查低马赫压力/能量方程如何把局部热释放转换为下游压力、速度、密度、温度。两个卡只改变比热假设：一个固定比热比，一个采用线性温度依赖的 `RAMP_CP`。

**模型。** DNS、无重力、无辐射、无黏性/导热（`LJ AIR` 或 `MY_AIR` 的 viscosity/conductivity=0）、绝热 free-slip 壁。`tunnel_const_gamma` 设置 `CONSTANT_SPECIFIC_HEAT_RATIO=T`；`tunnel_linear_cp` 设置为 F，并给 `CP=aT+b` 的两点 RAMP。

**网格与计算。** `IJK=100,1,4`，域 `0.1 x 0.001 x 0.004 m`，x 向 1 mm 网格；`T_END=0.2 s`。设备以 100 个点采样 x=0.0005–0.0995 m 的 p、u、rho、T，线性 cp 版额外输出 Cp。

**边界条件。** XMIN BLOW（`VEL=-1 m/s`、`TAU_V=0`），XMAX OPEN，其余绝热 free-slip；没有浮力和壁面热损失。压力容差 `1e-4`、最大压力迭代 5000，反映这是对低马赫压力闭合的严格数值测试。

**工况参数及判据。** 热源在 x=0.040–0.041 m，横截面全覆盖。const-gamma 版应与 `tunnel_const_gamma.csv` 的 x 分布对照；linear-cp 版与 `tunnel_linear_cp.csv` 对照，检查温升引起 Cp 从 1.0 至约 1.1552 kJ/(kg K) 的变化是否影响温度/速度/压力关系。

### 3.7 `tmp_lower_limit_*`：扩散火焰温度下界

**问题描述与验证目的。** 在 `0.8 x 0.2 x 1 m` 的二维甲烷-空气扩散火焰中，检查温度不会因反应、辐射损失或时间步处理而低于环境 20°C。三卡分别是显式化学计量默认时间步、显式化学计量 `DT=0.001 s` 且改气体供给/辐射收率、以及 simple chemistry。

**模型。** lumped AIR/PRODUCTS 和 M1 fuel，反应 `M1 + 9.623581 AIR -> 10.623581 PRODUCTS`；default 卡 `RADIATIVE_FRACTION=0.2365`，dt 卡设置 `RADIATIVE_FRACTION=1` 并使用 `RAMP_CHI_R`，simple 卡为简化化学。输出 `CHI_R`、`RADIATION LOSS`、温度和整个域的最小温度。

**网格与计算。** `IJK=80,1,100`，`XB=-0.4..0.4,-0.1..0.1,-0.02..0.98 m`，dx=dz=0.01 m；`T_END=1 s`，只有 `dt_p001` 指定 0.001 s 时间步。该分辨率是火焰数值稳定性测试，不能直接外推为工程火焰网格要求。

**边界条件。** 中心底部 fuel port `MASS_FLUX=0.04 kg/(m2 s)`，周围 oxidizer port 为 AIR/N2 指定通量；XMIN、XMAX、ZMIN、ZMAX OPEN，几何障碍将射流区域限定。环境 AIR 含约 40% RH 的组分。

**工况参数及判据。** 全域 `DEVC` 的 `SPATIAL_STATISTIC='MIN'` 输出 `minT` 是唯一主判据：应不低于 20°C（允许浮点舍入）。若出现低温，先分别缩小时间步、改 simple chemistry，并检查 `CHI_R` 和氧化剂 RAMP，不能直接用加热源掩盖数值问题。

### 3.8 `spray_burner`：2 MW n-heptane 喷雾燃烧器

**问题描述与验证目的。** 这是 NIST 液体燃料喷雾 burner 的功能模型：两个喷嘴向钢板围成的燃烧盘喷射 n-heptane 液滴，目标为约 2 MW 量级燃烧过程，检查 PART/PROP、液滴蒸发、燃烧、wall heat transfer 和喷嘴控制器的集成行为。它是模型演示/回归算例，不提供本目录内的解析验证曲线。

**模型。** Lagrangian `PART`，`DIAMETER=500 micron`、`HEAT_OF_COMBUSTION=44500 kJ/kg`、`SAMPLING_FACTOR=10`；喷嘴 `FLOW_RATE=1.97 kg/s`、粒子速度 10 m/s、喷射锥角 0–45°；N-heptane 一步燃烧，soot yield 0.015。钢板使用温度相关 `cp/k` RAMP，石膏板作为 25.4 mm 默认衬层。

**网格与计算。** `IJK=20,30,40`，`XB=3..5,-1.5..1.5,0..4 m`，网格 0.1 m；`T_END=90 s`，HRR 每 1 s 输出。对 500 micron 液滴而言网格不解析液滴内部，仅通过粒子传热/传质子模型处理。

**边界条件。** 五面 OPEN；燃烧盘由 3 mm steel sheet 的底板和侧板组成，默认 wall 为 gypsum board。两台控制器在 `(4,-0.3,0.5)`、`(4,0.3,0.5)` 启动 nozzle，燃料 RAMP 在 0–20 s 上升、20–40 s 保持、40–60 s 下降到零。

**工况参数及判据。** 两喷嘴总流量约 1.97 kg/s，若按 44.5 MJ/kg 完全释放，热功率上限远高于 2 MW 标题，说明 `FLOW_RATE` 很可能是每个喷嘴/模型内部采样或标题对应的实验运行模式，不能只通过输入数值直接断言 2 MW。应以 `spray_burner_hrr.csv` 实际 HRR 为准，并检查燃料 RAMP、粒子质量、CPUA/MPUA/AMPUA、壁温和能量闭合。

### 3.9 `couch` 与 `simple_test`：集成功能/教学算例

**问题描述与验证目的。** `couch` 为多层布料/泡沫沙发，使用固定高温点火粒子引燃，测试热解、材料层、燃尽、室内开口与输出；所有软包材料参数明确标注为 fabricated，不能与真实家具实验直接比较。`simple_test` 则是 60 s 丙烷 burner + 一侧开口的最小教学算例，用于 Smokeview、温度速度切片、heat-flux BND 文件等输出通路。

**模型。** couch：聚氨酯燃料，fabric/foam 单步热解、`BURN_AWAY=T`、`BACKING='VOID'`，soot yield 0.01、燃烧热 22.7 MJ/kg；点火粒子表面 1000°C。simple：propane simple chemistry、soot yield 0.01、`HRRPUA=1000 kW/m2`。

**网格与计算。** couch：基础 `25x25x24`、`2.5x2.5x2.4 m`，`MULT` 复制为 4 网格总 `5x5x2.4 m`，dx=0.1 m，`T_END=600 s`。simple：`36x24x24`、`3.6x2.4x2.4 m`，dx=0.1 m，`T_END=60 s`。

**边界条件。** couch 壁为 12 mm gypsum，底层家具结构和 upholstery 分别建模，x/y 范围内有低位 OPEN；simple 在 x=3.6 m 设置开口，其余按默认壁处理。二者都输出热通量、壁温、燃烧率或温度/HRRPUV 场。

**工况参数及判据。** 这两个是连通性/输出和教学回归案例。建议检查：是否点燃、HRR 是否随燃料耗尽衰减、燃尽后障碍是否删除、开口排烟方向是否合理、热通量和壁温文件能否在 Smokeview 打开；不应把结果报告为经过实验验证的家具 HRR 预测。

## 4. 统一网格与工况表

| 算例组 | 网格/时间 | 边界 | 关键参数 |
|---|---|---|---|
| box burn-away 3D | 4 个 `10^3`，约 2x2x1 m；30 s，0.01 s | 六面 HOT | 泡沫 20 kg/m3，0.4 m 立方，1100°C |
| box burn-away 2D/residue | `10x1x10`，1x0.4x1 m；30 s，0.01 s | 默认 HOT 封闭 | gas/residue=0.5/0.5，bulk density 10 |
| circular burner | 8 个 `20^3`，2x2x2 m；20 s | 顶部和四侧 OPEN | R=0.5 m，spread=0.05 m/s，0.02 kg/m2/s |
| HoC | `10^3`，1 m³；4 s | 底部 fire | 40 kW，CO=0.1，soot=0.1 |
| fire const-gamma | `16x16x32`，4x4x8 m；30 s，0.01 s | 封闭绝热 | 1 MW propane，20 s，constant gamma |
| tunnel | `100x1x4`，0.1x0.001x0.004 m；0.2 s | XMIN blow，XMAX OPEN | u=1 m/s，局部 251330 kW/m3 |
| temp lower limit | `80x1x100`，0.8x0.2x1 m；1 s | 燃料/氧化剂端口 + 四面 OPEN | fuel 0.04 kg/m2/s，`minT` |
| spray burner | `20x30x40`，2x3x4 m；90 s | 五面 OPEN | heptane droplets 500 um，two nozzles |
| couch | 4 个 `25x25x24`，5x5x2.4 m；600 s | 室内开口 | fabric+foam、1000°C ignitor |

## 5. 输入卡静态审查

### 确定或高风险问题

1. **`spray_burner` 标题与输入量级需要核对。** 标题称 2 MW，但 `FLOW_RATE=1.97 kg/s` 和 44.5 MJ/kg 若全燃烧对应约 87.7 MW；需确认该参数是否在两喷嘴、采样或单位转换中另有定义。后处理必须以 HRR CSV 为准，不应仅按标题引用。
2. **`fire_const_gamma` 官方文字与输入不一致。** Guide 文字为 1000 MW，但输入为 1 m² x 1000 kW/m² = 1 MW。以输入卡和输出 CSV 为计算依据，并在引用 Guide 图时注明这一差异。
3. **`box_burn_away_2D*` 的 DEVC 分隔符风格。** `SPATIAL_STATISTIC='VOLUME INTEGRAL' ID='...'` 少逗号的写法在较新严格解析版本可能产生设备解析风险；先用当前 FDS 版本试跑再决定是否修复副本。原卡不应直接修改。
4. **无 `&TAIL` 的文件。** `HoC_NonIdeal.fds`、`simple_test.fds` 在所见输入末尾没有显式 `&TAIL/`。当前 FDS 通常允许 EOF 结束，但建议新建项目时补齐，以降低老版本或审查工具的兼容性风险。
5. **二维/单层网格限制。** `box_burn_away_2D` 和 `tmp_lower_limit` 是数值特化设置；不应把其中的质量、辐射或火焰形状直接解释为三维实体火灾结果。

### 已检查的关键一致性点

- 25 张输入卡均有 `&HEAD`；`BURN_AWAY` 卡的 `MATL_ID`、`SPEC_ID`、`NU_SPEC/NU_MATL` 在抽查案例中互相匹配。
- `circular_burner` 的圆形 VENT 采用 `RADIUS` 和 `SPREAD_RATE`，不应使用外接矩形面积。
- constant-gamma 隧道例明确关闭了黏性、导热、辐射和重力，因此其基准只检查压力/能量方程，不检查真实湍流热损失。
- couch 的所有材料数据写明 fabricated；将其替换为工程材料时，必须重新校准热解、燃烧热、烟炱和 CO 收率。

## 6. 实跑与后处理建议

本轮尝试直接运行 `circular_burner` 等三维燃烧算例；其计算时间超过交互检查窗口，未把它们记作“成功实跑”。因此本报告的结果性结论来自输入卡、官方 Guide 与配套 CSV，而非伪造的本机数值。对所有正式复现，应在原目录运行，避免相对文件输出落入仓库根目录：

```powershell
Set-Location 'F:\DESK\1FireDynamicsSimulation\SHENBBAO\Verification\Fires'
$fds='C:\Program Files\firemodels\FDS6\bin\fds.exe'
& $fds .\HoC_Ideal.fds
& $fds .\tunnel_const_gamma.fds
```

建议优先实跑顺序：`HoC_Ideal/NonIdeal` → `tunnel_const_gamma/linear_cp` → `tmp_lower_limit_*` → `box_burn_away_2D_residue` → `circular_burner` → `spray_burner/couch`。每次运行后，记录 FDS 版本、CPU 数、MPI 网格分割、HRR、总质量、最小温度、以及与 CSV 的最大绝对/相对误差。对于长时三维火灾算例，还应进行网格敏感性和火焰分辨率检查，不能因本目录通过回归就省略工程验证。
