# 城市形态—文化相似性外部验证

本目录用论文数据中的 Covered Index（CI）检验：卫星影像提取的城市形态相似性，是否与独立的 WVS/EVS 文化距离一致。

## 外部数据

- `cultural_distance_PSW2024.csv`：基于 WVS/EVS 问卷的国家对文化距离，使用最新的 2021 波次。来源：https://www.geopoliticaldistance.org/cultural-distance
- `dist_cepii.dta`：CEPII GeoDist 的距离、共同语言、殖民关系等变量。来源：https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=6
- `ne_10m_admin_0_countries.zip`：Natural Earth 国家边界，用于按城市栅格中心建立国家代码。来源：https://www.naturalearthdata.com/

SHA-256：

```text
d6ed44a53f5a0d886299ae520fbf155da83526666548242ff3208a1a13b7e6cd  cultural_distance_PSW2024.csv
a6695221f1dc9e60df0bc5b3a6d72605efdc7d0def1d145391e096c1eb3b737a  dist_cepii.dta
ce1ac7036499a0edd641fbc093cd209a98f96a49d2eca8480aaacad35138a7f6  ne_10m_admin_0_countries.zip
```

## 运行

先按仓库根目录 README 解压 PCL 数据，并把三个外部数据源下载到 `cultural_validation/external/`。脚本预期的主要文件名为：

```text
external/cultural_distance_PSW2024.csv
external/dist_cepii.dta
external/natural_earth/ne_10m_admin_0_countries.shp
```

```bash
python3 scripts/run_validation.py
```

需要 Python 3、NumPy、pandas、SciPy、Matplotlib 和 GDAL Python bindings。脚本会重建 K=200、500、1000 的全部城市对 CI，合并外部数据，运行相关、标准化 OLS 和 999 次国家标签置换检验。

## 主要输出

- `output/RESULTS.md`：主要数值结果。
- `output/ci_vs_cultural_distance.png`：三种聚类尺度的可视化。
- `output/ci_vs_cultural_distance_nature.pdf`：Nature 风格的可编辑双栏图。
- `output/ci_vs_cultural_distance_nature.png`：Nature 风格的 600 dpi PNG。
- `output/ci_vs_cultural_distance_nature.tif`：Nature 风格的 600 dpi TIFF。
- `output/analysis_dataset_all_pairs.csv`：完整合并数据。
- `output/regression_results.csv`：模型系数。
- `output/validation_results.json`：机器可读汇总。
- `output/city_country_mapping.csv`：城市—国家映射审计表。

Nature 风格版本可单独重新生成：

```bash
sudo apt install fonts-liberation2  # Arial 度量兼容的开源字体
python3 scripts/plot_nature_style.py
```

额外交叉验证使用 Hofstede 官方六维文化矩阵、CC0 EcoCultural Dataset 和 CEPII 共同语言关系。原始外部数据不随仓库重新分发，来源和变量选择见 `output/ADDITIONAL_VALIDATION.md`；准备好外部文件后可运行：

```bash
python3 scripts/run_additional_cross_validation.py
```

按主图的 Nature 风格绘制每个外部文化指标的 K=200/500/1000 三联图：

```bash
python3 scripts/plot_additional_nature_style.py
```

输出文件以 `output/additional_*_nature` 开头，每个指标提供 PDF、600 dpi PNG 和 600 dpi TIFF。

## 解释边界

文化距离是国家层级指标，同一国家内的城市文化差异无法识别，因此主分析排除了同国城市对。城市对共享城市与国家，普通逐行显著性会夸大有效样本量；结论以国家标签置换检验为主。结果支持外部关联效度，不单独识别文化影响城市形态的因果方向。
