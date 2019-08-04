import os
import json
import begin
import requests
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import PictorialBar
from pyecharts.charts import Line
from pyecharts.charts import Bar
import configparser
import folium
from folium import plugins


DATA_SOURCE = 'http://www.changsha.gov.cn/xxgk/szfgbmxxgkml/szfgzbmxxgkml/szfcxjsw/'


def load_config():

    cf = configparser.ConfigParser()
    cf_path = os.path.join('..', 'config.ini')
    cf.read(cf_path)
    return cf


def load_data():
    # 读取数据
    dfs = []
    path = os.path.join('..', 'data', 'changsha_zhufangyushou')
    for filename in os.listdir(path):
        filename = os.path.join(path, filename)

        # 跳过第一行和第二行
        df = pd.read_excel(filename, skiprows=[0, 1])
        dfs.append(df)

    # 将各个文件合并起来
    df_combined = pd.concat(dfs)

    # 删除其中合计行
    df_combined = df_combined[df_combined['序号'] != '合计']

    config = load_config()

    lats, lngs = [], []

    for address in df_combined['坐落地点']:
        lat, lng = query_location(address, '房地产', '长沙', config.get('basic', 'baidu_ak'))
        lats.append(lat)
        lngs.append(lng)

    df_combined['lat'] = lats
    df_combined['lng'] = lngs

    return df_combined


def query_location(address, tag, city, ak, count=0):
    if '号' in address:
        address = address[:address.index('号')+1]

    pathname = os.path.join('.cache', 'location')
    if not os.path.exists(pathname):
        os.makedirs(pathname)
    filename = os.path.join(pathname, '{}_{}_{}.json'.format(address, tag, city))
    if os.path.exists(filename):
        location = json.load(open(filename, 'r'))
        return location

    url = 'http://api.map.baidu.com/place/v2/search?query={address}&tag={tag}&region={city}&output=json&ak={ak}'
    req = requests.get(url.format(
        address=address,
        tag=tag,
        city=city,
        ak=ak
    ))
    location = [None, None]
    if req.status_code == 200:
        ret = json.loads(req.text)
        if ret.get('results'):
            location = ret['results'][0]['location']
            location = [
                location['lat'],
                location['lng']
            ]

    # if location == [None, None]:
    #     if '路' in address and count == 0:
    #         address = address[:address.index('路')+1]
    #         location = query_location(address, tag, city, ak, count=1)
    #     if '区' in address and count == 1:
    #         address = address[:address.index('区')+1]
    #         location = query_location(address, tag, city, ak, count=2)
    json.dump(location, open(filename, 'w'), ensure_ascii=False, indent=2)
    return location


@begin.subcommand
def stat_floors_distribution():
    df = load_data()
    summary = df.groupby('层数').count()
    min_date = min(df['发证日期'])
    max_date = max(df['发证日期'])
    chart = (
        PictorialBar()
        .add_xaxis(summary.index.tolist())
        .add_yaxis(
            "层数", 
            summary['序号'].tolist(),
            symbol_repeat="fixed",
            symbol_offset=[0, -5],
            is_symbol_clip=True,
        )
        .reversal_axis()
        .set_global_opts(
            title_opts=opts.TitleOpts(title="长沙预售房屋层数分布", subtitle="统计日期:{}至{}，数据来源：{}".format(
                min_date, max_date, DATA_SOURCE)),
            legend_opts=opts.LegendOpts(is_show=False),
            toolbox_opts=opts.ToolboxOpts(is_show=True),
            yaxis_opts=opts.AxisOpts(
                name="层数",
                is_show=True,
                name_location='center',
                name_gap=30
            )
        )
        .set_series_opts(
            label_opts=opts.LabelOpts(is_show=False)
        )
    )
    filename = os.path.join(
        '..', 'assets', '01_changsha_zhufangyushou_层数分布.html')
    chart.render(filename)


@begin.subcommand
def stat_area_trend():
    df = load_data()
    df['发证月份'] = [i[:7] for i in df['发证日期']]
    summary = df.groupby('发证月份').sum()
    columns_area = ['预售建筑面积', '总建筑面积', '住宅面积', '办公面积', '其他面积', '车库面积']
    columns_other = ['层数', '住宅套数']
    chart = Line()
    chart.add_xaxis(summary.index.tolist())
    for column in columns_area:
        chart.add_yaxis(
            column,
            summary[column].tolist(),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.1),
            is_smooth=True
        )

    chart.set_series_opts(
        label_opts=opts.LabelOpts(is_show=False),
    ).extend_axis(
        yaxis=opts.AxisOpts(
            axislabel_opts=opts.LabelOpts(is_show=False),
            is_show=False
        )
    )

    bar = Bar()
    bar.add_xaxis(summary.index.tolist())
    for column in columns_other:
        bar.add_yaxis(
            column,
            summary[column].tolist(),
            yaxis_index=1
        )

    chart.overlap(bar)
    min_date = min(df['发证日期'])
    max_date = max(df['发证日期'])
    chart.set_global_opts(
            title_opts=opts.TitleOpts(title="长沙预售房屋面积变化趋势", subtitle="统计日期:{}至{}，数据来源：{}".format(
                min_date, max_date, DATA_SOURCE)),
            legend_opts=opts.LegendOpts(is_show=True),
            toolbox_opts=opts.ToolboxOpts(is_show=True)
        )

    filename = os.path.join(
        '..', 'assets', '01_changsha_zhufangyushou_面积趋势.html')
    chart.render(filename)


@begin.subcommand
def stat_other():
    df = load_data()
    df['住宅面积/层'] = df['住宅面积'] / df['层数']
    df['住宅面积/套'] = df['住宅面积'] / df['住宅套数']
    print("查看底层建筑分布情况")
    df_low = df[df['层数']<=4]
    summary_low = df_low[['住宅面积', '住宅面积/层']].describe()
    print(df_low['住宅套数'].sum())
    print(summary_low)
    summary = df[['住宅面积', '住宅面积/层']].describe()
    print(summary)
    df_high = df[df['层数'] <= 34]
    df_high = df_high[df_high['层数'] >= 34]
    print(df_high[['住宅面积', '住宅面积/层', '住宅面积/套']].describe())

    print(df[df['项目名称'] == '军民融合科技城']['住宅面积'])

    print(df[df['lat'] == 28.35704]['住宅面积'])


@begin.subcommand
def stat_geo():

    df = load_data()
    buildings = df[['lat', 'lng', '住宅面积']].dropna().values

    heatmap = plugins.HeatMap(buildings)

    m = folium.Map([28, 113])

    m.add_child(heatmap)
    filename = os.path.join(
        '..', 'assets', '01_changsha_zhufangyushou_位置分布按建筑面积.html')
    m.render()
    m.save(outfile=filename)

    


@begin.start
def run():
    pass
