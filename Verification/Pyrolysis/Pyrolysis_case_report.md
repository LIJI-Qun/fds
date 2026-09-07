# FDS Verification/Pyrolysis 算例报告

## 1. 报告范围与判读原则

本报告针对 `Verification/Pyrolysis` 目录中的 87 个 FDS 输入卡（FDS 6.10.1 验证目录版本）及其配套 CSV、材料库和《FDS Verification Guide》Pyrolysis 章节进行整理。仓库中的官方说明主要位于 `Manuals/FDS_Verification_Guide/FDS_Verification_Guide.tex` 的 `Pyrolysis` 章节；桌面上对应的 PDF 为 `F:\DESK\1FireDynamicsSimulation\SHENBBAO\FDS_Verification_Guide.pdf`。后处理映射位于 `Utilities/Matlab/FDS_verification_dataplot_inputs.csv`。

这里区分两个概念：

* **Verification（数值/方程验证）**：与解析解、守恒关系或人为构造的极限工况比较，例如质量守恒、两步反应 ODE、材料焓守恒和收缩/膨胀几何关系。
* **Validation/材料模型回归（实验对比）**：与 TGA、MCC、锥形量热等实验曲线比较。这些算例同时检查输入材料参数和 FDS 热解实现，但实验曲线本身不是解析解，不能表述为纯数学验证。

本报告是静态审查和少量可复现实跑的组合结果。已使用安装版 `C:\Program Files\firemodels\FDS6\bin\fds.exe`（FDS-6.10.1-0-g12efa16-release）成功运行：`two_step_solid_reaction.fds`、`part_baking_soda_450K.fds`、`tga_analysis.fds`、`anca-couce-fig2_10K.fds` 和 `surf_mass_vent_char_cart_fuel.fds`。其余算例的结论来自输入卡、官方指南和参考数据静态审查，未宣称已全部运行。

## 2. 目录总体分类

| 类别 | 数量 | 代表文件 | 主要被检查的内容 |
|---|---:|---|---|
| VENT 固体表面质量守恒 | 12 | `surf_mass_vent_char_*`、`surf_mass_vent_nonchar_*` | 笛卡尔/圆柱/球面、炭化/非炭化、燃料气/额外气体的质量损失 |
| PART 离散粒子质量守恒 | 13 | `surf_mass_part_*`、`surf_mass_part_specified` | 粒子几何、残余炭、指定质量通量以及粒子质量转移 |
| 多气体产物质量守恒 | 3 | `surf_mass_two_species_{cart,cyl,spher}` | 同时生成燃料和水蒸气时的总质量与各物种质量 |
| 固体粒子分解速率 | 3 | `part_baking_soda_{420,450,500}K` | 等温一阶反应和收缩体积反应的粒径解析解 |
| 材料焓/反应能量守恒 | 9 | `matl_e_cons_1` 至 `_9` | 热生成焓、反应路径、欠定/超定矩阵和最小二乘焓修正 |
| TGA/MCC/材料动力学 | 31 | `tga_*`、`cellulose_TGA_*`、`pine_wood_TGA_*`、`anca-couce-*`、`birch_*`、`cable_*` | Arrhenius 参数、升温速率、多组分木材、电缆材料、MCC HRR |
| 液体蒸发 | 5 | `surf_mass_vent_liquid_*`、`methanol_evaporation`、`liquid_mixture`、`water_pool` | 液池质量守恒、潜热、沸点、传质和非贴合网格 |
| 其他固体热解/几何/指定热释放 | 8 | `enthalpy`、`two_step_solid_reaction`、`shrink_swell`、`cell_burn_away`、`ice_cube`、`specified_hrr`、`pyrolysis_1/2` | 固相 ODE、焓、烧失、相变、收缩膨胀和指定 HRR |
| SPyro 缩放热解 | 3 | `spyro_cone_demo`、`_2`、`_3` | 锥形量热数据缩放、外部热流和厚度/时间插值 |

合计为 87 个输入卡。目录中另有 CSV 参考曲线、解析解、实验数据和外部材料库；CSV 不计入上述输入卡数量。

## 3. 共同模型与输入结构

Pyrolysis 算例共同使用 `SURF`-`MATL` 的固相传热/反应框架。`SURF` 定义厚度、几何、外部热通量、背衬、表面温度或材料组分；`MATL` 定义密度、导热系数、比热、发射率和一个或多个反应。反应可以采用 `REFERENCE_TEMPERATURE`/`REFERENCE_RATE`/`HEATING_RATE` 的 TGA 形式，也可以直接采用 Arrhenius `A`、`E`、`N_S`；产物由 `NU_SPEC`/`SPEC_ID` 和 `NU_MATL`/`MATL_ID` 指定。`SOLID_PHASE_ONLY=T` 常用于隔离固相过程，`RADIATION=F` 常用于关闭不相关的气相辐射。

气相物种在质量守恒算例中往往是人为定义的 `SPEC`，并通过极低 `Y_O2_INFTY` 或很高 `CRITICAL_FLAME_TEMPERATURE` 禁止气相燃烧；这属于机制隔离，不是实际火灾工况。TGA/MCC 算例也经常用 `TGA_ANALYSIS=T`，它是 FDS 的虚拟 TGA/材料回归功能。

## 4. 典型案例详细分析

### 4.0 典型案例参数汇总表

| 算例 | 网格与计算 | 边界条件 | 主要工况参数 |
|---|---|---|---|
| `surf_mass_vent_char_cart_fuel` | `IJK=6x6x6`，域 3x3x3 m，`T_END=200 s`，`DT=0.01 s` | 五面 `OPEN`，1 m² 底部 VENT，绝热背衬，低氧 | rho=360 kg/m3，厚度 0.01 m，炭产率 0.5，外部热流 50 kW/m2 |
| `surf_mass_part_char_spher_fuel` | `IJK=6x6x6`，3x3x3 m，`T_END=100 s`，`DT=0.01 s` | 开放环境，静止球形粒子 | r=0.01 m，rho=360 kg/m3，炭化后期望质量 7.54e-4 kg |
| `surf_mass_two_species_cart` | `IJK=4x4x4`，1 m3，`T_END=1000 s`，`DT=0.02 s` | 底部 700 K RAMP 热壁，低氧/高临界火焰温度 | 初始粒子质量 0.1 kg，燃料产率 0.032 kg、水蒸气 0.020 kg |
| `part_baking_soda_450K` | `IJK=5x5x5`，2x2x2 m，`T_END=10 s`，`DT=0.001 s` | 六面 `OPEN`，环境 450 K，等温粒子 | r0=2.5 um，rho=2200，E=103 kJ/mol，N=1 或 2/3 |
| `two_step_solid_reaction` | `IJK=3x3x4`，0.3x0.3x0.4 m，`T_END=50 s`，`DT=0.01 s` | 无外部热通量，固相专用 | Kab=0.389 s-1，Kbc=0.262 s-1，A->B->C |
| `matl_e_cons_5` | `IJK=4x4x4`，4x4x4 m，`T_END=1 s`，`DT=0.1 s` | 辐射关闭，无气相反应，三个 VENT | M1/M1a/M2，反应焓 500--1000 kJ/kg，目标焓 -1140/-640/-695 kJ/kg |
| `enthalpy` | `IJK=3x3x4`，0.3x0.3x0.4 m，`T_END=7 s`，`DT=0.005 s` | 前表面 3 kW/m2，背面环境，对流系数 0 | 1 mm 板，A 密度 30，A->B 恒速 6 kg/(m3 s)，比热 80--81 C 降阶 |
| `tga_sample` | `IJK=4x1x4`，4x1x1 m，`T_END=9600 s`，`DT=0.2 s` | 820 K 表面温度 RAMP，绝热背衬，辐射关闭 | 两组分 0.60/0.40，升温速率 5 K/min，47% 气体/53% 残余 |
| `water_pool` | `IJK=50x10x10`，5x1x1 m，`T_END=3600 s`，`DT=0.4 s` | XMIN 0.15 m/s 吹流，XMAX 开放，池面 20 C | 池 1.2x1x0.05 m，RH 25%，理论蒸发率 1.42e-5 kg/s |
| `shrink_swell` | 6 个 `IJK=3x3x4` 网格，单域 0.3x0.3x0.4 m，`T_END=15 s` | 外边界开放，样品绝热，热流 25--60 kW/m2 | 反应物/产物密度 500->1000/1125 或 1000->500/450，厚度 0.001 m |
| `spyro_cone_demo_2` | `IJK=4x1x4`，0.4x0.1x0.4 m，`T_END=600 s`，`DT=0.1 s` | 顶面开放，零对流，`SOLID_PHASE_ONLY` | 参考热流 50 kW/m2，`RAMP_EF` 每 18 s 在 10/100 切换，输出 HRRPUA |

### 4.1 `surf_mass_vent_char_cart_fuel`：VENT 笛卡尔炭化表面质量守恒

**问题描述与验证目的。** 一个 1 m² 的平面木质表面受热，初始材料密度 360 kg/m³、厚度 0.01 m，反应将一半质量留为炭（`NU_MATL=0.5`），另一半作为混合分数燃料气（`NU_SPEC=0.5`）释放。该算例是 VENT 表面质量守恒族的基准成员；同组还改变几何（圆柱、球面）、是否炭化和产物是燃料还是额外 `SPEC`。官方推导给出的炭化笛卡尔表面最终质量损失为 `rho(1-NU_RESIDUE)*A*delta=360*0.5*0.01*1=1.8 kg`，参考 CSV `surf_mass_vent_char_cart.csv` 在 110--190 s 均为 1.8 kg。

**使用模型。** 采用一维深度方向固相导热、Arrhenius 固相热解、炭残余和气体产物释放；气相反应被低氧环境隔离。`SURF BACKING='INSULATED'` 使热量不从背面散失，`EXTERNAL_FLUX` 负责加热。

**网格与计算。** 计算域为 `[-1.5,1.5] x [-1.5,1.5] x [0,3] m`，`IJK=6,6,6`，网格尺寸约 0.5 m；样品 VENT 为 `[-0.5,0.5] x [-0.5,0.5]` 的 1 m² 平面。`T_END=200 s`、`DT=0.01 s`，设备输出和 HRR 输出间隔 0.1 s，壁面输出每步累计 1 s。网格只用于解析气相控制体和表面位置，固相厚度由 `SURF THICKNESS=0.01 m` 单独表示。

**边界条件。** 五个外边界（XMIN/XMAX/YMIN/YMAX/ZMAX）为 `OPEN`，样品在底部水平 VENT 上；样品背衬绝热。`Y_O2_INFTY=1e-7`、`SOOT_YIELD=CO_YIELD=0`，燃烧实际被抑制，因此质量释放不会受到气相火焰消耗影响。

**工况参数。** 采用人为木材燃料 `WOOD`，元素式 C3.4H6.2O2.5，燃烧热 12000 kJ/kg；PINE 密度 360 kg/m³、导热系数 0.05 W/(m·K)、比热 1 kJ/(kg·K)、发射率 1，`A=1e20 1/s`、`E=1.6e5 J/mol`、炭产率 0.5、热解反应热 1000 kJ/kg，炭密度 180 kg/m³。外部热通量 50 kW/m²。

**输出与判据。** 重点输出 VENT 面积分的 `SURFACE DENSITY`、体积分的燃料密度和燃烧率时间积分；判据是总质量损失与解析值 1.8 kg 相符。实跑 `surf_mass_vent_char_cart_fuel.fds` 在 FDS 6.10.1 下正常完成；启动时仅提示自定义 `WOOD` 未使用预定义物种属性，这不影响本算例的质量守恒目标。

**同组推广。** 圆柱和球面不应复用平面质量值。官方公式分别给出炭化质量损失 0.9 kg/m²（圆柱，体积/面积为 `r/2`）和 0.6 kg/m²（球面，体积/面积为 `r/3`）；非炭化则为 1.8 和 1.2 kg/m²。`*_gas` 文件把一半产物改为显式 `SPEC`，用于验证额外物种通量。

### 4.2 `surf_mass_part_char_spher_fuel` 与 `surf_mass_part_specified`：离散粒子质量转移

**问题描述与验证目的。** 第一类为球形炭化木粒子，验证 Lagrangian 粒子从固相转化为炭和燃料气时，粒子初始/最终质量是否与几何体积和残余率一致。官方给出的球形炭化粒子期望质量为 `360*0.5*(4*pi*r^3/3)=7.54e-4 kg`，其中 `r=0.01 m`。第二类 `surf_mass_part_specified` 不反应，而给平板、圆柱和球形粒子指定恒定 `MASS_FLUX`，用于验证指定质量通量的积分。

**使用模型。** 使用 `PART`、`INIT`、`SURF GEOMETRY='CARTESIAN'/'CYLINDRICAL'/'SPHERICAL'`，并输出 `MPUV`、物种体积分密度和粒子质量。炭化模型使用 `NU_MATL` 和 `NU_SPEC`；指定通量模型使用 `SPEC_ID`、`MASS_FLUX`、`TAU_MF`，不依赖 Arrhenius 反应。

**网格与计算。** 炭化球案例域为 `3 x 3 x 3 m`（`IJK=6,6,6`，约 0.5 m 网格），`T_END=100 s`、`DT=0.01 s`；一个 `STATIC=.TRUE.` 的粒子通过 `INIT` 放在 1.5 m 高度附近。指定通量案例域为 `[-1.5,1.5] x [-1.5,1.5] x [0,3] m`、`IJK=6,6,6`，`T_END=20 s`、`DT=0.01 s`，三个粒子分别位于 x=-1、0、1 m。

**边界条件。** 质量守恒粒子案例使用低氧 `Y_O2_INFTY=1e-7`、无湿度和高临界火焰温度，所有外边界开口。粒子本身为静止粒子，几何尺寸由 `THICKNESS`、`LENGTH`、`WIDTH` 或 `RADIUS` 给定；指定通量案例只定义物种释放，不施加受热边界。

**工况参数。** 炭化粒子与 VENT 族采用 PINE 密度 360 kg/m³、初始半径 0.01 m、炭产率 0.5；指定通量案例中平板厚度 0.01 m、长宽 0.05 m、`ARGON` 通量 0.05 kg/(m²·s)，圆柱 `SO2` 通量 0.1，球形 `HELIUM` 通量 0.1，均采用 `TAU_MF=0.001 s`。

**输出与判据。** 比较粒子质量或 `MPUV` 体积分与官方 CSV 的 0.009 kg（炭化平板）、0.00565 kg（炭化圆柱）和 7.54e-4 kg（炭化球）等值；指定通量则检查物种质量随时间的线性积分。该组尤其适合检查粒子几何和质量归属，不能用普通 VENT 面积公式替代。

### 4.3 `surf_mass_two_species_cart`：同时生成燃料气和水蒸气

**问题描述与验证目的。** 单位立方体中放置总质量约 0.1 kg 的平板型粒子，固体组分 80%，水分 20%；热解后固体产生燃料气和水蒸气。官方 CSV 在 800--1000 s 给出燃料 0.032 kg、水 0.020 kg、总释放 0.048 kg。算例验证多物种产物的质量分配、粒子剩余质量和气相积分是否同时守恒；圆柱和球形版本只改变粒子几何。

**使用模型。** `SOLID` 采用 `NU_SPEC=0.4` 的燃料气产率和 `NU_MATL=0.6` 的 CHAR 产率；`MOISTURE` 采用 `NU_SPEC=1` 的水蒸气蒸发。粒子用 `STATIC=.TRUE.`，热源通过底部 `HOT WALL` 的升温 RAMP 给出。

**网格与计算。** 域为 1 m³、`IJK=4,4,4`（0.25 m 网格），`T_END=1000 s`、`DT=0.02 s`；一个粒子覆盖单位立方体，通过 `MASS_PER_VOLUME=0.1` 设置总质量。输出设备每 0.1 s 左右记录燃料气、水蒸气、固体粒子质量。

**边界条件。** `HOT WALL` 的 `TMP_FRONT` 从 0 K 线性升至 700 K；其余边界默认为开放/环境条件。`Y_O2_INFTY=1e-7`、`Y_CO2_INFTY=0`、湿度为 0，并将 `CRITICAL_FLAME_TEMPERATURE=2000 K`，目的是禁用气相燃烧。

**工况参数。** SOLID 密度 500 kg/m³、导热系数 0.2、比热 1.0，参考温度 200 K，燃料气质量分数 0.4，热解热 1000 kJ/kg；MOISTURE 密度 1000、比热 4.184、参考温度 100 K、热解热 2500 kJ/kg；表面厚度 0.0002 m，平板长度/宽度 0.001 m。

**输出与判据。** 设备 `fuel gas mass`、`water vapor mass` 和 `solid mass` 必须满足组分产率与总质量闭合；还输出粒子/壁面温度。该算例比单一气体案例更能暴露 `SPEC_ID`、`NU_SPEC` 与质量积分的错误。

### 4.4 `part_baking_soda_450K`：等温球形粒子分解解析解

**问题描述与验证目的。** 该算例对直径 5 μm 的 NaHCO3 球形粒子施加 450 K 等温环境，比较两种固相反应形式：一阶反应和收缩体积（contracting-volume）反应。官方解析式为一阶模型 `m/m0=exp(-kt)`、`r^3=r0^3 exp(-kt)`；收缩体积模型满足 `r=r0(1-kt)`。FDS 通过固定几何体积并设置 `ALLOW_SHRINKING=F`、反应级数 `N_S=2/3` 和调整后的 `A=133e11` 来重现收缩体积的质量衰减。

**使用模型。** `SOLID_PHASE_ONLY=T`，不求解气相燃烧；固相反应采用 Arrhenius `A=3.4e11 1/s`、`E=103000 J/mol`、`N_S=1`（一阶）或 `A=133e11`、`N_S=0.667`（收缩体积等效形式）。产物是 0.461 水蒸气和 0.539 二氧化碳，反应热为 0。

**网格与计算。** 域为 `[-1,1] x [-1,1] x [0,2] m`，`IJK=5,5,5`（0.4 m 网格）；两个静止粒子放在 `(0,0,1)` 附近，`T_END=10 s`、`DT=0.001 s`、壁面输出每 1 s。宏观网格远大于微米粒子，这是点粒子固相 ODE 测试，不是解析粒子内部温度场的空间分辨率测试。

**边界条件。** 六个外表面均为 `OPEN`；`TMPA=177 °C`（约 450 K），两个粒子表面使用 `TMP_INNER=177`，因此粒子等温。`SOLID_PHASE_ONLY=T` 将气相输运和燃烧从目标中剥离。

**工况参数。** 初始密度 2200 kg/m³、半径 2.5 μm、导热系数 0.2、比热 1.0、发射率 0.8；反应活化能 103 kJ/mol。输出一阶粒子的壁厚换算直径、内部温度和固体密度；球形粒子同样输出，并用控制器 `MY POWER` 将 `rho_s^(1/3)` 转换为等效直径。

**输出与判据。** `part_baking_soda_450K.csv` 和后处理配置比较一阶、球形解析直径与 FDS 的 `diam first-order`、`SPHERE DIA`，允许误差约 5%。已实跑该卡，FDS 6.10.1 正常完成；但输入卡末尾的 `SPHERE DIA` 设备存在重复关键字问题，详见第 5 节。

### 4.5 `two_step_solid_reaction`：两步固相 ODE

**问题描述与验证目的。** 初始固体全为 A，按 A→B→C 两步反应分解，常数反应率为 `K_ab=0.389 s^-1`、`K_bc=0.262 s^-1`。输入卡本身附有解析解：`Ya=exp(-Kab t)`，`Yb=Kab/(Kbc-Kab)[exp(-Kab t)-exp(-Kbc t)]`，`Yc` 为剩余积分项。此算例直接验证 FDS 固相反应 ODE 求解器、连续产物传递和质量分数随时间的演化。

**使用模型。** `SOLID_PHASE_ONLY=T`，`E=0`，因此 `A` 直接等于反应率；每个材料密度 1 kg/m³、导热系数 0.1、比热 1.0。A 的反应生成 B，B 的反应生成 C，C 为惰性终产物。没有气体反应或辐射耦合。

**网格与计算。** 域为 `[-0.15,0.15] x [-0.15,0.15] x [0,0.4] m`，`IJK=3,3,4`；样品 VENT 为底面中心 `0.1 x 0.1 m`，表面厚度 0.001 m。`T_END=50 s`、`DT=0.01 s`，`NFRAMES=200`，设备在表面内部深度 0.0001 m 读取三种材料的 `SOLID DENSITY`。

**边界条件。** 未定义外部开口和热通量，反应速率通过 `E=0` 与 `SOLID_PHASE_ONLY` 隔离；`STRETCH_FACTOR=1`，不发生几何变化。`BNDF WALL TEMPERATURE` 仅用于确认温度场没有意外耦合。

**工况参数。** `MAT_A`、`MAT_B`、`MAT_C` 初始密度均 1，反应参数分别为 0.389 和 0.262 s^-1；初始质量分数 Ya=1、Yb=Yc=0。理论上任意时刻 `Ya+Yb+Yc=1`。

**输出与判据。** 对 `Ya`、`Yb`、`Yc` 设备曲线与 `two_step_solid_reaction.csv` 对照，重点检查峰值时刻、长时间趋近 C 和总和为 1。已实跑成功，FDS 输出正常结束；该结果只说明输入能被当前版本正确解析和完成，数值误差仍应由后处理曲线/误差范数计算。

### 4.6 `matl_e_cons_5`：多材料、多反应焓守恒

**问题描述与验证目的。** `matl_e_cons_1`--`9` 是人为构造的 1 m 级立方体材料焓守恒组。每个材料通过一个 VENT 放置约 1 kg，输出 `WALL ENTHALPY`，将反应热、物种生成焓、材料比热和材料间反应路径组合起来。案例 5 在案例 4 的基础上增加一个相变路径，形成三个材料和四个反应，属于超定但路径总焓相容的系统；理论上应得到精确解。

**使用模型。** `M1` 有两步反应：直接生成 `S1`/`M2`，以及生成 `M1a`；`M1a` 再生成 `S1`/`M2`；`M2` 最终生成 `S1`。材料和物种密度/分子量被人为设为便于手算的数值，反应焓由 `HEAT_OF_REACTION`、参考温度和热解范围构造。`matl_e_cons_5.csv` 的初始期望焓为 M1=-1140、M1 相变材料=-640、M2=-695 kJ/kg。

**网格与计算。** 域为 `0--4 m` 的立方体，`IJK=4,4,4`（每个单元 1 m），`T_END=1 s`、`DT=0.1 s`；底面布置三个 1 m² 的 VENT，分别对应 M1、M1a 和 M2，表面厚度 0.001 m。每个设备在各 VENT 中心读取 `WALL ENTHALPY`。

**边界条件。** `RADIATION=F`，没有外部热通量或气相反应，所有能量变化来自材料焓定义和反应矩阵。气体 S1 的分子量 1000 g/mol、形成焓 0 kJ/mol、比热 1 kJ/(kg·K)。

**工况参数。** M1 密度 1000、比热 0.5、两反应热分别 1000 和 500 kJ/kg；M1a 密度 1000、比热 0.5、反应热 500；M2 密度 1000、比热 1.5、反应热 500；反应参考温度为 280--400 °C，热解范围 40--60 K。

**输出与判据。** 比较 `H_M1`、`H_M1a`、`H_M2` 与 CSV/指南手算值，官方材料焓组的目标容差约 0.5%。该组不是普通“火焰 HRR”测试，而是检查 FDS 为反应体系求解材料焓修正的线性代数过程。静态检查发现该文件若干 namelist 行末带逗号，当前版本仍需以运行结果确认兼容性。

### 4.7 `enthalpy`：比热突变与反应热耦合

**问题描述与验证目的。** 1 mm 薄板一面受到 3 kW/m² 热通量，MAT_A 以恒定速率 6 kg/(m³·s) 在 5 s 内转化为 MAT_B。MAT_A 的比热在 80--81 °C 从 1.0 降至 0.1 kJ/(kg·K)，反应焓修正会在该区间产生温度“bump”。官方所谓解析曲线是对薄板能量方程的小步长数值积分，因此这是传导、质量加权比热、反应速率、辐射边界的耦合验证。

**使用模型。** 反应式 `r=rho_s^n A exp(-E/RT)` 取 `A=6`、`E=0`、`N_S=0`；MAT_A→MAT_B，二者密度 30 kg/m³、导热系数 10 W/(m·K)。通过 `SPECIFIC_HEAT_RAMP='c_ramp'` 设置比热突变，`HEAT_TRANSFER_COEFFICIENT=0` 关闭对流，发射率 1 保留辐射。

**网格与计算。** 域 `[-0.15,0.15] x [-0.15,0.15] x [0,0.4] m`，`IJK=3,3,4`；底面中心 VENT 面积 0.01 m²，厚度 0.001 m。`T_END=7 s`、`DT=0.005 s`，输出表面温度和 MAT_A 固体密度。

**边界条件。** 前表面外部热通量 3 kW/m²、背衬未设为绝热而暴露于环境；五个外边界开放。对流系数为 0，因而温度曲线主要受净辐射与输入热通量控制。

**工况参数。** 初始 MAT_A 密度 30 kg/m³，MAT_B 同密度；比热 A 为 20--80 °C 时 1.0、81 °C 后 0.1，B 恒为 1.0；导热系数 10、表面厚度 0.001 m，A 的反应在 5 s 完成。

**输出与判据。** `enthalpy.csv` 给出表面温度参考曲线，后处理容差约 1%。重点检查 80 °C 附近斜率突变/温度峰和 5 s 后反应材料消失，而不是只看最终温度。

### 4.8 `tga_sample`、`tga_analysis` 和真实材料 TGA/MCC

#### `tga_sample`：多组分虚拟 TGA

**问题描述与验证目的。** 0.01 mm 薄样品由 component 1（60%）和 component 2（40%）组成，按 5 K/min 的升温程序加热到 820 K。两个组分具有不同参考温度/速率，均产生 47% `OFF-GAS` 与 53% residue，用来验证多组分 TGA 的质量分峰、总归一化质量损失率和组分归属。

**网格与计算。** 域 `[-2,2] x [-0.5,0.5] x [0,1] m`、`IJK=4,1,4`，`T_END=9600 s`、`DT=0.2 s`，`SOLID_PHASE_ONLY=T`、`RADIATION=F`。底部样品 VENT 为 2 m²，输出表面温度、总质量、两组分质量、残余质量及各自 MLR。

**边界条件与工况。** 表面 `BACKING='INSULATED'`、`HEAT_TRANSFER_COEFFICIENT=1000`，前表面温度由 0 到 820 K 的 `T_RAMP` 控制；component 1 的参考温度/速率为 300 K/0.0016，component 2 为 500 K/0.0005，二者 `HEATING_RATE=5`，密度 1000、导热系数 0.2、比热 1.0。判据是总质量和分组 MLR 与 `tga_sample_data.csv` 的曲线一致。

#### `tga_analysis`：含水湿木材三组分反应

**问题描述与验证目的。** 90% dry wood 与 10% water 组成湿木材。水先蒸发，dry wood 生成 char 和 `CELLULOSE` 气体，char 再生成 ash 和气体；`TGA_ANALYSIS=T` 自动进行虚拟 TGA。它验证多层/多组分材料的反应顺序、含水率和产物分配。

**网格与计算。** 两个串联网格，每个 `IJK=3,1,4`，分别覆盖 `[-6,-2]` 和 `[-2,2]` 的 x 区间，单元约 1.33 m；`T_END=60 s`。FDS 实跑显示“performed a TGA analysis only and finished successfully”。

**边界条件与工况。** 底部中央 2 m² VENT 使用 0.01 m 厚的 `wet wood`，没有显式外部热通量而由 TGA 分析驱动。dry wood 密度 500、比热 1、导热 0.2，参考 315 K/0.0056；char 参考 430 K/0.0075，水参考 100 K/0.0016、比热 4.184、蒸发热 2500 kJ/kg；干木→char 残余 0.40，char→ash 残余 0.15。当前 FDS 运行提示自定义 `CELLULOSE` 不是预定义物种，属于属性未定义警告，运行仍成功。

#### 真实材料 TGA/MCC 组

`cellulose_TGA_{1,3,5}KPM_Air` 使用外部 `cellulose_1C_MATL.fds`，氧质量分数 0.23，分别考察 1、3、5 K/min。`pine_wood_TGA_exp03/13/14/15/16/17_{1C,3C}` 使用 1C 或 3C 松木材料库、不同实验编号和 2.5 K/min 等升温工况；`anca-couce-fig{1,2}_{2p5K,5K,10K}` 使用纤维素/半纤维素/木质素三组分材料库，比较 Anca-Couce 木材 TGA；`birch_tga_1step_{2,20}` 比较桦木单步反应在不同升温条件下的实验质量；6 个 `cable_*_mcc` 将电缆护套/绝缘材料的 TGA 动力学转化为 MCC HRR 曲线。

这些输入卡共同使用 `TGA_ANALYSIS=T`、`SURFACE_VOLUME_RATIO`、圆柱粒子和 `CATF OTHER_FILES` 材料库。运行目录必须保持在 `Verification/Pyrolysis`，否则 `../../Utilities/Input_Libraries/MATL/...` 相对路径会失效。MCC 算例的判据是 HRR（通常以 W/g 归一化）峰值、峰温和曲线形状，与实验 CSV 比较，容差以 `FDS_verification_dataplot_inputs.csv` 为准，属于材料模型回归/验证。

### 4.9 液体蒸发：`methanol_evaporation`、`liquid_mixture`、`water_pool`

#### `methanol_evaporation`

**问题描述与验证目的。** 1 m x 1 m 甲醇池放在钢制盘内，外部热通量 20 kW/m²，跟踪甲醇液面温度、质量通量和热通量，检查液体达到沸点后潜热消耗与蒸发速率。参考 CSV 给出沸点 64.65 °C，后处理还将总热通量乘以 0.00091 换算理想蒸发速率。

**网格与计算。** 基础网格 `IJK=12,12,12`、`[-0.6,0] x [-0.6,0] x [0,0.6] m`，通过 `MULT` 在三个方向各复制 1 次，形成 8 个 0.6 m 网格。`T_END=360 s`，设备/剖面/HRR 间隔 5 s，池厚 0.05 m，四周钢壁及钢底板厚度 0.003 m。

**边界条件与工况。** 五个外边界开放，池表面绝热背衬、发射率 1、外部热通量 20 kW/m²；钢壁为 exposed backing，材料导热 45.8 W/(m·K)、密度 7850、比热 0.46。甲醇密度 796、比热 2.48、导热 100、沸点 64.65 °C、蒸发潜热 1099 kJ/kg、吸收系数 1500 m^-1。

**输出与判据。** `MASS FLUX`、`TOTAL/CONVECTIVE HEAT FLUX`、`WALL TEMPERATURE` 和平均/最大池面温度用于检验热平衡；重点是液面保持在沸点附近、蒸发通量与理想换算值接近。该算例的结果对网格边界和钢盘热惯性敏感。

#### `liquid_mixture`

池面积约 1 m²，液层 0.002 m、钢层 0.002 m，外部热通量 5 kW/m²，液体为 hexane 0.521、heptane 0.054、octane 0.063、decane 0.023、benzene 0.200、water 0.139（质量分数）。烃类蒸汽统一简化为 `N-HEXANE`，水蒸气单独输出。域 `[-2.5,1.5] x [-2.5,2.5] x [0,5] m`，`IJK=10,10,10`，`T_END=600 s`，`MASS_FILE=T`。分别定义密度、导热系数、比热、沸点、蒸发潜热和吸收系数，输出各组分质量通量、池厚度和壁温；CSV 在 400--600 s 给出水 0.2048 kg、燃料 1.269 kg 的稳定积分值。该算例主要验证多组分液体质量闭合，不应把统一 `N-HEXANE` 蒸汽误解为真实六种蒸汽化学组成。

#### `water_pool`

**问题描述与验证目的。** 1.2 m x 1 m、0.05 m 深水池上方有 25% RH、305 K 空气以 0.15 m/s 流过，池面约 293 K。官方依据 Clausius-Clapeyron 和 Sherwood 关联式给出理论蒸发率 `1.42e-5 kg/s`；该案例验证液面平衡蒸汽浓度、对流传质和水蒸气质量通量。

**网格与计算。** 域 `5 x 1 x 1 m`，`IJK=50,10,10`（0.1 m x 0.1 m x 0.1 m），`T_END=3600 s`、`DT=0.4 s`；池 VENT 为 x=1--2.2 m、宽 1 m 的底面区域，设备每 10 s 输出，剖面每 100 s 输出。

**边界条件与工况。** XMIN 为 `BLOW` 入口，速度 -0.15 m/s；XMAX 开放。池面 `TMP_INNER=20 °C`、`TMP_GAS_BACK=20 °C`、`BACKING='VOID'`，水材料沸点 100 °C、蒸发热 2260 kJ/kg；`ADJUST_H=F` 便于与理论值比较。环境 `TMPA=32 °C`，初始水蒸气质量分数 0.008374。

**输出与判据。** `mdot` 为水蒸气质量通量面积积分，`Ts` 为池面平均温度；CSV 参考 1200--3600 s 均约 1.42e-5 kg/s。理论与 FDS 不会完全重合，因为实际表面温度和上方水蒸气浓度会偏离名义值，报告应使用“接近理论值”而非零误差表述。

### 4.10 `shrink_swell`、`cell_burn_away` 与 `ice_cube`

#### `shrink_swell`

**问题描述与验证目的。** 六个并列网格分别测试纯收缩、含可收缩基体、含静态基体、纯膨胀、含可膨胀基体和含静态基体。反应物/产物密度差导致厚度变化：密度增大应收缩，密度降低应膨胀；基体 `ALLOW_SHRINKING`/`ALLOW_SWELLING` 为假时厚度保持不变，但单位面积质量应守恒。

**网格与计算。** 六个网格各 `IJK=3,3,4`，每个尺寸 0.3 x 0.3 x 0.4 m，x 方向从 1.0 到 6.3 m 平移排列；`T_END=15 s`、`DT=0.1 s`，设备每 0.5 s 输出。每个样品 VENT 为 0.1 x 0.1 m，初始厚度 0.001 m。

**边界条件与工况。** 外边界 X/Y MIN/MAX、ZMAX 开放，背衬绝热、对流系数 0；`SOLID_PHASE_ONLY=T`，`Y_O2_INFTY=0.01`，`CRITICAL_FLAME_TEMPERATURE=2000 K` 禁止气相燃烧。六个样品外部热通量分别 40、30、25、60、50、50 kW/m²。

**工况参数与理论值。** 收缩组反应物密度 500、产物 1000/1125 kg/m³；含基体时反应物/基体质量分数 0.9/0.1。膨胀组反应物密度 1000、产物 500/450 kg/m³，基体密度 90 或 1000。官方 CSV 期望：Shrink 1/2/3 厚度分别从 0.001 变为 0.0005、0.0005、0.001 m；Swell 1/2/3 从 0.001 变为 0.002、0.002、0.001 m，表面密度保持 0.5 或 1 kg/m²。

**输入审查。** `swelling_1` 段在反应物本身设置了 `ALLOW_SWELLING=.FALSE.`，与“纯膨胀”命名和官方表格中允许膨胀的语义不一致，必须结合当前版本结果确认是否为有意的等效设置；不能擅自修改原卡。文件中另有行末逗号格式风险。

#### `cell_burn_away`

单个 4 cm 立方体网格障碍物使用 `BURN_AWAY=.TRUE.`，材料密度 50 kg/m³、恒定反应率 0.05 s^-1，`THICKNESS=V/A=0.0066666 m`。因此燃烧率理论式为 `dm/dt=m0*rs*exp(-rs t)`，质量指数衰减至零。域 `0.2 x 0.2 x 0.2 m`、`IJK=5,5,5`、`T_END=110 s`、`DT=0.01 s`，六面开放边界。它验证整个固体单元烧失而非仅表面层反应时的速率；参考容差约 4%。

#### `ice_cube`

冰材料（密度 1000、比热 4.186、导热 0.2）在 20 kW/m² 下熔化，反应产物为水滴/水蒸气，潜热 334 kJ/kg，`BURN_AWAY=T`。立方体尺寸约 0.1 m，域 1 m³、`IJK=10,10,10`、`T_END=50 s`、`DT=0.05 s`，环境温度 20 °C、内部温度 -5 °C。设备输出池面水滴的 `AMPUA`，用于检查相变潜热、粒子释放和烧失几何。该卡的 `&HEAD`/`&TAIL` 组织和 `PART_ID='WATER DROP'` 依赖当前 FDS 对相变粒子的支持，建议运行时检查水滴数量和质量闭合。

### 4.11 `spyro_cone_demo_2`：SPyro 时变热流缩放

**问题描述与验证目的。** SPyro 模型不通过完整 Arrhenius 参数直接预测材料热解，而是用锥形量热实验得到的 `HRRPUA` 响应，在参考热流、时间和热流倍率之间插值/外推。本案例施加 10 与 100 交替的 `RAMP_EF='EF'`，检查时间变化外部热流下 `RAMP_Q='CONE'` 的响应缩放；`spyro_cone_demo` 还包含 25、50、75 kW/m² 多块参考热流，`spyro_cone_demo_3` 同时改变厚度与四组参考热流。

**使用模型。** `SURF HRRPUA=1`、`RAMP_Q`、`REFERENCE_HEAT_FLUX=50 kW/m²`、`INERT_Q_REF=T`、`RAMP_EF` 构成 SPyro 输入；`SOLID_PHASE_ONLY=T`、`HEAT_TRANSFER_COEFFICIENT=0`，因此不求解常规固相导热/Arrhenius 热解。材料仅提供密度 1000、导热 100、比热 1、厚度 0.01 m 以满足表面定义。

**网格与计算。** `spyro_cone_demo_2` 域 `0.4 x 0.1 x 0.4 m`、`IJK=4,1,4`，样品 VENT 为 x=0.1--0.2 m 的 0.1 m² 区域，`T_END=600 s`、`DT=0.1 s`，设备每 0.5 s 输出 `HRRPUA`。`EF` 以 18 s 周期在 10 与 100 之间切换。

**边界条件与工况参数。** 顶面开放，其余面默认；`TMPA=0`、点火温度 0、参考热流 50 kW/m²。材料厚度 0.01 m，外部名义热流为 1（作为 SPyro 归一化驱动），实际热流倍率由 `EF` 控制。CSV `spyro_cone_demo_2.csv` 提供 `Exact` 参考 HRRPUA 时间序列。

**输出与判据。** 比较 `HRRPUA` 设备和 `Exact`/参考锥形数据，检查热流切换后响应是否按 SPyro 定义缩放。`spyro_cone_demo` 的超长 `CONE` RAMP 是实验数据本身，修改 RAMP、参考厚度或热流后必须同步更新 expected CSV。

## 5. 输入卡问题与风险清单

以下问题来自静态扫描和实际启动信息。原始卡未被修改。

| 严重程度 | 文件/位置 | 发现 | 影响与建议 |
|---|---|---|---|
| 高 | `part_baking_soda_420K/450K/500K.fds` 末尾 `SPHERE DIA` | 同一个 namelist 行在 `/` 后又出现 `CONVERSION_FACTOR=DIAMETER/(RHO_S(0)^(1/3))` | 第一段 `CONVERSION_FACTOR=0.38444` 已结束 namelist，后半段看起来是残留说明/错误关键字。FDS 6.10.1 实跑仍完成，但应核对输出是否采用了 0.38444；建议保留一个明确的设备定义并在副本中测试，不能直接覆盖基准卡。 |
| 中高 | `anca-couce-fig2_{2p5K,5K,10K}.fds` | `MATL_ID(1,1:4)` 只给出 `CELLULOSE, HEMICELLULOSE, LIGNIN` 3 个值 | 维度与值数不一致，可能依赖 Fortran namelist 容忍行为。FDS 6.10.1 实跑 `10K` 正常完成 TGA，但仍建议改成 `1:3` 的测试副本并比较结果。 |
| 中 | `tga_analysis.fds` | 运行提示自定义 `SPEC CELLULOSE` 未在预定义物种表 | 不是语法错误，但气相热释放/热物性可能使用默认或不完整属性；本案例目标是 TGA 质量曲线，若要分析 HRR 必须显式给物种属性。 |
| 中 | `anca-couce-fig2_10K.fds` | 运行提示 `SPEC FUEL` 未预定义，且 TGA 输出 HRR 可能因多反应使用同一 FUEL 而不正确 | 质量损失/组分 MLR 仍可用于 TGA，对 HRR 结论应谨慎；若研究燃烧热释放，需要定义物种热物性并避免多个反应共用同一简化燃料。 |
| 中 | `cable_*_mcc.fds`、`birch_*`、`liquid_mixture`、`matl_e_cons_5/6`、`shrink_swell`、`spyro_cone_demo_3` | 若干行存在行末多余逗号或逗号换行不统一 | FDS 当前 namelist 解析器通常能容忍，但跨版本/其他编译器可能有兼容风险。建议在 CI 中用目标 FDS 版本逐卡启动检查。 |
| 中 | `shrink_swell.fds` 的 `swelling_1` | “纯膨胀”材料设置 `ALLOW_SWELLING=.FALSE.` | 语义可疑，可能是测试“禁止膨胀”的遗留设置，也可能是版本特定实现。应依据输出厚度与官方 `Swell 1` 期望 0.002 m 判定，不要仅凭名称修正。 |
| 中 | 外部材料库案例 | `CATF OTHER_FILES` 使用相对路径 | 必须从 `Verification/Pyrolysis` 目录运行；复制单卡到别处会找不到 `Utilities/Input_Libraries/MATL`，导致材料不完整。 |
| 低 | 质量守恒和粒子案例 | 极低氧、`SOLID_PHASE_ONLY`、高 `CRITICAL_FLAME_TEMPERATURE` | 这些是隔离机制的设计，不是错误；不能把结果用于真实燃烧 HRR 预测。 |

此外，部分设备行在多个卡中省略了行内逗号（例如 `ID` 后直接接 `SPATIAL_STATISTIC`），当前 FDS 仍可能将换行视作 namelist 分隔。若需要移植到旧版 FDS，应优先规范为每个关键字以逗号分隔并逐卡回归。

## 6. 复现与后处理建议

1. 从 `Verification/Pyrolysis` 目录运行，以保证 `CATF` 相对路径有效；使用与验证指南一致的 FDS 版本，并记录 revision。
2. 先运行短而敏感的 `two_step_solid_reaction`、`part_baking_soda_450K`、`surf_mass_vent_char_cart_fuel`，确认输入解析、设备输出和质量/直径量纲，再运行长时间 TGA、MCC 和液池案例。
3. 对解析/守恒案例，计算末值相对误差、最大绝对误差和守恒残差；不要只凭 Smokeview 曲线目测。建议使用官方 CSV 的容差字段。
4. 对 TGA/MCC/锥形量热案例，报告升温速率、氧浓度、实验编号、材料库版本和曲线误差；实验对比应称为材料模型验证/回归。
5. 对粒子案例同时检查 `PARTICLE MASS`、`MPUV`、`SOLID DENSITY` 和等效直径，防止设备选取位置或面积统计造成假误差。
6. 对 `liquid_mixture` 记录每种液体的质量积分并核对总质量；统一 `N-HEXANE` 蒸汽只是气相简化，不代表真实组分化学反应。
7. 修改任何 `MATL_ID` 数组范围、`RAMP`、厚度、外部热流或 SPyro 参考数据前，先复制输入卡，保存原始 expected CSV，并在报告中注明版本差异。

## 7. 总结

Pyrolysis 目录不是一组单一的“木材燃烧”案例，而是从最小单元测试到实验材料回归的分层验证套件。质量守恒族覆盖 VENT/PART、三种几何、炭化与非炭化、燃料与显式气体；`part_baking_soda` 和 `two_step_solid_reaction` 直接检验固相 ODE 与粒子分解解析解；`matl_e_cons` 与 `enthalpy` 检查反应焓和热传递耦合；液体案例覆盖潜热、沸点、传质和多组分蒸发；TGA/MCC/Anca-Couce/松木案例检验真实材料动力学；SPyro 案例则验证基于锥形量热数据的热解响应缩放。

最适合作为后续质量门槛的典型组合是：`surf_mass_vent_char_cart_fuel`（面质量守恒）、`surf_mass_two_species_cart`（多物种）、`part_baking_soda_450K`（粒子解析解）、`two_step_solid_reaction`（固相 ODE）、`matl_e_cons_5`（反应焓）、`water_pool` 或 `liquid_mixture`（液体传质）、`shrink_swell`（几何变化）、`tga_sample`/`pine_wood_TGA_exp13_3C`（材料 TGA）和 `spyro_cone_demo_2`（SPyro）。当前已实跑的五个输入卡均能由 FDS 6.10.1 完成，但这不替代全部 87 个算例的数值误差回归；输入卡风险应按第 5 节处理并保留原始基准。
