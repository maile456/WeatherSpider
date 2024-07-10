import requests
from lxml import etree
import csv
import sqlite3
from wordcloud import WordCloud
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Pie, Bar, Timeline, Line,Scatter
import matplotlib.pyplot as plt


import matplotlib
matplotlib.use('TkAgg')

def get_weather(url):
    """
    获取指定URL页面的天气信息并返回解析后的数据列表。

    Args:
    - url (str): 包含天气信息的页面URL。

    Returns:
    - list: 包含每日天气信息的字典列表，每个字典包含 'date_time', 'high', 'low', 'weather' 键。
    """
    weather_info = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
    }

    resp = requests.get(url, headers=headers)
    resp_html = etree.HTML(resp.text)

    # 解析天气信息
    resp_list = resp_html.xpath("//ul[@class='thrui']/li")
    for li in resp_list:
        day_weather_info = {}
        # 日期
        day_weather_info['date_time'] = li.xpath("./div[1]/text()")[0].split(' ')[0]
        # 最高气温 (包含摄氏度符号)
        high = li.xpath("./div[2]/text()")[0]
        day_weather_info['high'] = high[:high.find('℃')]
        # 最低气温
        low = li.xpath("./div[3]/text()")[0]
        day_weather_info['low'] = low[:low.find('℃')]
        # 天气
        day_weather_info['weather'] = li.xpath("./div[4]/text()")[0]
        weather_info.append(day_weather_info)

    return weather_info

def write_to_csv(filename, data):
    """
    将天气数据写入CSV文件。

    Args:
    - filename (str): 要写入的CSV文件名。
    - data (list): 包含天气信息的字典列表，每个字典包含 'date_time', 'high', 'low', 'weather' 键。
    """
    with open(filename, "w", newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # 写入表头
        writer.writerow(["日期", "最高气温", "最低气温", '天气'])
        # 写入数据
        for day_data in data:
            writer.writerow([day_data['date_time'], day_data['high'], day_data['low'], day_data['weather']])

    print(f"数据已写入 {filename} 文件。")

def insert_into_sqlite(data, db_name='weather.db'):
    """
    将天气数据插入SQLite数据库中。

    Args:
    - data (list): 包含天气信息的字典列表，每个字典包含 'date_time', 'high', 'low', 'weather' 键。
    - db_name (str): SQLite数据库文件名，默认为 'weather.db'。
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 创建表格
    cursor.execute('''CREATE TABLE IF NOT EXISTS weather (
                        date_time TEXT,
                        high TEXT,
                        low TEXT,
                        weather TEXT
                    )''')

    # 插入数据
    for day_weather_dict in data:
        date_time = day_weather_dict['date_time']
        high = day_weather_dict['high']
        low = day_weather_dict['low']
        weather = day_weather_dict['weather']

        cursor.execute("INSERT INTO weather VALUES (?, ?, ?, ?)", (date_time, high, low, weather))

    conn.commit()
    conn.close()

def generate_weather_timeline_plot(input_file, output_file='weathers.html'):
    # 读取指定的CSV文件，选择编码格式为utf-8
    df = pd.read_csv(input_file, encoding='utf-8')

    # 将日期列的数据类型转换为日期格式
    df['日期'] = pd.to_datetime(df['日期'])

    # 新增一列月份数据（从日期中提取月份）
    df['month'] = df['日期'].dt.month

    # 需要的数据：每个月中每种天气出现的次数
    df_agg = df.groupby(['month', '天气']).size().reset_index()
    df_agg.columns = ['month', 'tianqi', 'count']

    # 绘图部分
    timeline = Timeline()  # 创建时间轴实例
    timeline.add_schema(play_interval=1000)  # 设置播放间隔为1秒（单位是毫秒）

    # 循环遍历每个月份的数据
    for month in df_agg['month'].unique():
        data = (df_agg[df_agg['month'] == month][['tianqi', 'count']]
                .sort_values(by='count', ascending=True)
                .values.tolist())

        # 创建柱状图对象
        bar = Bar()
        bar.add_xaxis([x[0] for x in data])  # x轴是天气名称
        bar.add_yaxis('', [x[1] for x in data])  # y轴是出现次数

        # 设置柱状图的样式
        bar.reversal_axis()  # 横向放置柱状图
        bar.set_series_opts(label_opts=opts.LabelOpts(position='right'))  # 标签放在右侧
        bar.set_global_opts(title_opts=opts.TitleOpts(title='成都2023年每月天气变化'))  # 设置图表标题

        # 将设置好的柱状图添加到时间轴中，标签显示为月份（格式为 数字月）
        timeline.add(bar, f'{month}月')

    # 将设置好的时间轴图表保存为HTML文件
    timeline.render(output_file)

def generate_weather_trend_plot(input_file, output_file='weather_trend.html'):
    # 读取数据
    df = pd.read_csv(input_file, encoding='utf-8')

    # 转换日期格式
    df['日期'] = pd.to_datetime(df['日期'])
    df['month'] = df['日期'].dt.month

    # 按月份和天气类型统计出现次数
    df_agg = df.groupby(['month', '天气']).size().reset_index()
    df_agg.columns = ['month', 'tianqi', 'count']

    # 创建时间轴对象
    timeline = Timeline()
    timeline.add_schema(play_interval=1000)  # 设置播放间隔为1秒（单位是毫秒）

    # 遍历每种天气类型
    for tianqi in df_agg['tianqi'].unique():
        data = (df_agg[df_agg['tianqi'] == tianqi][['month', 'count']]
                .sort_values(by='month', ascending=True)
                .values.tolist())

        # 创建折线图对象
        line = Line()
        line.add_xaxis([x[0] for x in data])  # x轴是月份
        line.add_yaxis(tianqi, [x[1] for x in data], is_smooth=True)  # y轴是出现次数，平滑曲线

        # 设置折线图的系列选项
        line.set_series_opts(
            markpoint_opts=opts.MarkPointOpts(
                data=[opts.MarkPointItem(type_="max", name="最大值")]
            )
        )

        # 设置全局选项，包括标题和数据缩放
        line.set_global_opts(
            title_opts=opts.TitleOpts(title='成都2023年天气趋势'),
            datazoom_opts=opts.DataZoomOpts(type_="slider", range_start=0, range_end=100),
        )

        # 将设置好的折线图添加到时间轴中，并以天气类型作为标签
        timeline.add(line, tianqi)

    # 将时间轴渲染为HTML文件
    timeline.render(output_file)
def generate_scatter_timeline(input_file, output_file='scatter_timeline.html'):
    # 读取数据
    df = pd.read_csv(input_file, encoding='utf-8')
    # 转换日期格式
    df['日期'] = pd.to_datetime(df['日期'])
    df['month'] = df['日期'].dt.month

    # 按月份和天气类型统计出现次数
    df_agg = df.groupby(['month', '天气']).size().reset_index()
    df_agg.columns = ['month', 'tianqi', 'count']

    # 实例化时间轴对象
    timeline = Timeline()
    # 设置时间轴的播放间隔为1秒（单位是毫秒）
    timeline.add_schema(play_interval=1000)

    # 遍历每个月份
    for month in df['month'].unique():
        # 从 df_agg 中筛选出当前月份的数据，并按出现次数排序
        data = (df_agg[df_agg['month'] == month][['tianqi', 'count']]
                .sort_values(by='count', ascending=True)
                .values.tolist())

        # 创建散点图对象
        scatter = Scatter()
        scatter.add_xaxis([x[0] for x in data])  # x轴是天气名称
        scatter.add_yaxis('', [x[1] for x in data])  # y轴是出现次数

        # 设置散点图的全局选项，包括标题
        scatter.set_global_opts(title_opts=opts.TitleOpts(title=f'{month}月天气散点图'))

        # 将设置好的散点图添加到时间轴中，并以月份作为标签
        timeline.add(scatter, f'{month}月')

    # 渲染输出文件
    timeline.render(output_file)


def main():
    weathers = []

    # 循环爬取1-12月的数据
    for month in range(1, 13):
        weather_time = f'2023{month:02d}'  # 格式化为两位数的月份，例如 '202301', '202302', ...
        url = f'https://lishi.tianqi.com/chengdu/{weather_time}.html'
        weather = get_weather(url)
        weathers.append(weather)

    write_to_csv("weather.csv", [day_data for month_data in weathers for day_data in month_data])
    insert_into_sqlite([day_data for month_data in weathers for day_data in month_data])

    # 查询并打印数据库中的数据
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weather")
    rows = cursor.fetchall()
    #for row in rows:
    #    print(row)  # 打印每一行数据
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute("SELECT weather FROM weather")  # 假设 'weather' 列包含天气描述信息
    rows = cursor.fetchall()
    weather_descriptions = " ".join([row[0] for row in rows])  # 将所有描述信息组合成一个字符串

    # 生成词云
    wordcloud = WordCloud(font_path='C:\\Windows\\Fonts\\微软雅黑\\msyh.ttc', width=800, height=400,
                          font_step=1, prefer_horizontal=0.9).generate(weather_descriptions)

    # 显示词云图像
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.show()
    conn.close()

    generate_weather_timeline_plot('weather.csv', 'weathers.html')
    generate_weather_trend_plot('weather.csv', 'weather_trend.html')
    generate_scatter_timeline('weather.csv', 'scatter_timeline.html')
    # 渲染为HTML文件


if __name__ == '__main__':
    main()
