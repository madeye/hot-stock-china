#!/usr/bin/env python3
"""
抓取东方财富人气榜Top100股票数据和K线数据
生成静态HTML页面
使用新浪财经接口获取K线数据（更稳定）
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
import random
import re
from datetime import datetime, timedelta
import os

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

def create_session():
    """创建带重试机制的session"""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.trust_env = False  # 禁用系统代理
    return session

SESSION = create_session()

def get_hot_stocks():
    """获取东方财富人气榜Top100股票"""
    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    headers = {
        **HEADERS,
        'Host': 'emappdata.eastmoney.com',
        'Origin': 'https://guba.eastmoney.com',
        'Referer': 'https://guba.eastmoney.com/',
        'Content-Type': 'application/json',
    }

    data = {
        'appId': 'appId01',
        'globalId': 'bfb8aa53-5044-4a02-b979-1082731e3657',
        'marketType': '',
        'pageNo': 1,
        'pageSize': 100,
    }

    try:
        response = SESSION.post(url, json=data, headers=headers, timeout=30)
        result = response.json()
        if result.get('code') == 0:
            return result.get('data', [])
    except Exception as e:
        print(f"获取人气榜失败: {e}")

    return []

def get_stock_kline_sina(stock_code, market, days=20):
    """使用新浪财经接口获取K线数据"""
    # 构建新浪股票代码格式
    if market == 1:  # 沪市
        symbol = f"sh{stock_code}"
    else:  # 深市
        symbol = f"sz{stock_code}"

    # 使用新浪财经的日K数据接口
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    params = {
        'symbol': symbol,
        'scale': 240,  # 日K
        'ma': 'no',
        'datalen': days,
    }

    headers = {
        **HEADERS,
        'Host': 'money.finance.sina.com.cn',
        'Referer': 'https://finance.sina.com.cn/',
    }

    try:
        response = SESSION.get(url, params=params, headers=headers, timeout=10)
        # 新浪返回的是类JSON格式，需要处理
        text = response.text
        if text and text != 'null':
            # 解析JSON
            data = json.loads(text)
            if data:
                klines = []
                for item in data:
                    klines.append({
                        'date': item.get('day', ''),
                        'open': float(item.get('open', 0)),
                        'close': float(item.get('close', 0)),
                        'high': float(item.get('high', 0)),
                        'low': float(item.get('low', 0)),
                        'volume': int(float(item.get('volume', 0))),
                    })
                return klines
    except Exception as e:
        pass  # 静默失败，不打印错误

    return []

def get_stock_realtime(stock_codes_with_market):
    """批量获取股票实时行情"""
    secids = []
    for code, market in stock_codes_with_market:
        if market == 1:
            secids.append(f"1.{code}")
        else:
            secids.append(f"0.{code}")

    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        'fltt': 2,
        'invt': 2,
        'fields': 'f1,f2,f3,f4,f5,f6,f7,f12,f13,f14,f15,f16,f17,f18',
        'secids': ','.join(secids),
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
    }

    headers = {
        **HEADERS,
        'Host': 'push2.eastmoney.com',
        'Referer': 'https://quote.eastmoney.com/',
    }

    try:
        response = SESSION.get(url, params=params, headers=headers, timeout=30)
        result = response.json()
        if result.get('data') and result['data'].get('diff'):
            stocks = {}
            for item in result['data']['diff']:
                code = item.get('f12', '')
                stocks[code] = {
                    'code': code,
                    'name': item.get('f14', ''),
                    'price': item.get('f2', 0),
                    'change_pct': item.get('f3', 0),
                    'change': item.get('f4', 0),
                    'high': item.get('f15', 0),
                    'low': item.get('f16', 0),
                    'open': item.get('f17', 0),
                    'prev_close': item.get('f18', 0),
                    'volume': item.get('f5', 0),
                    'amount': item.get('f6', 0),
                }
            return stocks
    except Exception as e:
        print(f"获取实时行情失败: {e}")

    return {}

def get_kline_batch(stock_codes_with_market):
    """批量获取K线数据"""
    kline_data = {}
    total = len(stock_codes_with_market)
    success_count = 0

    for i, (code, market) in enumerate(stock_codes_with_market):
        klines = get_stock_kline_sina(code, market)
        if klines:
            kline_data[code] = klines
            success_count += 1
            status = "✓"
        else:
            status = "✗"

        # 显示进度
        progress = (i + 1) / total * 100
        print(f"\r进度: {i+1}/{total} ({progress:.1f}%) 成功: {success_count} {status}", end='', flush=True)

        # 添加随机延迟避免请求过快
        time.sleep(random.uniform(0.1, 0.3))

    return kline_data

def parse_stock_code(sc):
    """解析股票代码，返回(代码, 市场)"""
    if sc.startswith('SH'):
        return sc[2:], 1
    elif sc.startswith('SZ'):
        return sc[2:], 0
    return sc, 0

def generate_html(stocks_data, kline_data):
    """生成静态HTML页面"""

    # 将K线数据转换为JSON
    kline_json = json.dumps(kline_data, ensure_ascii=False)
    stocks_json = json.dumps(stocks_data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股热门股票Top100 - 人气榜</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }}

        .header {{
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .header h1 {{
            font-size: 28px;
            background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .header .update-time {{
            color: #888;
            font-size: 14px;
            margin-top: 8px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        .stock-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}

        .stock-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 16px;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.1);
        }}

        .stock-card:hover {{
            transform: translateY(-4px);
            background: rgba(255,255,255,0.1);
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}

        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }}

        .stock-rank {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
            flex-shrink: 0;
        }}

        .rank-1 {{ background: linear-gradient(135deg, #FFD700, #FFA500); color: #000; }}
        .rank-2 {{ background: linear-gradient(135deg, #C0C0C0, #A0A0A0); color: #000; }}
        .rank-3 {{ background: linear-gradient(135deg, #CD7F32, #8B4513); color: #fff; }}
        .rank-other {{ background: rgba(255,255,255,0.2); color: #fff; }}

        .stock-info {{
            flex: 1;
            margin-left: 12px;
        }}

        .stock-name {{
            font-size: 16px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }}

        .stock-code {{
            font-size: 12px;
            color: #888;
        }}

        .stock-price-section {{
            text-align: right;
        }}

        .stock-price {{
            font-size: 20px;
            font-weight: bold;
        }}

        .stock-change {{
            font-size: 14px;
            margin-top: 2px;
        }}

        .price-up {{ color: #ff4757; }}
        .price-down {{ color: #2ed573; }}
        .price-flat {{ color: #888; }}

        .chart-container {{
            height: 120px;
            margin-top: 12px;
        }}

        .no-chart {{
            height: 120px;
            margin-top: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #555;
            font-size: 12px;
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
        }}

        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: #666;
            font-size: 12px;
        }}

        .footer a {{
            color: #48dbfb;
            text-decoration: none;
        }}

        @media (max-width: 600px) {{
            .stock-grid {{
                grid-template-columns: 1fr;
            }}

            .header h1 {{
                font-size: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>A股热门股票 Top 100</h1>
        <div class="update-time">数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据来源：东方财富人气榜</div>
    </div>

    <div class="container">
        <div class="stock-grid" id="stockGrid"></div>
    </div>

    <div class="footer">
        <p>本页面仅供学习研究使用，不构成投资建议</p>
        <p>数据来源：<a href="https://guba.eastmoney.com/rank/" target="_blank">东方财富股吧人气榜</a></p>
    </div>

    <script>
        const stocksData = {stocks_json};
        const klineData = {kline_json};

        function formatNumber(num) {{
            if (num >= 100000000) {{
                return (num / 100000000).toFixed(2) + '亿';
            }} else if (num >= 10000) {{
                return (num / 10000).toFixed(2) + '万';
            }}
            return num.toFixed(2);
        }}

        function createStockCard(stock, index) {{
            const rankClass = index < 3 ? `rank-${{index + 1}}` : 'rank-other';
            const priceClass = stock.change_pct > 0 ? 'price-up' : (stock.change_pct < 0 ? 'price-down' : 'price-flat');
            const changeSign = stock.change_pct > 0 ? '+' : '';
            const hasKline = klineData[stock.code] && klineData[stock.code].length > 0;

            const card = document.createElement('div');
            card.className = 'stock-card';
            card.innerHTML = `
                <div class="stock-header">
                    <div class="stock-rank ${{rankClass}}">${{index + 1}}</div>
                    <div class="stock-info">
                        <div class="stock-name">${{stock.name}}</div>
                        <div class="stock-code">${{stock.code}}</div>
                    </div>
                    <div class="stock-price-section">
                        <div class="stock-price ${{priceClass}}">${{stock.price ? stock.price.toFixed(2) : '--'}}</div>
                        <div class="stock-change ${{priceClass}}">${{changeSign}}${{stock.change_pct ? stock.change_pct.toFixed(2) : '0.00'}}%</div>
                    </div>
                </div>
                ${{hasKline ? `<div class="chart-container" id="chart-${{stock.code}}"></div>` : '<div class="no-chart">暂无K线数据</div>'}}
            `;
            return card;
        }}

        function renderKlineChart(containerId, klines, isUp) {{
            const container = document.getElementById(containerId);
            if (!container || !klines || klines.length === 0) return;

            const chart = echarts.init(container);

            const dates = klines.map(k => k.date.slice(5));
            const data = klines.map(k => [k.open, k.close, k.low, k.high]);

            const upColor = '#ff4757';
            const downColor = '#2ed573';

            const option = {{
                animation: false,
                grid: {{
                    left: 0,
                    right: 0,
                    top: 5,
                    bottom: 20
                }},
                xAxis: {{
                    type: 'category',
                    data: dates,
                    axisLine: {{ show: false }},
                    axisTick: {{ show: false }},
                    axisLabel: {{
                        fontSize: 9,
                        color: '#666',
                        interval: Math.floor(dates.length / 4)
                    }}
                }},
                yAxis: {{
                    type: 'value',
                    show: false,
                    scale: true
                }},
                series: [{{
                    type: 'candlestick',
                    data: data,
                    itemStyle: {{
                        color: upColor,
                        color0: downColor,
                        borderColor: upColor,
                        borderColor0: downColor
                    }},
                    barWidth: '60%'
                }}]
            }};

            chart.setOption(option);
        }}

        function init() {{
            const grid = document.getElementById('stockGrid');

            stocksData.forEach((stock, index) => {{
                const card = createStockCard(stock, index);
                grid.appendChild(card);
            }});

            // 延迟渲染图表以提高性能
            setTimeout(() => {{
                stocksData.forEach(stock => {{
                    const klines = klineData[stock.code];
                    if (klines) {{
                        renderKlineChart(`chart-${{stock.code}}`, klines, stock.change_pct >= 0);
                    }}
                }});
            }}, 100);
        }}

        // 窗口大小变化时重新渲染图表
        let resizeTimer;
        window.addEventListener('resize', () => {{
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {{
                stocksData.forEach(stock => {{
                    const container = document.getElementById(`chart-${{stock.code}}`);
                    if (container) {{
                        const chart = echarts.getInstanceByDom(container);
                        if (chart) {{
                            chart.resize();
                        }}
                    }}
                }});
            }}, 200);
        }});

        init();
    </script>
</body>
</html>
'''
    return html

def main():
    print("=" * 50)
    print("A股热门股票Top100数据抓取工具")
    print("=" * 50)

    # 1. 获取人气榜股票列表
    print("\n[1/4] 正在获取人气榜Top100...")
    hot_stocks = get_hot_stocks()

    if not hot_stocks:
        print("获取人气榜失败，请检查网络连接")
        return

    print(f"成功获取 {len(hot_stocks)} 只热门股票")

    # 2. 解析股票代码
    stock_codes = []
    for item in hot_stocks:
        sc = item.get('sc', '')
        code, market = parse_stock_code(sc)
        stock_codes.append((code, market))

    # 3. 获取实时行情
    print("\n[2/4] 正在获取实时行情数据...")
    realtime_data = get_stock_realtime(stock_codes)
    print(f"成功获取 {len(realtime_data)} 只股票行情")

    # 4. 获取K线数据（使用新浪接口）
    print("\n[3/4] 正在获取K线数据...")
    kline_data = get_kline_batch(stock_codes)
    print(f"\n成功获取 {len(kline_data)} 只股票K线数据")

    # 5. 整合数据
    stocks_data = []
    for i, item in enumerate(hot_stocks):
        sc = item.get('sc', '')
        code, market = parse_stock_code(sc)

        stock_info = realtime_data.get(code, {})
        stocks_data.append({
            'rank': i + 1,
            'code': code,
            'name': stock_info.get('name', item.get('name', '')),
            'price': stock_info.get('price', 0),
            'change_pct': stock_info.get('change_pct', 0),
            'change': stock_info.get('change', 0),
            'market': market,
        })

    # 6. 生成HTML
    print("\n[4/4] 正在生成HTML页面...")
    html_content = generate_html(stocks_data, kline_data)

    output_file = os.path.join(os.path.dirname(__file__), 'index.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n生成完成！")
    print(f"输出文件: {output_file}")
    print(f"\n可以使用浏览器打开 index.html 查看结果")
    print("或运行: python3 -m http.server 8000 然后访问 http://localhost:8000")

if __name__ == '__main__':
    main()
