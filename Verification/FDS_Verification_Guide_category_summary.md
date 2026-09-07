# FDS Verification Guide 与桌面验证算例分类汇总

## 0. 文档定位

本报告把桌面目录 `F:\DESK\1FireDynamicsSimulation\SHENBBAO\Verification` 的输入卡目录、现有“三类/六类算例”整理稿，以及桌面根目录的 `FDS_Verification_Guide.pdf` 统一到同一套分类中。

依据文件：

- `FDS_Verification_Guide.pdf`：NIST Special Publication 1018-2，Sixth Edition，*Fire Dynamics Simulator Technical Reference Guide, Volume 2: Verification*，共 364 个 PDF 页面；
- `Verification/README.md` 和 `Verification/FDS_Cases.sh`：官方 nightly/firebot 验证输入及运行方式；
- 当前桌面 `Verification` 目录中的实际 `.fds` 文件；
- `Complex_Geometry/Complex_Geometry_case_report.md` 及桌面已有的三类/六类算例整理稿。

本报告的“算例数量”按文件系统中的 `.fds` 文件统计；“active 数量”按 `FDS_Cases.sh` 中未注释的 `$QFDS` 行统计。后者表示脚本覆盖，不等于已经在本机完成回归。

## 1. 指南对 Verification、Validation 的区分

指南第 1 章（印刷页 1）给出的核心区分是：

| 概念 | 要回答的问题 | 典型证据 | 本地对应内容 |
|---|---|---|---|
| Verification（验证/代码验证） | 程序实现是否正确地表达了数学方程、离散格式和开发者的算法描述？ | 解析解、制造解、守恒关系、收敛阶、对称性、错误输入检查 | `NS_Analytical_Solution`、`Scalar_Analytical_Solution`、`Energy_Budget`、`Complex_Geometry`、`Thread_Check` 等 |
| Validation（确认/物理验证） | 模型是否在预期用途下正确代表真实世界？ | 与实验测量的温度、速度、HRR、烟层、热流或压力比较 | 桌面已有 `cabinet_01/06`、`FM_SNL_01/03`、`VTT_01/03` 六算例表 |
| Sensitivity（敏感性分析） | 网格、时间步、湍流、辐射、材料参数变化是否改变结论？ | 多分辨率、多模型或多参数序列 | `Turbulence`、`Timing_Benchmarks`、MMS 收敛序列、Complex Geometry scaling |
| Code checking（代码检查） | 是否存在越界、除零、边界条件实现错误、并行竞争或错误输入未拦截？ | debug 运行、正错误测试、对称性、OpenMP/重启检查 | `Controls`、`Pressure_Solver`、`Restart`、`Thread_Check`、几何坏输入等 |

因此，桌面表格中把“与实验对比的六类算例”和“解析解/代码检查算例”都叫作“验证”是工程上常见的简称，但正式报告必须注明层级。FDS 指南第 1 章明确指出：**verification 是 check of the math，validation 是 check of the physics**。

## 2. FDS 官方判定方法

指南附录 A（印刷页 307--328）说明，官方 verification suite 是持续集成的一部分，每晚运行并把 FDS 预测值与 exact/expected 值逐项比较。每条记录至少包含：

1. 算例名称和指南章节；
2. 期望物理量及其数值；
3. FDS 输出量及其数值；
4. 相对误差或绝对误差；
5. 允许容差；
6. 是否在容差内。

判定规则为：相对误差或绝对误差不超过该条记录的 tolerance 才算通过。不能仅凭 `.fds` 文件存在、FDS 启动成功或曲线“看起来合理”判定通过。附录 B（印刷页 329--330）进一步把安装测试定义为：安装指定版本、运行指定输入、与 Expected Results 比较，再按附录 A 判据确认安装没有损坏。附录 C（印刷页 331 起）给出复杂几何切割单元表面积、气体体积和质心的守恒定义。

## 3. 桌面 Verification 目录盘点

桌面 `Verification` 下共有 26 个含输入卡的验证目录和 1 个 `scripts` 目录，共 **924 个 `.fds` 输入卡**。`FDS_Cases.sh` 中识别到 **861 条未注释运行命令**。下表中的“指南对应”是按验证对象映射，不表示每个目录在 PDF 主文中都有同名小节；一部分控制、探测器、输出和并行案例主要由用户指南及附录 A 收录。

| 桌面目录 | 输入卡数 | active/总数 | 指南章节/来源 | 代表性算例 | 主要验证内容 | 主要输出或判据 |
|---|---:|---:|---|---|---|---|
| `Adaptive_Mesh_Refinement` | 4 | 1/4 | 第 8.5 节嵌入/重叠网格；开发扩展 | `ns2d_16_emb_1to1_refinement`、`ns2d_16_int_1to2_refinement`、`random_meshes` | 网格细化、嵌套网格和重叠网格通信；`random_meshes` 实际是嵌入网格流量测试 | 体积流量、跨网格场传递、debug 稳定性；部分 refinement 卡被注释 |
| `Aerosols` | 15 | 14/15 | 第 10.13.1--10.13.7 节 | `aerosol_agglomeration`、`aerosol_gravitational_deposition`、`aerosol_scrubbing`、`soot_oxidation_wall` | 气溶胶粒径分箱、凝并、重力/热泳/湍流沉积、液滴洗消、壁面烟炱氧化 | 各粒径箱质量、气相/壁面/总质量，与解析值或期望质量的误差 |
| `Atmospheric_Effects` | 13 | 12/13 | 第 6 章；部分大气边界层例在用户指南 | `atmospheric_boundary_layer_*`、`MO_velocity_profile_*`、`lee_waves`、`stack_effect` | 中性/稳定/不稳定大气边界层、Monin--Obukhov 相似律、Ekman 层、地形波、烟囱效应和气压递减 | 风速/温度/压力剖面、体积流量，与相似律、实验或理论曲线比较 |
| `Chemistry` | 41 | 41/41 | 第 10.4、10.5、10.6、10.7 节 | `reactionrate_*`、`ign_delay_*`、`EDC_*`、`load_bal_*` | EDC 无限快化学、Arrhenius 有限速率、详细机理点火延迟、反应热、负载均衡及串/并行一致性 | 物种浓度、温度、HRR、点火延迟、各 MPI 进程负载；与 Cantera/解析值比较 |
| `Complex_Geometry` | 125 | 92/125 | 第 16 章；附录 C；并涉及第 7.1.8、9、14 章 | `geom_simple`、`geom_sphere1*`、`cone_1mesh`、`saad_CC_*`、`shunn3_*`、`sphere_radiate` | GEOM 三角面、球/地形/纹理、坏几何检查、cut-cell、切割通道、MMS、辐射、泄漏、粒子和性能 | 几何预处理错误、面积/体积/质心守恒、L2 误差、摩擦因子、热流、压力；详见本目录已有报告 |
| `Controls` | 12 | 11/12 | 主要由用户指南/附录 A 的控制测试收录 | `activate_vents`、`control_test`、`create_remove`、`cycle_test` | 控制函数、加减乘除/PID、按时间激活或移除对象、外部控制和心跳曲线 | 控制器输出、开关状态、HRR/边界状态是否与设定值一致 |
| `Detectors` | 5 | 5/5 | 用户指南检测器章节；附录 A 18.3 | `aspiration_detector`、`beam_detector`、`objects_dynamic`、`smoke_detector` | 点型/线型探测器、吸气式和光束烟探测器、静态/动态对象探测 | 探测器激活时间、光学浓度、束遮挡或控制状态，与期望值比较 |
| `Energy_Budget` | 10 | 10/10 | 第 7.2 节 | `energy_budget_adiabatic_walls`、`energy_budget_combustion`、`energy_budget_particles`、`test_hrr_3d` | 热释放、对流/辐射/壁面换热、气体混合、固体和粒子能量守恒 | HRR、总焓、边界热通量和能量余额；余额应接近零或在附录 A 容差内 |
| `Extinction` | 2 | 2/2 | 主文未独立列章，附录 A/燃烧模型相关 | `extinction_1`、`extinction_2` | 火焰熄灭、氧浓度/温度与燃烧源项耦合的边界情况 | 熄灭时间、HRR、温度和氧/燃料浓度的期望趋势 |
| `Fires` | 25 | 25/25 | 第 3.8.5、3.9、3.10 节及第 7、10、12 章相关案例 | `box_burn_away*`、`couch`、`fire_const_gamma`、`circular_burner` | 固体烧蚀/烧尽、规定火源、常比热比、隧道流、圆形燃烧器和火源下限温度 | 燃料质量、MLR、HRR、温度和压力；与解析质量/热释放比较 |
| `Flowfields` | 45 | 40/45 | 第 3、5、8 章 | `blasius_*`、`cyl_test_*`、`symmetry_test`、`velocity_bc_test`、`divergence_test_*` | 基本流、边界层、轴对称、速度边界条件、对称性、散度约束和孔洞影响 | 速度/压力/温度剖面、散度最小/最大值、左右对称误差、边界条件一致性 |
| `Heat_Transfer` | 46 | 45/46 | 第 5、9、11 章及用户指南表面温度章节 | `back_wall_test`、`convective_cooling`、`heat_conduction_*`、`ht3d_*` | 一维/三维固体导热、对流冷却、网格边界传热、浸没边界、热流边界和热电偶 | 表面/内部温度、热流、前后壁能量；与解析解或有限元结果比较 |
| `HVAC` | 38 | 38/38 | 第 14 章 | `ashrae7_*`、`fan_test`、`HVAC_mass_conservation`、`HVAC_leak_exponent`、`HVAC_mass_transport*` | 管段/节点损失、风机/过滤器/阻尼器、质量与能量守恒、泄漏压力指数、瞬态输运 | 流量、压差、温度、焓和质量；与 ASHRAE/解析网络解比较 |
| `Miscellaneous` | 21 | 21/21 | 第 17 章输出及用户指南输入功能 | `devc_interpolation_*`、`external_test`、`init_overlap`、`layer_*` | DEVC 插值、外部数据、重叠 INIT、多网格层高、输入输出边界情况 | 插值误差、层高、初始化字段和外部数据一致性 |
| `NS_Analytical_Solution` | 12 | 12/12 | 第 3.1 节 | `ns2d_16`、`ns2d_32`、`ns2d_*_nupt1` | 二维 Navier--Stokes 解析解；无黏和有黏情形分别考核对流、黏性项 | 中心速度时间历程和 RMS 误差；网格收敛目标为二阶 |
| `Pressure_Effects` | 12 | 12/12 | 第 3.2、3.9、3.10 节及第 8.3 节 | `isentropic`、`isentropic2`、`pressure_boundary`、`pressure_rise`、`zone_break_*` | 连续性方程、等熵/非等熵注气、压力边界、分区压力和开闭区域 | 压力、密度、温度、流量及压力平衡，与解析关系比较 |
| `Pressure_Solver` | 28 | 28/28 | 第 3、8 章；部分属于开发者压力求解测试 | `dancing_eddies_*`、`pressure_solver_*`、`random_obstructions_fft` | 压力泊松求解、预条件器、嵌入网格压力传递、涡街和随机障碍物 | 压力残差、迭代次数、涡量/速度和并行一致性 |
| `Pyrolysis` | 87 | 87/87 | 第 12 章 | `anca-couce-*`、`tga_sample`、`pine_wood_TGA`、`spyro_cone_demo_*`、`ice_cube` | 固体热解质量/能量守恒、TGA/MCC 解释、炭化、两步反应、SPyro、熔化和收缩膨胀 | 质量、MLR、HRRPUA、温度、残炭和反应组分；与实验/解析热解曲线比较 |
| `Radiation` | 73 | 72/73 | 第 9 章 | `geom_rad`、`radiation_box`、`radiation_shield`、`TC_view_factor`、`droplet_absorption` | 视角因子、盒内辐射、平板/球体、屏蔽、气体/粒子衰减、热电偶和液滴吸收 | 视角因子、入射/净热流、壁温、粒子吸收能，与解析辐射解比较 |
| `Restart` | 18 | 11/18 | 第 8.11、16.6 节及用户指南重启章节 | `clocks_restart_*`、`csvf_restart_*`、`device_restart_*`、`geom_restart` | FDS/Smokeview 文件重启、设备状态、控制状态、GEOM 内部温度连续性 | 重启前后 HRR、温度、设备和内部状态的差异；应在容差内 |
| `Scalar_Analytical_Solution` | 78 | 77/78 | 第 3.2--3.5 节 | `compression_wave_*`、`pulsating_*`、`move_slug`、`soborot`、`saad`、`shunn3` | 连续性波、标量平移、固体旋转、可变密度投影和制造解 | 标量/密度/速度/压力 L2 误差、时间阶和空间阶 |
| `Species` | 67 | 65/67 | 第 3.8、3.9、10.1--10.3、10.8、10.11、10.14 节 | `bound_test_*`、`burke_schumann_*`、`humidity`、`methane_flame`、`water_evaporation_*` | 物种边界、湿度、产物收率、混合分数、FED/FIC、冷凝/蒸发和比热比 | 物种质量分数和总和、温度、密度、湿度、压力及毒性剂量 |
| `Sprinklers_and_Sprays` | 54 | 53/54 | 第 9.7--9.10、13.3--13.5 节 | `bucket_test_*`、`water_evaporation_*`、`geom_particle_cascade_2`、`cascadempi` | 喷头激活、水滴蒸发、液滴撞击/沿固体表面运动、喷雾辐射和 MPI 跨网格 | 水质量、粒子数/轨迹、蒸发热、壁面通量和跨网格守恒 |
| `Thread_Check` | 2 | 2/2 | 第 8.8 节 | `race_test_1`、`race_test_4` | OpenMP 线程竞争、串行/并行结果一致性 | 结果文件差异、运行时错误、线程诊断 |
| `Timing_Benchmarks` | 16 | 16/16 | 指南持续集成/安装和性能支持，不是物理精度章节 | `openmp_test64*`、`openmp_test128*` | 网格规模、OpenMP 线程数、并行性能和计时可重复性 | CPU/wall time、加速比、并行效率；不能用“误差在容差内”解释 |
| `Turbulence` | 25 | 21/25 | 第 4 章 | `csmag_*`、`dsmag_*`、`deardorff_*`、`vreman_*`、`wale_*`、`jet_*` | 衰减各向同性湍流、Smagorinsky/动态 Smagorinsky/Deardorff/Vreman/WALE 和射流衰减 | 动能时间历程、能谱、中心线速度，与 CBC 数据或标度律比较 |
| `WUI` | 50 | 48/50 | 第 15 章；并涉及第 10.13、13 章 | `Bova_*`、`bulk_density_file`、`vegetation_drag_*`、`LS4_ember_*`、`char_oxidation_*` | 野外火蔓延 level-set、植被阻力/辐射吸收、含水率、炭氧化、余烬生成和点燃 | 火线椭圆误差、余烬产率/权重、压力损失、植被质量和 HRR |

### 3.1 目录统计的解释

- `Complex_Geometry` 的 125 个输入中，主目录 116 个，`CompGeom_Scaling` 9 个；脚本主动运行 92 个，缩放目录没有并入普通 nightly 行。
- `Adaptive_Mesh_Refinement`、`Restart`、`Turbulence`、`WUI` 等目录中存在人工、替代模型或未纳入当前脚本的输入，不能仅用目录文件数评价回归覆盖。
- active 数量 861 是脚本命令数；若同一输入以不同 `-p/-o` 选项出现，应在 CI 报告中按“输入文件 + 运行模式”保留唯一记录。

## 4. 按指南章节重排的验证内容

下表是适合放在项目总表中的“章节级”版本。每一行先说明指南验证问题，再说明桌面目录中的具体实现。

| 指南章节 | 具体验证问题 | 典型模型/工况 | 对应桌面目录 | 推荐记录的结果 |
|---|---|---|---|---|
| 第 3 章 Basic Flow Solver | 基本动量、连续性和标量输运离散是否收敛 | 规则笛卡尔网格；解析速度场、脉动波、压缩波、平移/旋转标量；DNS、固定 CFL | `NS_Analytical_Solution`、`Scalar_Analytical_Solution`、`Flowfields`、`Pressure_Effects` | 解析值与 FDS 值、RMS/L2 误差、误差随 `Δx` 或 `Δt` 的斜率 |
| 第 3.4 Saad | 可变密度压力投影的时间精度 | 1D 周期域、两种密度组分、零扩散；CFL 0.25/0.125/0.0625 | `Scalar_Analytical_Solution`、`Complex_Geometry/saad_CC_*` | 三个步长的时间阶；Complex Geometry 变体指南给出约 `p=2.0053` |
| 第 3.5 Shunn | 可变密度制造解的整体空间/时间精度 | 周期方域、解析源项、CHARM 与 GODUNOV 通量限制器、多分辨率 `N={32,64,128,256,320}` | `Scalar_Analytical_Solution`、`Complex_Geometry/shunn3_*` | `ρ、Z、u、H、p` 的 L2 误差；CHARM 的标量/速度约二阶，GODUNOV 约一阶，压力约一阶 |
| 第 4 章 Turbulence | 亚格子模型能否再现衰减湍动能和能谱 | CBC 衰减各向同性湍流；`Cs=0.2`、动态模型、Deardorff、Vreman、WALE；32³/64³ 网格 | `Turbulence` | 总动能、能谱、耗散趋势及与 CBC 过滤数据的差异 |
| 第 5 章 Boundary Effects | 壁面剪切、热边界层、近壁网格和复杂边界是否正确 | Poiseuille/Moody、Blasius、Pohlhausen、`y+`、自然/强制对流、带肋方管；规则与 GEOM 对照 | `Flowfields`、`Heat_Transfer`、`Complex_Geometry` | 摩擦因子 `f`、Nusselt 数、速度/温度剖面、网格收敛 |
| 第 6 章 Atmospheric Flows | 大气边界层剖面和地形/稳定度效应是否正确 | Monin--Obukhov 稳定/不稳定剖面、Ekman 层、风场和地形波 | `Atmospheric_Effects` | `U/V/T` 高度剖面、压力递减和体积流量 |
| 第 7 章 Mass and Energy Conservation | 质量、物种、热量和能量预算是否闭合 | 入口/出口质量通量、气相/固相/粒子源项、反应放热、绝热/冷壁 | `Energy_Budget`、`Species`、`Complex_Geometry` | `in-out+generation` 余额、总焓变化、HRR 与边界热量 |
| 第 8 章 Checking for Coding Errors | 代码和边界实现是否出现可重复的逻辑错误 | 对称性、速度边界、散度、重叠网格、INIT、孔洞、OpenMP、层高和重启 | `Flowfields`、`Pressure_Solver`、`Controls`、`Miscellaneous`、`Restart`、`Thread_Check` | 错误文本、对称差、散度界、迭代数、重启前后差和线程一致性 |
| 第 9 章 Thermal Radiation | 视角因子、辐射传输、吸收/发射和屏蔽是否正确 | 热平板、直角平板、盒体、热气层、热球、液滴、辐射屏和热电偶 | `Radiation`、`Heat_Transfer`、`Sprinklers_and_Sprays`、`Complex_Geometry` | 视角因子、入射/净热流、壁温和吸收能；例如热球最近壁理论值 `σT⁴/4=5.065 kW/m²` |
| 第 10 章 Species and Combustion | 物种性质、反应速率、产物、点火、混合分数和气溶胶耦合是否正确 | 简单化学、EDC 无限快、Arrhenius 有限速率、Cantera 点火延迟、湿度、FED/FIC、冷凝 | `Chemistry`、`Species`、`Extinction`、`Aerosols`、`Fires` | 物种质量分数和产率、温度/压力、HRR、点火时间和质量守恒 |
| 第 11 章 Heat Conduction | 固体一维/三维导热、对流冷却和网格界面传热是否正确 | 平板解析解、温变热物性、绝热/指定热流、钢梁/球/多层固体；有限元对照 | `Heat_Transfer` | 表面/背面温度、热流、固体能量和 FE/解析误差 |
| 第 12 章 Pyrolysis | 表面、颗粒和多组分固体热解的质量/能量是否守恒 | 非炭化/炭化表面、TGA/MCC、两步反应、液面蒸发、SPyro、冰融化 | `Pyrolysis`、`Fires`、`WUI` | 质量、MLR、HRRPUA、残炭、温度和反应组分 |
| 第 13 章 Lagrangian Particles | 粒子拖曳、动量/能量交换、蒸发和随机运动是否正确 | 无阻力粒子、自由流拖曳、植被/多孔介质、终端速度、水滴蒸发和表面撞击 | `Sprinklers_and_Sprays`、`Aerosols`、`WUI`、`Complex_Geometry` | 轨迹、终端速度、流固总动量、粒子/气相质量和能量 |
| 第 14 章 HVAC | 风管网络的流量、损失、压力、能量、泄漏和瞬态输运是否正确 | 固定流量/二次损失/表格风机、节点、滤网、泄漏指数、ASHRAE 7、多区域瞬态输运 | `HVAC` | 风量、压差、焓、温度、质量平衡和 ASHRAE 解析值 |
| 第 15 章 Wildland Fire Spread | level-set 火线、余烬产生和余烬点燃是否正确 | 椭圆火线、无风/有风、植被燃料层、余烬生成高度和点火概率 | `WUI` | 火线位置误差、余烬产率、平均权重因子和点燃概率 |
| 第 16 章 Unstructured Geometry | GEOM/Smokeview 几何、cut-cell 算法和复杂边界守恒是否正确 | 闭合三角面、XB 生成体、递归/经纬球、DEM 地形、纹理、锥体退化 cut-cell、MMS、Poiseuille、热流/泄漏 | `Complex_Geometry` | 错误检查、面积/体积/质心、L2 收敛、摩擦因子、热流和压力；见第 5 节 |
| 第 17 章 Outputs | 统计量和插值输出是否正确 | 1 m³ 盒内正交射流；DEVC RMS、协方差、互相关和插值 | `Miscellaneous`、`Controls`、`Detectors` | 统计量逼近全时间历史解析值，插值误差在容差内 |

## 5. Complex_Geometry 与指南第 16 章的直接对应

这是桌面目录中与本 PDF 对应最直接的一组，指南印刷页为 275--293。

| 指南小节 | 桌面输入卡 | 问题描述 | 关键模型和参数 | 期望验证结果 |
|---|---|---|---|---|
| 16.1 坏几何 setup check | `geom_bad_inconsistent_normals`、`geom_bad_inverted_normals`、`geom_bad_non_manifold_edge`、`geom_bad_open_surface` | 故意构造法向错误、非流形边和开口表面 | `POSITIVE_ERROR_TEST=T`；通过错误文本触发 `SUCCESS` | `.err` 中出现预期错误；`geom_positive_errors.m` 检查文本 |
| 16.2.1 简单几何 | `geom_simple` | 3 个顶点、1 个三角面 | `VERTS/FACES/SURF_ID` | GEOM 预处理和 Smokeview 三角面显示正确 |
| 16.2.2 XB 立方体 | `geom_obst`、`geom_simple2` | 用 `XB` 定义、并可用 `MOVE` 旋转的块体 | `MOVE AXIS/ROTATION_ANGLE`、GEOM 与 OBST 对照 | 几何位置、旋转和网格一致性 |
| 16.2.3 递归球 | `geom_sphere1a-f` | 从 20 面二十面体逐级细分；每级三角数乘 4 | `N_LEVELS=0..5`、`SPHERE_RADIUS`、`SPHERE_ORIGIN` | 三角形近似等边；几何分辨率随级别增加 |
| 16.2.3 经纬球 | `geom_sphere3a-f` | 经度/纬度切分，极点附近长宽比增大 | `(N_LAT,N_LONG)=(3,6)..(96,192)` | 生成球的拓扑和显示纹理正确 |
| 16.2.4 DEM 地形 | `geom_terrain`、`geom_terrain2` | 矩形高程阵列和 terrain cut-cell | `ZVALS`、`IS_TERRAIN=T`、外边界 OPEN | 地形高度、CELL PHASE 和 cut-cell 正确 |
| 16.2.5--16.2.7 纹理 | `geom_texture*` | 三角面、多纹理、球面纹理映射方法对照 | `TEXTURE_MAP`、`TEXTURE_ORIGIN`、`TEXTURE_MAPPING='SPHERICAL'` | Smokeview 纹理位置/方向一致 |
| 16.3 锥体 cut-cell | `cone_1mesh` | 316 vertices、628 triangles；同一 Cartesian cell 内 piercing、split、alignment | 单网格 `5×5×12`；锥体 `H=4DB` | cut-face、polyhedron、最大气体子单元和守恒正确 |
| 附录 C / 表 16.1 | `cone_1mesh`、`geom_mass_file_test` | 三角面和切割面计算表面积，固体/气体体积及气体质心 | 相对误差按浮点精度检查 | 指南示例中面积约 `6.25e-15`、体积约 `2.21e-14`、质心约 `1.86e-15` |
| 16.4.1 Saad cut-cell | `saad_CC_explicit_512_cfl_p25/p125/p0625` | 人为 cut-cell 区域不应改变可变密度投影时间阶 | `Nx=512`、`x=[-1,1]`、密度比 10:1、零扩散、CFL 0.25/0.125/0.0625 | 时间阶约 2；指南给出的 Complex Geometry 变体 `l2(p)=2.0053` |
| 16.4.2 Shunn cut-cell | `shunn3_*_cc_exp_{chm,gdv}` | cut-cell 区域的整体空间/时间误差 | `N={32,64,128,256,320}`、周期边界、CHARM/GODUNOV | CHARM 对 `ρ/Z/u` 约二阶，GODUNOV 约一阶，压力约一阶 |
| 16.4.3 旋转立方体 MMS | `rotated_cube_{0,27,45}deg_*` | 倾斜 GEOM 下应力法和标量传输 | 0°、`arctan(1/2)=26.565°`、45°；CFL=0.1；`N=32..320` | 倾斜几何标量通常一阶；压力一阶；0° 与 OBST 对照可达更高阶 |
| 16.4.4 双 GEOM 泊肃叶流 | `geom_poiseuille_N*_{a,na,nah}_theta0_stm` | 两个几何构成高 1 m、长 10 m 通道 | `ρ=1.165`、`μ=0.025`、`dp/dx=-1 Pa/m`、`Re_H≈155`；`f_an=24/Re_H`；N=10/20/40/80 | 摩擦因子误差随 `Δz` 收敛；比较 `h=0`、`Δz/3`、固定偏移 |
| 16.5.1 辐射球 | `sphere_radiate` | 773.15 K、半径 1 m 热球向 0 K 冷壁辐射 | 4 m 立方域、ε=1、无对流；100 radiation angles | 最近壁热流理论值 `5.065 kW/m²` |
| 16.5.2 泄漏球 | `sphere_leak` | 中空球内 0.008 m³/s 注气，通过 0.0001 m² 泄漏 | `Δp=ρ∞/2·(Vdot/A)²≈3840 Pa` | 球内压力上升逼近解析值 |
| 16.6 复杂几何重启 | `geom_restart` 相关输入/重启文件 | 几何底部加热，700 s 重启并与连续计算比较 | GEOM 固体内部温度、RESTART | 重启前后内部温度、HRR 和设备历史连续 |

已有的复杂几何逐卡报告见：[Complex_Geometry_case_report.md](F:/DESK/1FireDynamicsSimulation/SHENBBAO/Verification/Complex_Geometry/Complex_Geometry_case_report.md)。该报告还包括网格/边界/工况参数和当前构建的短算例核对。

## 6. 桌面已有六个实验算例表的重新归类

桌面已有的 `FDS六类验证算例整理报告.md`、`六类FDS算例整理.md` 和 `FDS三类算例模型详细报告.md` 主要讨论以下六个实验对照算例：

| 层级 | 算例 | 物理问题 | 主要比较量 | 应归入的正式类别 |
|---|---|---|---|---|
| Validation | `cabinet_01` | NIST/NRC 大机柜、前门关闭、格栅和泄漏、50/100/200/400 kW 甲烷规定火源 | 柜内外温度、钢板/板式温度计、泄漏和烟气流动 | FDS Validation Guide/NUREG 实验验证，不是本 PDF 第 16 章的 GEOM verification |
| Validation | `cabinet_06` | NIST/NRC 大机柜、前门和顶部/侧面开口、200/400/700/1000 kW | 柜内外温度、开口羽流、HRR 敏感性 | 同上 |
| Validation | `FM_SNL_01` | 约 10 ACH 的强制通风隔间、约 516 kW 丙烯火 | HGL 温度/高度、顶棚射流、中心羽流 | 实验 validation |
| Validation | `FM_SNL_03` | 相同房间/通风、约 2000 kW 丙烯强火 | HGL、羽流和烟层下降速率 | 实验 validation |
| Validation | `VTT_01` | 大空间大厅、约 1.86 MW 正庚烷池火、自然渗漏近似 | 大尺度羽流、温度分层、HGL、壁面热流 | 实验 validation |
| Validation | `VTT_03` | 约 3.64 MW、大门开启、11 m³/s 屋顶机械排烟 | 烟层、羽流、排烟和墙面热流 | 实验 validation |

这些六算例的详细网格、HRR、材料、开口和测点表可以保留，但应在项目总表中单独增加 `Verification/Validation 层级` 列。它们不能作为第 3--16 章解析/代码 verification 的替代证据。

### 6.1 对原有六类表格的必要纠正

1. `cabinet_01` 和 `cabinet_06` 的开口建模不能合并成一句“HOLE + GRILL + LEAK”：当前输入中 `cabinet_01` 明确定义了 GRILL 和四个 HVAC LEAK，而 `cabinet_06` 主要使用显式 `HOLE`，没有同样的 GRILL/HVAC LEAK 组合。
2. FM/SNL 当前输入用 6 个 `SURF VOLUME_FLOW=-0.63` 送风面和一个 `OPEN` 排风口，没有 HVAC 名录，不能写成“HVAC 网络”。
3. VTT_01 的当前输入是两端小 OPEN 泄漏近似；VTT_03 才有两端门和屋顶 `SUCK VOLUME_FLOW=11.0 m³/s`。不能把 VTT_01 写成机械排烟。
4. 当前输入未显式 `SIMULATION_MODE` 的柜体/FM 算例，在本机 FDS 6.10.1 运行时默认为 VLES；VTT 输入显式为 SVLES。报告应区分“LES 数学框架”和“实际运行模式”。
5. `SOOT_YIELD` 是简单烟炱产率，不等于开启了独立烟炱粒径、凝并、氧化和沉积模型。
6. FDS 标准辐射求解应表述为 RTE/FVM 及气体/烟炱辐射性质处理；不能把没有 `WSGG_MODEL=T` 的输入写成 WSGG 模型。

## 7. 建议项目采用的统一验证表字段

为了把桌面现有多个 Word/Markdown 表格合并为可审查的数据表，建议每个输入卡至少保留以下字段：

| 字段 | 填写要求 |
|---|---|
| `层级` | `Verification`、`Validation`、`Sensitivity`、`Code checking` 或 `Performance` |
| `目录/算例` | 与 `.fds` 相对路径一致；不要只写中文简称 |
| `指南章节` | 记录 FDS Verification Guide 的章节号和印刷页；实验算例另记 Validation Guide/原始试验来源 |
| `问题描述` | 用一句话说明数学/物理问题，而不是只写“验证某模型” |
| `实际启用模型` | 按输入卡填写 DNS/LES/VLES/SVLES、湍流、反应、辐射、颗粒、固体导热、cut-cell 等；区分默认与显式设置 |
| `网格与计算` | 每个 MESH 的 IJK、XB、网格尺寸、网格数量、MPI/OpenMP、DT/CFL、T_END |
| `边界条件` | OPEN、MIRROR、PERIODIC、INLET、SUCK、HVAC、GEOM/OBST 的位置、方向、面积、流量和温度 |
| `工况参数` | 材料、物种、密度、黏度、温度、HRR/MLR、辐射分数、颗粒参数等，保留单位 |
| `输出量` | DEVC/BNDF/SLCF/CSV/MASS_FILE 的实际 ID、坐标、采样间隔和积分区域 |
| `期望值/判据` | 解析值、实验值或期望文本；给出相对/绝对误差容差和比较时刻 |
| `状态` | `active`、`manual`、`display-only`、`expected-failure`、`performance`、`not checked` |
| `证据` | FDS `.out/.err`、Expected Results、Matlab/Python 后处理、版本号、源码提交号和运行日期 |

## 8. 当前桌面算例库的复现和审查建议

1. 先固定 FDS 版本、编译器、MPI/OpenMP 设置和源码提交号；附录 A 的结果是版本相关的，不应直接套用到另一版本。
2. 对 `Verification` 算例先做 debug 两步运行，再做 release 全时长运行；检查 `.err`、运行时错误、NaN、越界和除零。
3. 对解析/守恒算例保存 exact/expected 值、误差和容差；对实验 validation 算例保存实验数据、时间对齐和测量不确定度。
4. 将 `Complex_Geometry` 的几何预处理错误、粒子旧卡、纹理缺失和自相交测试缺陷单独列为已知问题，不要计入“全部通过”。
5. 对性能目录只比较 wall time、CPU time、线程/进程扩展性；性能趋势不是物理正确性判据。
6. 运行覆盖应按“文件 + 运行参数”统计。目前整个桌面 Verification 目录为 924 个输入、861 条 active 命令；复杂几何目录为 125 个输入、92 条 active 命令，不能写成 100% nightly 覆盖。

## 9. 结论

桌面上的算例库实际上是一个多层级 V&V 体系，而不是一张“火灾场景清单”：

- 第 3--5 章主要回答基本流、标量、湍流和壁面离散是否正确；
- 第 6--7 章回答大气边界层、质量和能量是否正确；
- 第 8 章回答代码、边界、网格、并行和重启是否可靠；
- 第 9--14 章回答辐射、物种/燃烧、导热、热解、粒子和 HVAC 子模型是否正确；
- 第 15 章回答野外火蔓延和余烬模型是否正确；
- 第 16 章回答 GEOM/cut-cell/复杂边界的几何、守恒、精度和耦合是否正确；
- 第 17 章回答统计和插值输出是否正确；
- 桌面已有 cabinet/FM/VTT 六个算例则提供实验物理 validation，应与上述 verification 分栏管理。

因此，项目总报告应采用“指南章节 + 桌面目录 + 实际输入 + 期望/实验判据 + 运行证据”的结构，而不应把“目录里有 `.fds`”直接等同于“模型已经验证”。

