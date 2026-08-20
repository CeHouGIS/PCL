# PCL 文件分类索引

本索引按文件的实际用途分类，而不是简单地按扩展名分类。项目中的 TIFF
既包括聚类栅格数据，也包括论文输出图，二者用途不同。为保证现有脚本仍可运行，
本次只建立分类导航，不移动或重命名原文件。

## 分类总览

| 类别 | 主要位置 | 内容 | 管理建议 |
| --- | --- | --- | --- |
| 源代码 | 各实验目录的 `scripts/`、`feature/calculate_hi.py` | 数据处理、统计分析和绘图脚本 | 纳入 Git 管理 |
| 原始数据与外部数据 | `data/`、`cultural_validation/external/`、根目录历史关系工作簿 | 原始压缩包、外部文化与地理数据、历史关系矩阵 | 保留原文件；大型或受许可限制的数据不提交 Git |
| 数值特征数据 | `feature/` | PCL 与 MoCo 的 NumPy 特征及辅助表格 | 体积最大，按模型与特征类型分层保存 |
| 聚类栅格数据 | `clusters/` | K=200、500、1000 的分块 TIFF 聚类结果 | 属于分析数据，不是论文图片 |
| 合并栅格数据 | `merge/`、`feature/Moco/merge/` | 按城市合并后的 TIFF 栅格 | 属于中间或派生数据 |
| 分析结果数据 | 各实验目录的 `output/` | CSV、JSON、NPY、NPZ、TeX 等结果与审计表 | 可复现的小型汇总结果适合纳入 Git |
| 结果图片 | 各实验目录的 `output/` | PNG、TIFF 和 PDF 格式的图表、地图 | PNG 用于预览，PDF 用于编辑，TIFF 用于投稿 |
| 项目文档 | 根目录及各实验目录的 `README.md`、结果说明 Markdown | 方法、复现说明和结果解释 | 纳入 Git 管理 |
| 压缩归档 | `data/PCL.tar.gz` | PCL 原始数据归档 | 作为只读源文件保留 |
| 缓存与临时文件 | 各 `scripts/__pycache__/`、`*.pyc`、`feature/.@__thumb/` | Python 缓存和缩略图临时文件 | 不纳入 Git，可随时重新生成 |

## 1. 源代码

共 20 个 Python 文件。绝大多数实验均采用“计算脚本 + 绘图脚本”的组织方式：

- `cultural_validation/scripts/`：文化距离验证及附加交叉验证。
- `direct_tie_layer_validation/scripts/`：直接历史联系验证。
- `dyadic_dependence_validation/scripts/`：城市对依赖诊断和回归。
- `five_type_interaction_validation/scripts/`：五类文化同源互动分析。
- `geographic_baseline_validation/scripts/`：地理距离基线分析。
- `global_ci_activation/scripts/`：全球城市 CI 激活地图。
- `k1000_validation_figures/scripts/`：K=1000 汇总图。
- `morphology_concordance_validation/scripts/`：形态一致性验证。
- `shared_regime_validation/scripts/`：共同历史政权验证。
- `feature/calculate_hi.py`：特征层面的 HI 计算。
- `cultural_validation/requirements.txt`：文化验证所需 Python 依赖。

## 2. 数据

### 原始与外部数据

- `data/PCL.tar.gz`：约 18 MB 的原始 PCL 数据归档。
- `historical_city_connection_layers_138x138.xlsx`：历史城市连接分层矩阵。
- `historical_city_direct_ties_138x138.xlsx`：历史城市直接联系矩阵。
- `cultural_validation/external/`：文化距离、CEPII 地理关系、Natural Earth
  边界和附加文化指标。

### 特征数据

`feature/` 约 1.6 GB，是仓库中占用空间最大的类别：

- `feature/PCL/spatiotemporal/`：PCL 时空特征。
- `feature/Moco/feature_self/`：自对比 MoCo 特征。
- `feature/Moco/feature_spatial/`：空间 MoCo 特征。
- `feature/Moco/feature_temporal/`：时间 MoCo 特征。
- `feature/Moco/feature_temporal_new/`：新版时间 MoCo 特征。
- `feature/Moco/feature_spatial_temporal/`：时空 MoCo 特征。
- `feature/Moco/merge/`：MoCo 合并栅格。
- `feature/colonial_information.xlsx`、`feature/HI_recalculated.csv`：辅助表格。

### 聚类与合并栅格

- `clusters/200/`、`clusters/500/`、`clusters/1000/`：共约 40,408 个城市分块
  TIFF 栅格，分别对应三种聚类尺度。
- `merge/200/`、`merge/500/`、`merge/1000/`：共约 391 个城市级合并 TIFF。

这些 TIFF 是模型输入或派生栅格数据，不应归入论文结果图片。

## 3. 图片与出版图稿

结果图片统一位于各验证模块的 `output/` 目录：

- `.png`：便于 README、网页和日常预览。
- `.pdf`：矢量或可编辑出版版本。
- `.tif`：高分辨率投稿版本，通常也是单个文件中占用空间最大的结果。

主要图片目录包括：

- `cultural_validation/output/`
- `direct_tie_layer_validation/output/`
- `dyadic_dependence_validation/output/`
- `five_type_interaction_validation/output/`
- `geographic_baseline_validation/output/`
- `global_ci_activation/output/`
- `k1000_validation_figures/output/`
- `morphology_concordance_validation/output/`
- `shared_regime_validation/output/`

## 4. 分析结果与文档

各 `output/` 目录中的 CSV、JSON、NPY、NPZ 和 TeX 文件属于结果数据：

- CSV：汇总表、分析数据集和审计表。
- JSON：机器可读的统计结果与元数据。
- NPY/NPZ：置换检验零分布或中间数值数组。
- TeX：论文回归表和审稿回复素材。
- `RESULTS.md`：面向阅读者的结果摘要。

项目文档采用两级结构：根目录 `README.md` 提供总览，各验证目录的
`README.md` 说明该实验的数据、方法、结果和复现命令。

## 5. 缓存与临时文件

当前可识别的临时内容包括 20 个 `.pyc` 文件，以及对应的
`scripts/__pycache__/` 目录；`feature/.@__thumb/` 中还有一个空的缩略图错误文件。
这些文件均不是研究数据，且已被根目录 `.gitignore` 的相关规则排除。

## 6. Git 管理边界

仓库目前只跟踪代码、说明文档、小型汇总数据和部分出版图片。`feature/`、
`clusters/`、`merge/`、外部数据、部分置换数组以及原始历史工作簿被排除在
Git 之外。这一边界可以避免将大型数据或不可再分发的数据误提交到版本库。

工作区中存在尚未提交的修改、新文件和删除记录。在这些改动合并或确认前，
不建议批量移动现有目录；如果以后需要物理归档，应同时修改脚本中的相对路径，
并完成一轮全流程复现测试。
