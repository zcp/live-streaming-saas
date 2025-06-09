import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import ast

# 设置中文字体和负号支持
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False


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
    def parse_ts_details(ts_str):
        try:
            return ast.literal_eval(ts_str)
        except:
            return []

    df['ts_details_parsed'] = df['ts_details'].apply(parse_ts_details)

    # 平均 TS 请求状态码和缓存命中率
    df['avg_ts_status'] = df['ts_details_parsed'].apply(
        lambda lst: pd.Series([d.get('status', 0) for d in lst]).mean() if lst else None
    )
    df['ts_cache_hit_rate'] = df['ts_details_parsed'].apply(
        lambda lst: sum(1 for d in lst if d.get('cf_cache_status') == 'HIT') / len(lst) if lst else None
    )

    # 转换时间字段
    df['start_time'] = pd.to_datetime(df['start_time'])
    return df


def plot_all_metrics(df):
    metrics = [
        ('speed', '拉流速度 (x倍速)', '速度 (倍速)'),
        ('fps', '帧率变化', 'FPS'),
        ('dropped', '丢帧数变化', '丢帧数'),
        ('first_screen_time', '首屏时间', '秒'),
        ('avg_ts_status', '平均 TS 状态码', '状态码'),
        ('ts_cache_hit_rate', 'TS 缓存命中率', '命中率'),
    ]

    fig, axes = plt.subplots(len(metrics), 1, figsize=(14, 3.5 * len(metrics)), sharex=True)

    for i, (metric, title, ylabel) in enumerate(metrics):
        ax = axes[i]
        for name, group in df.groupby('source_file'):
            ax.plot(group['start_time'], group[metric], marker='o', linestyle='-', label=name)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True)
        if i == len(metrics) - 1:
            ax.set_xlabel('测试时间')

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    fig.suptitle('CDN 拉流性能可视化指标汇总', fontsize=16)
    fig.legend(df['source_file'].unique(), title="测试文件", loc="upper center", ncol=3)

    # 可选：保存图片
    # plt.savefig("cdn_metrics_summary.png", dpi=300)

    plt.show()

def plot_all_metrics_v2(df):
    metrics = [
        ('speed', '拉流速度 (x倍速)', '速度 (倍速)'),
        ('fps', '帧率变化', 'FPS'),
        ('dropped', '丢帧数变化', '丢帧数'),
        ('first_screen_time', '首屏时间', '秒'),
        ('avg_ts_status', '平均 TS 状态码', '状态码'),
        ('ts_cache_hit_rate', 'TS 缓存命中率', '命中率'),
    ]

    fig, axes = plt.subplots(len(metrics), 1, figsize=(14, 3.5 * len(metrics)), sharex=True)

    for i, (metric, title, ylabel) in enumerate(metrics):
        ax = axes[i]
        for name, group in df.groupby('source_file'):
            # 主折线
            ax.plot(group['start_time'], group[metric], marker='o', linestyle='-', label=name)

            # 每组平均值线
            group_mean = group[metric].mean()
            ax.axhline(group_mean, linestyle='--', linewidth=1.2, label=f'{name} 平均值: {group_mean:.2f}')

        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True)

        if i == len(metrics) - 1:
            ax.set_xlabel('测试时间')

        # 避免图例重复（只保留唯一标签）
        handles, labels = ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        ax.legend(unique.values(), unique.keys(), loc='best')

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    fig.suptitle('CDN 与 R2 各指标可视化对比（含每组平均值）', fontsize=16)

    # 可选保存图
    # plt.savefig("cdn_r2_metrics_comparison.png", dpi=300)

    plt.show()


def main():
    df = load_data_from_csv()
    if df is None:
        return
    df = preprocess_data(df)
    plot_all_metrics_v2(df)


if __name__ == "__main__":
    main()
