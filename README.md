# A股热门股票 Top 100

每日自动更新的A股人气榜，展示当前交易日最受关注的100只股票，按网络热度排序。

**在线预览**: https://madeye.github.io/hot-stock-china/

## 功能特点

- 展示东方财富股吧人气榜 Top 100 股票
- 实时股价和涨跌幅
- 内嵌 20 日 K 线图（使用 ECharts）
- 每个交易日北京时间 15:00 自动更新
- 响应式设计，支持移动端

## 数据来源

- 人气排行：[东方财富股吧人气榜](https://guba.eastmoney.com/rank/)
- 实时行情：东方财富/新浪财经
- K 线数据：新浪财经

## 本地运行

```bash
# 安装依赖
pip install requests

# 抓取数据并生成页面
python fetch_hot_stocks.py

# 启动本地服务器查看
python -m http.server 8000
# 访问 http://localhost:8000
```

## 自动更新

通过 GitHub Actions 每个交易日（周一至周五）北京时间下午 3 点自动更新数据并部署到 GitHub Pages。

## 免责声明

本项目仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。

## License

[MIT](LICENSE)
