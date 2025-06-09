import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import ast

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei'] #设置为 Windows 常用中文字体 “SimHei”，避免中文乱码。

matplotlib.rcParams['axes.unicode_minus'] = False #用来正常显示负号。

def load_data_from_csv(pattern="*_round*_*.csv"):
    files = glob.glob(pattern)
    if not files:
        print("找不到符合模式的CSV文件")
        return None
    dfs = []
    for file in files:
        df = pd.read_csv(file)
        df['source_file'] = file
        dfs.append(df)
    data = pd.concat(dfs, ignore_index=True)
    return data

def preprocess_data(df):
    # 解析 ts_details 字符串成 list
    def parse_ts_details(ts_str):
        try:
            return ast.literal_eval(ts_str)
        except:
            return []

    df['ts_details_parsed'] = df['ts_details'].apply(parse_ts_details)

    # 计算平均 TS 请求状态码和缓存命中率
    df['avg_ts_status'] = df['ts_details_parsed'].apply(
        lambda lst: pd.Series([d['status'] for d in lst]).mean() if lst else None
    )
    df['ts_cache_hit_rate'] = df['ts_details_parsed'].apply(
        lambda lst: sum(1 for d in lst if d.get('cf_cache_status') == 'HIT') / len(lst) if lst else None
    )

    # 解析 cf_cache_status 字段（整体行级）
    # 这里为每条记录的 cf_cache_status 统计
    #df['cf_cache_status'] = df['cf_cache_status'].astype(str)

    # 解析 cf_ray 字段（统计不同请求数）
    #df['cf_ray'] = df['cf_ray'].astype(str)

    # 把 start_time 转成 datetime 类型
    df['start_time'] = pd.to_datetime(df['start_time'])

    return df

def plot_metric_over_time(df, metric, title, ylabel, groupby='source_file'):
    plt.figure(figsize=(12,6))
    for name, group in df.groupby(groupby):
        plt.plot(group['start_time'], group[metric], marker='o', linestyle='-', label=name)
    plt.title(title)
    plt.xlabel('测试时间')
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_cache_status_distribution(df):
    plt.figure(figsize=(10,6))
    sns.countplot(data=df, x='cf_cache_status', hue='source_file')
    plt.title('cf-cache-status 分布统计')
    plt.xlabel('cf-cache-status 状态')
    plt.ylabel('数量')
    plt.legend(title='测试文件')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_unique_cf_ray_counts(df):
    counts = df.groupby('source_file')['cf_ray'].nunique()
    plt.figure(figsize=(8,5))
    counts.plot(kind='bar')
    plt.title('每个测试文件的唯一 cf-ray 请求数')
    plt.xlabel('测试文件')
    plt.ylabel('唯一 cf-ray 数量')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()

def main():
    df = load_data_from_csv()
    if df is None:
        return
    df = preprocess_data(df)

    # 画速度变化图
    plot_metric_over_time(df, 'speed', '拉流速度变化 (x倍速)', '速度 (倍速)')

    # 画 FPS 变化图
    plot_metric_over_time(df, 'fps', '帧率变化', 'FPS')

    # 画丢帧数变化图
    plot_metric_over_time(df, 'dropped', '丢帧数变化', '丢帧数')

    # 画平均 TS 状态码（越接近200越好）
    plot_metric_over_time(df, 'avg_ts_status', '平均 TS 状态码', '状态码')

    # 画缓存命中率
    plot_metric_over_time(df, 'ts_cache_hit_rate', 'TS 缓存命中率', '命中率')

    # 画 cf-cache-status 分布
    #plot_cache_status_distribution(df)

    # 画每个文件唯一 cf-ray 请求数
    #plot_unique_cf_ray_counts(df)

if __name__ == "__main__":
    main()
