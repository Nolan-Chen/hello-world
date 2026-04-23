# hello-world

安卓手机（Termux）运行股票获取脚本说明。

## 1. 安装 Termux

建议通过 F-Droid 安装最新版 Termux。

## 2. 在 Termux 中安装依赖

本项目脚本只依赖 Python 标准库，无需额外 `pip install`。首次仅需安装 Python 与 Git：

```bash
pkg update -y
pkg install -y python git
```

## 3. 拉取项目并运行

```bash
git clone https://github.com/Nolan-Chen/hello-world.git
cd hello-world
python stock_fetch.py --symbols AAPL,MSFT,TSLA
```

安卓上一条命令直接跑（可复制）：

```bash
pkg update -y && pkg install -y python git && git clone https://github.com/Nolan-Chen/hello-world.git && cd hello-world && python stock_fetch.py --symbols AAPL,MSFT,0700.HK,600519.SS
```

也可以换成你关心的代码，例如：

```bash
python stock_fetch.py --symbols 0700.HK,600519.SS,000001.SZ
```

获取全市场 A 股（含北交所）：

```bash
python stock_fetch.py --all-a-share --include-bj --sample 20 --output-csv a_share_full_market.csv --output-json a_share_full_market.json
```

说明：
- `--sample 20` 只在终端展示前 20 条，完整数据写入文件
- `--output-csv` 与 `--output-json` 保存全量结果，方便后续分析

## 4. 成功输出示例

脚本会输出：
- 获取时间
- 代码 / 名称 / 当前价 / 涨跌幅 / 货币 / 交易状态

如果网络或代码有问题，会有明确错误信息，退出码非 0。

## 5. 代码格式说明

- 美股：`AAPL`、`MSFT`
- 港股：`0700.HK`
- 沪市：`600519.SS`
- 深市：`000001.SZ`
