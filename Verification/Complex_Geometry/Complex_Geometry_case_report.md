# FDS `Verification/Complex_Geometry` 算例报告

## 1. 范围和总体结论

检查对象为 `F:\DESK\1FireDynamicsSimulation\SHENBBAO\Verification\Complex_Geometry`，并以当前仓库中的 `Verification/Complex_Geometry`、`Verification/FDS_Cases.sh`、FDS 验证指南和相关 Matlab 后处理脚本交叉核对。

- 主目录有 116 个 `.fds`，`CompGeom_Scaling` 子目录另有 9 个，共 125 个输入卡。
- `Verification/FDS_Cases.sh` 中主动运行 92 个主目录算例；24 个主目录输入没有被该脚本主动运行。`zero_thick_roof.fds` 的运行行被注释。
- 这些算例不是单一火灾场景，主要验证 GEOM 三角面、自动生成几何、切割单元/CC-IBM、压力投影、物种与能量通量、辐射、粒子、网格收敛和几何预处理错误检查。
- 主要物理量为人为构造的验证量，不能把高质量流量、高质量通量或高温表面直接解释为工程火灾工况。
- 已执行的静态/短算例核对见第 8 节；完整批量回归仍应在项目规定的 FDS/编译器环境中运行。

## 2. 使用的 FDS 模型

`GEOM` 表示由闭合三角面组成的非结构化固体表面。每个三角面由三个顶点索引和一个表面索引组成，FDS 在笛卡尔网格上构造切割面、切割多面体和流体体积。`GEOM` 与 `OBST` 相交时，FDS 会尝试布尔合并；过于复杂时可能留下空单元。因此，GEOM 要求表面闭合、面不退化、边恰好连接两个面、顶点为流形、面法向一致且不同体积不自相交。

本目录覆盖以下模型和算法：

1. **几何生成**：`VERTS/FACES` 三角面；`XB` 块体；`SPHERE_ORIGIN/SPHERE_RADIUS` 球体；`CYLINDER_*` 圆柱；`ZVALS/IS_TERRAIN` 地形；`POLY/EXTRUDE` 平面多边形挤出；`MOVE` 刚体旋转、平移、缩放和 T34 变换；纹理映射。
2. **流动和传输**：DNS 或 LES/VLES；物种质量分数、密度、黏性和标量扩散；无重力、无噪声、无分层设置用于解析解测试。
3. **压力求解**：多数动态 GEOM 算例采用 UGLMAT；MMS 算例用 `CHECK_POISSON` 检查压力泊松方程；`CCVOL_LINK=0` 的泊肃叶算例测试不链接的小切割单元和应力方法。
4. **热和辐射**：`CONVECTIVE_HEAT_FLUX`、`MASS_FLUX`、固体导热材料、表面发射率、离散角度辐射传输、壁面热流和能量体积分。
5. **颗粒**：喷雾/水滴 `PROP`，静态固体颗粒，表面颗粒质量通量，颗粒与 OBST/GEOM 碰撞、跨网格和沿表面移动。
6. **制造解（MMS）**：`PERIODIC_TEST=7` Shunn，`11` Saad，`21/22/23` 旋转立方体，`105` 切割单元构造计时。源项在 `Source/main.f90`、`ccib.f90`、`mass.f90`、`divg.f90` 和 `velo.f90` 中加入。

## 3. 算例分类总表

| 类别 | 输入卡 | 主要验证内容 |
|---|---|---|
| 基础几何和显示 | `geom_simple(.fds/2)`, `geom_azim`, `geom_elev`, `geom_scale`, `t34_scaling` | 顶点/面连接、方位角、仰角、缩放、平移、翻转和 T34 变换；多数 `T_END=0`，属于预处理/Smokeview 检查 |
| 球面离散和地形 | `geom_sphere1a-f`, `geom_sphere3a-f`, `geom_terrain`, `geom_terrain2` | 递归二十面体球、经纬度球、ZVALS 地形、IS_TERRAIN 和 cut-cell 显示 |
| 纹理 | `geom_texture`, `geom_texture2`, `geom_texture3a/b`, `geom_texture4a/b` | 三角面、多纹理和球面纹理映射；依赖外部图片 |
| 几何质量错误 | `geom_bad_inconsistent_normals`, `geom_bad_inverted_normals`, `geom_bad_non_manifold_edge/vert`, `geom_bad_open_surface`, `geom_self_intersection` | 法向、非流形边/点、开口面、自相交检测；故意失败输入 |
| 切割单元几何 | `cone_1mesh`, `sphere_cc_compute`, `cube_cc_compute`, `two_spheres`, `geom_intersection`, `geom_extruded_poly` | 穿 cell、split cell、面与网格对齐、相交/挤出几何、面积/体积/质心守恒 |
| 通道和面积积分 | `geom_channel`, `geom_channel2`, `geom_channel_tmp`, `geom_channel_tmp2`, `devc_surface_integral` | GEOM 与 OBST 通道、质量通量、入口温度、表面积分/面积积分 |
| 泊肃叶流 | `geom_poiseuille_N10/20/40/80_{a,na,nah}_theta0_stm` | 解析摩擦因子 `f=24/Re`，网格对齐、偏移和 `h=dz/3` 的收敛；应力方法 |
| 球/圆柱绕流 | `sphere_Re200`, `sphere_stress`, `cylinder_Re200` | Re=200/100 绕流、压力阻力、黏性应力、跨网格和二维圆柱 |
| 氦气/燃烧 | `sphere_helium_1mesh`, `sphere_helium_3meshes`, `sphere_helium_conserve_3meshes`, `sphere_propane_demo` | 物种输运、跨 mesh 守恒、UGLMAT、球面周围丙烷燃烧 |
| 热流、辐射和泄漏 | `ccibm_sphere_heat_flux`, `ccibm_sphere_mass_flux`, `sphere_radiate`, `sphere_shadow`, `sphere_leak` | 对流热流、质量通量、辐射视因子/阴影、密闭球泄漏压力 |
| 初始化和颗粒 | `geom_hrrpuv_init`, `geom_part_init`, `geom_particle_cascade`, `geom_particle_flux`, `geom_particle_cascade_2`, `thin_object_mass` | GEOM/INIT 相交、HRRPUV、颗粒质量通量、滴落/碰撞、薄体小 cell 质量守恒 |
| 可变密度 MMS | `saad_CC_explicit_*`, `shunn3_*_cc_exp_{chm,gdv}` | 切割区域显式积分的时间/空间阶、密度/组分/速度/焓/压力误差 |
| 旋转立方体 MMS | `rotated_cube_{0,27,45}deg_*` | GEOM 与 OBST、0/26.565/45 度旋转、MMS 源项和网格收敛 |
| 性能缩放 | `CompGeom_Scaling/compgeom_scale_*` | 三角面数量、网格 cell 数、cut-cell 建造时间和 CPU 计时扩展性 |

## 4. 网格、计算和边界条件参数

### 4.1 基础几何、球面、地形和切割单元

| 算例/系列 | 网格与时间 | 边界/工况 | 关注量 |
|---|---|---|---|
| `geom_simple`, `geom_simple2` | `10x10x10`, `[0,1]^3`, `T_END=0` | 无物理边界；一个三角面，RGB 红色 | `VERTS/FACES` 解析和 Smokeview 显示 |
| `geom_azim` | `10x10x10`, `[0,1]^3`, `T_END=0` | 三个相同三角面，`AZIM=0/45/90`，红/绿/蓝 | 方位角旋转 |
| `geom_elev` | `10x10x10`, `[0,1]^3`, `T_END=0` | `ELEV=0/45/90`, `XYZ0=(0,0,1)` | 仰角变换 |
| `geom_scale` | `10x10x10`, `[-1,1]^3`, `T_END=0` | 三个三角面，`SCALE=(1,1,1),(1,1,2),(2,1,1)` | 缩放和参考点；三个记录均写成 `ID='geom4'` |
| `geom_sphere1a-f` | `20^3`, `[-1,1]^3`, `T_END=0` | 半径 1、中心原点；`N_LEVELS=0...5` | 20 面起始的递归球；三角数按 20×4^N 增长 |
| `geom_sphere3a-f` | 同上 | `N_LAT/N_LONG=(3,6),(6,12),(12,24),(24,48),(48,96),(96,192)` | 经纬度球；极点附近三角形长宽比增大 |
| `geom_terrain` | `20^3`, `[-1,1]^3`, `T_END=0` | `IJK=20,20`, `ZVALS` 数字高程，`ZMIN=-1`，外边界 OPEN | 规则地形三角剖分 |
| `geom_terrain2` | `40^3`, `[-1,1]^3`, `T_END=1` | `IS_TERRAIN=T`，40×40 顶点，两个表面，外边界 OPEN | terrain cut-cell 和 `CELL PHASE` |
| `geom_extruded_poly` | `36^3`, `[-2,2]x[-2,2]x[0,4]`, `T_END=20` | 多边形 10 顶点，`EXTRUDE=0.5`；五个侧面 OPEN，底面默认边界 | 平面简单多边形挤出为三维实体 |
| `geom_intersection` | `10^3`, `[-2,2]x[-2,2]x[0,4]`, `T_END=1` | 两个 2×2×2 重叠立方体，`INERT` | GEOM-GEOM 相交的布尔/线性化 cut-face |
| `cone_1mesh` | `5x5x12`, `[-1.5,1.5]^2 x[-2,6]`, `T_END=1` | 316 vertices、628 triangles；五个侧面 OPEN、顶部 OPEN | 穿 cell、split cell、z=0 对齐面；面积、体积、质心守恒 |
| `sphere_cc_compute` | 当前激活 8 mesh，每块 `36^3`；总区域约 `[-2,2]^2x[0,4]`，`T_END=1` | `COMPUTE_CUTCELLS_ONLY=T`；半径 1 球，中心 `(0,0,2)` | 多 mesh cut-cell 预处理；1/2/4/16 mesh 配置被注释 |
| `cube_cc_compute` | 当前激活 3 mesh，块为 `32x32x16` 和 `16x32x16`，`T_END=1` | `COMPUTE_CUTCELLS_ONLY=T`；旋转立方体三角面 | 旋转立方体 cut-cell 计算和分解 |
| `two_spheres` | `65x32x32`, `[-2.8,2.8]x[-1.4,1.4]^2`, `T_END=.01` | 两球中心 `x=±1.02`，半径 1，外边界 OPEN | 两个相邻、近接触球的 cut-cell 定义 |

### 4.2 通道、面积积分和传热

| 算例 | 网格/时间 | 边界和参数 | 验证 |
|---|---|---|---|
| `geom_channel` | `12x1x9`, `[-.25,1.25]x[0,1]x[-.25,1.25]`, `T_END=10` | XMIN `INLET`，`VEL=-1`、TRACER 质量分数 1；XMAX OPEN；上下为 GEOM 自由滑移壁 | `U0/A0`、`U1/A1` 和子区域 `U2/A2`、`U3/A3`；Matlab 脚本要求各面积约 1，容差 `1e-6` |
| `geom_channel2` | 两块：`11x1x8` 的 z=0..1 OBST 通道，`12x1x8` 的 z=-1.5..-.5 GEOM 通道；`T_END=1` | XMIN 质量通量 1 kg/m²/s，XMAX OPEN；TRACER；自由滑移绝热壁 | OBST 与 GEOM 入口质量通量对照 |
| `geom_channel_tmp` | 一块 OBST 通道加一块偏移 GEOM 通道；`T_END=1`，UGLMAT | 600°C 入口，`RAMP t1` 在 0 到 10 s 保持；两端 XMIN/XMAX 入口/出口 | 几何位置偏移和温度输运 |
| `geom_channel_tmp2` | 两块 `11x1x8`/`12x1x8`，`T_END=100` | 600°C 入口 ramp；XMAX OPEN；默认墙 | GEOM 通道热传递 |
| `devc_surface_integral` | `10^3`, `[-.25,1.25]^3`, `T_END=30`，LES、`CFL_MAX=.8` | XMIN TRACER/`VEL=-1`，XMAX OPEN；四面 GEOM 自由滑移壁 | 全截面与 1×1 截面的 NORMAL VELOCITY/U-VELOCITY 面积积分 |
| `geom_poiseuille_*` | `IJK=4,1,N+2`，x=3..7、y=-.5.. .5，z 约 -0.1..1.1；`N=10,20,40,80`，`T_END=70` | DNS、`VISCOSITY=.025`、`FORCE_VECTOR(1)=1`，XMIN/XMAX PERIODIC，`CCVOL_LINK=0` | 解析 `f_an=24/Re_H`；`a`: h=0；`nah`: h=dz/3；`na`: 固定偏移 `h=dz_10/11`；STM 横向速度应力方法 |

泊肃叶流的物理参考值为 `rho≈1.165 kg/m³`、H=1 m、`dp/dx=-1 Pa/m`、`u_bar≈3.33 m/s`、`Re_H≈155`。后处理 `poiseuille_convergence_cc.m` 绘制 `|f-24/Re|` 对 `dz` 的一阶/二阶趋势。

### 4.3 绕流、氦气、燃烧、辐射和泄漏

| 算例 | 网格与计算 | 边界/工况 | 主要输出和目的 |
|---|---|---|---|
| `sphere_stress` | `40^3`, `[-1,1]^3`, `T_END=1`，DNS | x=-1 入口 `VEL=-1`，x=+1 OPEN，四侧 MIRROR；半径 .5 球；背景气体黏性 .01 | 球面压力和黏性应力 x 向积分；Re=100，应力/阻力 |
| `sphere_Re200` | 两 mesh，各 `144x18x36`，总域 x=-3..9、y=-1.5..1.5、z=-1.5..1.5，`T_END=60` | x=-3 入口、x=9 OPEN；y/z PERIODIC；DNS，背景黏性 .005，U=1；半径 .5 球 | Re=200 球绕流、跨 mesh 接口、Q criterion、壁面压力/黏性应力 |
| `cylinder_Re200` | `144x36x36`, `[-3,9]x[-1.5,1.5]^2`, `T_END=60` | x 入口/出口；y/z MIRROR；背景黏性 .005、U=1；半径 .5、长度4、轴 x，再绕 z 旋转 90° 使圆柱跨 y | 二维圆柱 Re=200 绕流和壁面应力 |
| `sphere_helium_1mesh` | `64^3`, `[-2,2]x[-2,2]x[0,4]`，锁定 `DT=.01`，`T_END=.1` | 底面中心入口氦气，`VEL=-1`、`TAU_MF=1`；侧面和顶部 OPEN；球心 z=2、半径1、厚度 .1；DNS/UGLMAT | 氦气质量分数、密度、黏性、速度和焓 |
| `sphere_helium_3meshes` | 下部一块 `64x64x32`，上部两块 `32x64x32`，`MULT DX=2`；同样 `DT=.01,T_END=.1` | 同一入口/OPEN 条件 | 氦气穿过球面和跨三 mesh 输运 |
| `sphere_helium_conserve_3meshes` | 同上三 mesh，`T_END=3`，未锁定时间步 | 同上 | 较长时间的跨 mesh 质量/能量守恒 |
| `sphere_propane_demo` | 基础 `32x16x16`，`MULT DY=2,DZ=2,J_UPPER=1,K_UPPER=2`，即 6 个复制 mesh；总域约 4×4×6 m，`T_END=5` | 五侧 OPEN；底部 OBST burner `HRRPUA=3200 kW/m²`；丙烷、`SOOT_YIELD=.02`；球面半径1、材料 rho100/k1/cp1 | 球周围丙烷燃烧、HRRPUV、温度和球壁温度 |
| `ccibm_sphere_heat_flux` | `32^3`, `[-1.4,1.4]^3`, `T_END=10` | 无辐射；默认绝热墙；半径1球面 `CONVECTIVE_HEAT_FLUX=10 W/m²`；内部能量体积分 | 热流边界和能量守恒 |
| `ccibm_sphere_mass_flux` | `32^3`, 同域，`T_END=5`，LES | 顶部 OPEN；球面 TRACER 质量通量 10 kg/m²/s；半径1、`N_LEVELS=5` | 理论总输入质量 `10×4π×5=628.3 kg`；TOTAL MASS FLUX WALL 与 PID 控制值 |
| `sphere_radiate` | `64^3`, 4 m 立方域，`T_END=.01,DT=.01`，UGLMAT | 球面 `TMP_FRONT=500°C=773.15 K`；外墙 `-273°C≈0 K`；eps=1、无对流；400 radiation angles | 最近冷墙热流理论值 `sigma*T^4/4=5.065 kW/m²`，与 `HF1..HF6/HFT` 比较 |
| `sphere_shadow` | `64^3`, 同域，`T_END=20` | 顶面 HOT WALL 500°C，其余墙20°C；球面厚度 .01、材料 rho500/k.1/cp1、eps1；100辐射角 | 热球遮挡/辐射阴影、球面和墙面辐射热流 |
| `sphere_leak` | `32^3`, `[-1.6,1.6]^3`, `T_END=100`，ULMAT | 中心密闭球内 `ZONE LEAK_AREA(0)=1e-4 m²`；0.2 m 立方 blower，`VEL=-.2`，体积流量 `.04×.2=.008 m³/s`；外部六面 OPEN | 预期 `Δp=0.5*rho*(Vdot/A)^2≈3840 Pa`，检验 GEOM 泄漏路径 |

### 4.4 初始化、颗粒和薄体质量

| 算例 | 参数和边界 | 验证 |
|---|---|---|
| `geom_hrrpuv_init` | `20^3`, `[-1,1]^3`, `T_END=10`；六面 OPEN；GEOM `[-.5,0]^3` 与 INIT `[-.5,.5]^3` 相交，`HRRPUV=100 kW/m³` | 流体体积为 `1-.5^3=.875 m³`，理论总 HRR=87.5 kW；目录中的 csv 给出 0/10 s 均 87.5 |
| `geom_part_init` | `20^3`, `[-1,1]^3`, `T_END=10`；METHANE，六面 OPEN；10000 个 STATIC 粒子，半径 `.0028209479 m`，球面总面积约1 m²，`HRRPUA=100` | GEOM/INIT 相交时粒子初始化、粒子温度/直径和 HRRPUV |
| `geom_particle_cascade` | `50x50x25`, `[-5,5]^2x[0,5]`，`DT=.1,T_END=10`，`PARTICLE_CFL=T` | 顶部 0.4×0.4 m HOLE，`PARTICLE_MASS_FLUX=.1 kg/m²/s`、速度 -5；同时有同坐标 OBST 和 GEOM，另有半径1球 | 固体非蒸发粒子落到 GEOM/OBST 表面、MPUV 质量 |
| `geom_particle_flux` | 同网格，`DT=.1,T_END=20` | 与 cascade 相同的 HOLE、粒子和同坐标 OBST/GEOM | 表面粒子质量通量；当前文件为旧卡，详见第8节 |
| `geom_particle_cascade_2` | 四块 `20^3` mesh，x=0..1、2..3、4..5、6..7，`T_END=15` | 水蒸气滴，`FLOW_RATE=60`、1到10 s ramp、`DIAMETER=1000`、喷射速度2、喷雾角0..10°；四工况：OBST、静止 GEOM、旋转 GEOM、偏移 GEOM；第三个绕 `(1,1,1)` 转45° | 4 个 `AMPUA` 表面积分；目录 csv 在 13/14/15 s 给出每个区域 10 kg，验证滴落、碰撞和跨 mesh |
| `thin_object_mass` | 两块 `16x32x32` mesh 覆盖 0..1，第三块 `32^3` 覆盖 x=2..3；`T_END=2,DT=.002` | TRACER 质量通量 .01；第一块薄 GEOM 厚 .001 m 并绕 y 旋转20°，第二块厚 .101 m；无外部 vent（封闭） | 比较薄/厚几何的质量通量和体积累积，测试小流体 cell 的稳定性 |

## 5. MMS、解析解和收敛工况

### 5.1 Saad 可变密度时间精度

`saad_CC_explicit_512_cfl_p25/p125/p0625.fds` 都使用 `IJK=512,1,4`，`x=[-1,1]`，`y=[-.05,.05]`，`z=[-.125,.125]`。x 两端 PERIODIC，z 两端 MIRROR，`U0=1`，`CC_IBM=T`，`PERIODIC_TEST=11`，中间 x=[-.5,.5] 人为设置与规则 cell 同形状的 cut-cell。两种组分的参考密度分别为 5 和 0.5，扩散率和黏性为 0。

| 文件 | 固定步长 | 对应 CFL |
|---|---:|---:|
| `p25` | 0.0009765625 s | 0.25 |
| `p125` | 0.00048828125 s | 0.125 |
| `p0625` | 0.000244140625 s | 0.0625 |

`T_END=.390625`，`LOCK_TIME_STEP=T`，`MMS_TIMER` 在终点输出。初始混合分数为 `f=0.5(1+sin(2πx/L))`，场以单位速度向右平移；Matlab 后处理用三个时间步的差分比计算 rho 和 Z 的时间阶，目标为二阶。

### 5.2 Shunn Problem 3 切割区域空间/时间精度

`shunn3_N_cc_exp_chm/gdv.fds` 的 N 为 32、64、128、256、320、384；均为 `N x 1 x N`，域 `[-1,1] x [-.05,.05] x [-1,1]`，x/z PERIODIC，y 只有一个 cell。`T_END=1`，`MMS_TIMER=.9`，`CFL_MAX=.25`，`CC_IBM=T`，`PERIODIC_TEST=7`，检查泊松方程。背景/标量组分密度参数为 5/1，黏性和扩散率为 .001，导热系数 .02。

- `exp_chm`：DNS 默认 `CHARM` 通量限制器；
- `exp_gdv`：显式设置 `FLUX_LIMITER='GODUNOV'`；
- 后处理计算 rho、混合分数 Z、速度 u、焓 H 的 L2 误差。

验证指南预期：CHARM 下 rho、Z、u 近似二阶；GODUNOV 下对流量近似一阶；压力/焓受 FDS 投影方法限制，约一阶；扩散项在规则形状 cut-cell 上为二阶。`384` 文件存在但未列入当前 `FDS_Cases.sh`。

### 5.3 旋转立方体 MMS

每个文件为 `N x 1 x N`，N=32、64、128、256、320、384，`T_END=1`，`CFL=.1`，DNS、UGLMAT、无辐射，`MMS_TIMER=.95`，`CC_IBM` 由旋转 GEOM 路径使用。两个物种的 MW 为 24.055，黏性和扩散率 .01；x/z PERIODIC，y 为一层退化方向。

| 系列 | 旋转角 | 周期域 | `PERIODIC_TEST` | 对照 |
|---|---:|---|---:|---|
| `rotated_cube_0deg_*` | 0° | `0..2π` × `0..2π` | 21 | 同一网格另有 `*_obs` OBST |
| `rotated_cube_27deg_*` | 26.565°（文件名 27） | 长度 `sqrt(20)π≈14.05` | 22 | GEOM |
| `rotated_cube_45deg_*` | 45° | 长度 `sqrt(8)π≈8.89` | 23 | GEOM |

立方体局部边长 π，中心经 `MOVE` 平移到 `(π,0,π)` 附近；MMS 速度为正弦函数，压力为解析场，标量 Z 振幅 .1、均值 .15。`rotcube_cc_mms_error.m` 将全局坐标旋回局部坐标计算 u、v、Z、H、p 误差。预期压力约一阶；0° 对齐时 OBST 和 STM 速度可达到二阶，倾斜 GEOM 的标量扩散误差通常为一阶。

## 6. `CompGeom_Scaling` 性能算例

所有缩放卡均为 `64^3`、`[-1.4,1.4]^3`、`T_END=.01`、`PERIODIC_TEST=105`，半径1球，`N_LEVELS=2...7`，五个外边界 OPEN。递归球的三角面数为：

| N_LEVELS | 约三角面数 |
|---:|---:|
| 2 | 320 |
| 3 | 1,280 |
| 4 | 5,120 |
| 5 | 20,480 |
| 6 | 81,920 |
| 7 | 327,680 |

`32x32`、`128x128`、`256x256` 三个卡固定 `N_LEVELS=4`，用于 cell 数缩放；`64x64` 系列固定网格、改变三角面数。`Run_cases.sh` 使用 `-p 1 -o 1` 串行计时。`compgeom_scale_plots.m` 读取 `*_cc_cpu_000.csv` 的 cut-cell 阶段计时，绘制 wall time 对三角面数量的对数图，并比较线性和平方根参考趋势。该组是性能测试，不是物理精度验证。

## 7. 文件覆盖范围和后处理

主目录 116 个输入中，当前主动脚本没有运行以下 24 个：

`ccibm_sphere_heat_flux.fds`, `ccibm_sphere_mass_flux.fds`, `cube_cc_compute.fds`, `cylinder_Re200.fds`, `devc_surface_integral.fds`, `geom_azim.fds`, `geom_elev.fds`, `geom_particle_cascade.fds`, `geom_particle_flux.fds`, `geom_scale.fds`, `geom_simple2.fds`, `rotated_cube_0deg_384_obs/stm.fds`, `rotated_cube_27deg_384_stm.fds`, `rotated_cube_45deg_384_stm.fds`, `shunn3_384_cc_exp_chm/gdv.fds`, `sphere_cc_compute.fds`, `sphere_propane_demo.fds`, `sphere_Re200.fds`, `sphere_shadow.fds`, `sphere_stress.fds`, `two_spheres.fds`。

这些文件中一部分是高成本/历史/显示输入，另一部分是有价值但没有纳入 nightly 的物理回归。建议在报告或 CI 中明确标记 `active`, `manual`, `display-only`, `expected-failure`, `performance`，不要只按目录存在性判断覆盖率。

相关后处理包括：

- `geom_channel_test.m`：检查四组面积积分是否为 1，容差 1e-6；
- `poiseuille_convergence_cc.m`：计算摩擦因子和 Re，比较 `24/Re`；
- `saad_cc_mms_temporal_error.m`：检查 Saad rho/Z 的二阶时间阶；
- `shunn_cc_mms_error.m`：绘制 CHARM/GODUNOV 空间 L2 误差和容差；
- `rotcube_cc_mms_error.m`：计算旋转坐标系下 u/v/Z/H/p 误差；
- `geom_positive_errors.m`：检查法向、开口面、非流形边的错误文本；
- `geom_mass_file_test_exact.csv`、`geom_hrrpuv_init.csv`、`geom_particle_cascade_2.csv`、`sphere_radiate.csv`、`sphere_leak.csv`、`geom_stretched_grid_exact.csv`：作为期望结果/后处理参考，不是 FDS 输入依赖。

## 8. FDS 输入卡检查结果

### 8.1 已确认的设计性错误或缺陷

1. **粒子旧卡的 namelist 行格式有问题**：`geom_particle_cascade.fds` 和 `geom_particle_flux.fds` 中，OBST 行以及 `DEVC ID='clock'` 行缺少 `&`；OBST/GEOM 行还在 `SURF_IDS` 后过早出现 `/`，随后才写 `DEVC_ID='clock'`。规范写法应把所有字段放在一个 namelist 中，例如：
   ```text
   &OBST ..., SURF_IDS='INERT','HOLE','INERT', DEVC_ID='clock' /
   &GEOM ..., SURF_IDS='INERT','HOLE','INERT', DEVC_ID='clock' /
   &DEVC ID='clock', QUANTITY='TIME', ... /
   ```
   两个文件没有被当前自动测试脚本运行。用当前 Windows FDS 构建在隔离目录试跑时，均在早期粒子时间步发生 access violation（退出码 157），不能视为通过。
2. **相同坐标的 OBST 和 GEOM 重叠**：上述两个粒子旧卡同时在完全相同位置定义 OBST 和 GEOM。FDS 对 GEOM-OBST 会执行布尔合并，因此这不是清晰的独立 A/B 对照，且可能改变孔面和粒子碰撞拓扑。若目标是比较两种表示，应将两种对象放在不同区域，或一次只激活一种定义。
3. **自相交检查覆盖不足**：`geom_self_intersection.fds` 标题明确为自相交几何，但没有 `POSITIVE_ERROR_TEST=T`。当前 FDS 构建对它完整计算并返回成功，未产生预期错误。若这是负测试，应增加正错误标志并在 `geom_positive_errors.m` 增加检查；若自相交尚未实现检测，应在验证清单中标为 FIXME，而不是“通过”。
4. **非流形顶点检查目前只是警告**：`geom_bad_non_manifold_vert.fds` 虽设置 `POSITIVE_ERROR_TEST=T`，但当前构建只报告 `Vertex 6 not connected` 警告并继续计算。`geom_positive_errors.m` 也明确注释该条件尚未捕获。应保持为已知限制或补充真正的错误断言。

### 8.2 维护、可复现性和覆盖问题

1. `geom_texture*.fds` 引用 `nistleft.jpg`、`grass.jpg`、`sphere_cover_03.png`、`sphere_cover_04.png`，这些文件在目标目录和当前仓库中均不存在。FDS 几何本身不一定因此失败，但 Smokeview 纹理不可复现，会产生缺图/警告。应补齐二进制资源或改为仓库内相对路径。
2. `geom_elev.fds` 和 `geom_scale.fds` 的说明仍写着 `***AZIMUTHAL TEST`，不影响计算但容易误导维护者。
3. `geom_scale.fds` 三个几何都使用 `ID='geom4'`。当前 ID 不是计算所需的唯一键，通常不会改变几何，但建议改成 `geom_scale_1/2/3`。
4. `geom_texture3a/b/4a/b.fds` 没有显式 `&TIME`；它们应被标记为 Smokeview 显示输入，或补上 `T_END=0`，避免不同 FDS 版本的默认时间造成差异。
5. `zero_thick_roof.fds` 的 `GEOM` 屋顶为 `zmin=zmax=.05`，用于零厚度测试，但 `FDS_Cases.sh` 中运行行被注释。若保留，应明确是人工/已知限制测试；若不再支持，应移入历史目录。
6. 384 分辨率的 Shunn 和旋转立方体文件存在但未在 nightly 脚本中运行；球/圆柱绕流、热流和表面积分等多个有价值算例也未运行。当前自动测试覆盖的是“目录输入”的约 79%（92/116），不是全部验证范围。

### 8.3 未发现明显错误但应按版本确认的配置

- `geom_terrain2` 的 `SURF_ID='surf1','surf2'` 是 GEOM 数组写法，源码 `READ_GEOM` 支持多表面数组；不应机械改成单一 `SURF_ID`。
- 粒子 `DIAMETER=1000` 按 FDS 粒子约定通常表示微米量级，属于人为喷雾参数；在跨版本运行前应核对当前 User Guide 的单位。
- `ccibm_sphere_mass_flux` 的 10 kg/m²/s、理论 628.3 kg 总质量是质量守恒压力测试，不是火灾工程值。
- `sphere_radiate` 的 `TMP_FRONT=500` 和 `-273` 按摄氏度输入正好对应约 773 K 和 0 K，不能当作开尔文误读。
- `geom_poiseuille_*` 的 `CCVOL_LINK=0`、`CFL` 和 70 s 运行时间是收敛测试设计；不建议为普通工程算例直接照搬。

## 9. 已执行的最小运行核对

在隔离临时目录使用 `Build/impi_intel_win/fds_impi_intel_win.exe`，避免污染原目录：

- `geom_simple.fds`：设置检查完成，退出码 0；
- `geom_bad_inconsistent_normals.fds`：输出 `SUCCESS`，检测到法向错误后停止，退出码 0；
- `geom_bad_inverted_normals.fds`：同上；
- `geom_bad_non_manifold_edge.fds`：输出 `SUCCESS`，检测到非流形边后停止，退出码 0；
- `geom_bad_open_surface.fds`：输出 `SUCCESS`，检测到开口边后停止，退出码 0；
- `geom_bad_non_manifold_vert.fds`：只警告并完成 1 s 计算；
- `geom_self_intersection.fds`：完成 1 s 计算，未检测到错误；
- `geom_particle_cascade.fds`、`geom_particle_flux.fds`：可进入求解，但当前构建在早期粒子时间步发生 access violation，退出码 157；这两个旧卡不应列为通过。

上述结果是当前构建的静态/短算例证据，不替代完整 MPI nightly 回归。建议修正第 8.1 节的输入/测试断言后，再用项目指定版本重新跑全部 active 和 scaling 列表。

