# PCL 文件分类索引

项目文件已经按内容类型实际分开存放。分类后的根目录结构如下：

```text
PCL/
├── code/       Python 代码与依赖文件
├── images/     结果图和出版图稿
├── data/       原始、外部、特征、栅格及结果数据
├── docs/       实验说明、结果说明和 LaTeX 文档
├── cache/      Python 缓存及缩略图临时文件
├── README.md
└── FILE_CLASSIFICATION.md
```

## 代码：`code/`

每项分析拥有独立子目录，Python 文件不再与图片或结果表混放：

- `code/cultural_validation/`
- `code/direct_tie_layer_validation/`
- `code/dyadic_dependence_validation/`
- `code/five_type_interaction_validation/`
- `code/geographic_baseline_validation/`
- `code/global_ci_activation/`
- `code/k1000_validation_figures/`
- `code/morphology_concordance_validation/`
- `code/shared_regime_validation/`
- `code/feature/`

所有脚本均以仓库根目录为路径基准。运行方式为：

```bash
python3 code/<分析名称>/<脚本名称>.py
```

## 图片：`images/`

这里仅存放用于阅读、展示或投稿的成图，并按分析名称分目录：

- PNG：预览和 README 展示版本。
- PDF：矢量或可编辑出版版本。
- TIFF：高分辨率投稿版本。

`data/rasters/` 中的 TIFF 是聚类或城市栅格数据，不属于本图片目录。

## 数据：`data/`

| 子目录 | 内容 |
| --- | --- |
| `data/raw/` | PCL 压缩包和历史城市关系工作簿 |
| `data/external/` | 文化距离、CEPII、Natural Earth 等外部数据 |
| `data/features/` | PCL、MoCo NumPy 特征及辅助数据表 |
| `data/rasters/clusters/` | K=200、500、1000 的分块聚类 TIFF |
| `data/rasters/merge/` | 按城市合并的 TIFF 栅格 |
| `data/results/` | 各项分析产生的 CSV、JSON、NPY 和 NPZ 结果 |

`data/features/` 约 1.6 GB，是占用空间最大的类别；`data/rasters/clusters/`
包含约 40,408 个文件。大型数据、受许可限制的外部数据和部分中间结果继续由
`.gitignore` 排除。

## 文档：`docs/`

各分析的 README、结果说明 Markdown、回归表和审稿材料均按分析名称存放在
`docs/` 下。仓库根目录保留总览 README 和本分类索引，方便从 GitHub 首页访问。

## 缓存：`cache/`

- `cache/python/`：原 Python `__pycache__` 中的 `.pyc` 文件。
- `cache/thumbnails/`：缩略图和临时错误文件。

整个 `cache/` 已排除在 Git 版本控制之外，可在不影响研究数据的情况下清理。

## 输出规则

重跑脚本时，新文件会继续按类别写入：

- 统计表和机器可读结果 → `data/results/<分析名称>/`
- PNG、PDF、TIFF 成图 → `images/<分析名称>/`
- Markdown 和 LaTeX 文档 → `docs/<分析名称>/`

因此后续生成内容不会重新混回代码目录。
