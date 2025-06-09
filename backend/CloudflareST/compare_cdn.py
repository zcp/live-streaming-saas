import pandas as pd
import matplotlib.pyplot as plt
import sys

# Step 1: Set up Matplotlib to display Chinese characters correctly.
try:
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
except Exception as e:
    print(f"Could not set font to 'SimHei'. Please ensure you have a Chinese font installed. Error: {e}")
    print("You may need to change 'SimHei' to a font available on your system (e.g., 'Microsoft YaHei' on Windows).")

# Step 2: Define the filenames and load the data.
cdn_filename = 'result_cdn.csv'
no_cdn_filename = 'result_r2.csv'

try:
    df_cdn = pd.read_csv(cdn_filename)
    df_no_cdn = pd.read_csv(no_cdn_filename)
    print(f"Successfully loaded '{cdn_filename}' and '{no_cdn_filename}'.")
except FileNotFoundError as e:
    print(f"Error: {e}")
    print("\nPlease make sure that both CSV files are in the same directory as this Python script.")
    sys.exit()

# Step 3: Clean up column names by stripping any leading/trailing whitespace
df_cdn.columns = df_cdn.columns.str.strip()
df_no_cdn.columns = df_no_cdn.columns.str.strip()


# Step 4: Perform and print a statistical analysis.
print("="*50)
print("              数据统计分析 (Statistical Analysis)")
print("="*50)

print(f"\n--- {cdn_filename} (有 CDN 的情况) ---")
print(df_cdn[['平均延迟', '下载速度 (MB/s)']].describe())

print(f"\n--- {no_cdn_filename} (没有 CDN 的情况) ---")
print(df_no_cdn[['平均延迟', '下载速度 (MB/s)']].describe())
print("\n" + "="*50)
print("正在生成图表...")


# Step 5: Create visualizations with proper IP Address labels.
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(18, 16))
fig.suptitle('CDN开启与关闭性能对比 (IP地址)', fontsize=20, weight='bold')

# Combine IP addresses from both dataframes for the x-axis labels
all_ips = list(df_cdn['IP 地址']) + list(df_no_cdn['IP 地址'])
x_positions = range(len(all_ips))

# --- Plot 1: Download Speed Comparison ---
ax1 = axes[0]
ax1.bar(x=range(len(df_cdn)), height=df_cdn['下载速度 (MB/s)'], label='有 CDN', color='royalblue')
ax1.bar(x=range(len(df_cdn), len(all_ips)), height=df_no_cdn['下载速度 (MB/s)'], label='没有 CDN', color='sandybrown')

ax1.set_title('各 IP 下载速度对比', fontsize=16)
ax1.set_ylabel('下载速度 (MB/s)', fontsize=12)
ax1.grid(axis='y', linestyle='--', alpha=0.7)
ax1.legend()
ax1.axvspan(-0.5, len(df_cdn) - 0.5, facecolor='blue', alpha=0.05)
ax1.axvspan(len(df_cdn) - 0.5, len(all_ips) - 0.5, facecolor='orange', alpha=0.05)

# --- Plot 2: Average Latency Comparison ---
ax2 = axes[1]
ax2.bar(x=range(len(df_cdn)), height=df_cdn['平均延迟'], label='有 CDN', color='deepskyblue')
ax2.bar(x=range(len(df_cdn), len(all_ips)), height=df_no_cdn['平均延迟'], label='没有 CDN', color='lightcoral')

ax2.set_title('各 IP 平均延迟对比', fontsize=16)
ax2.set_ylabel('平均延迟 (ms)', fontsize=12)
ax2.grid(axis='y', linestyle='--', alpha=0.7)
ax2.legend()
ax2.axvspan(-0.5, len(df_cdn) - 0.5, facecolor='blue', alpha=0.05)
ax2.axvspan(len(df_cdn) - 0.5, len(all_ips) - 0.5, facecolor='orange', alpha=0.05)


# --- ！！！修改部分在这里！！！ ---
# Apply IP Address labels to both charts with a 45-degree rotation
for ax in axes:
    ax.set_xticks(x_positions)
    # 将 rotation 从 90 改为 45, 将 ha(horizontal alignment) 从 'center' 改为 'right'
    ax.set_xticklabels(all_ips, rotation=45, ha='right', fontsize=10)
    ax.set_xlabel('IP 地址', fontsize=12)

# Improve layout to prevent labels from being cut off
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()