import matplotlib.pyplot as plt
import numpy as np

# 1. 粘贴你抓取到的数据 (周日开始)
data = [
    [13, 6, 3, 2, 5, 10, 15, 20, 24, 27, 28, 29, 31, 34, 39, 43, 46, 47, 46, 40, 36, 30, 26, 22], # Sunday
    [15, 9, 5, 5, 10, 20, 36, 53, 62, 65, 70, 72, 73, 72, 77, 85, 88, 80, 64, 50, 39, 33, 28, 25], # Monday
    [17, 8, 4, 5, 10, 21, 36, 54, 67, 75, 78, 81, 84, 83, 88, 92, 98, 90, 71, 54, 42, 36, 32, 28], # Tuesday
    [17, 9, 5, 7, 12, 24, 39, 56, 67, 74, 79, 79, 80, 79, 85, 92, 99, 90, 72, 54, 43, 37, 35, 29], # Wednesday
    [17, 10, 6, 8, 13, 24, 38, 56, 68, 75, 78, 80, 80, 79, 83, 92, 100, 93, 73, 55, 43, 39, 34, 29], # Thursday
    [23, 12, 6, 7, 13, 23, 35, 49, 62, 70, 79, 82, 83, 82, 88, 96, 97, 90, 72, 56, 48, 44, 42, 38], # Friday
    [21, 11, 5, 4, 5, 9, 15, 20, 26, 31, 36, 40, 43, 47, 52, 57, 57, 54, 49, 45, 41, 42, 39, 34]  # Saturday
]

# 2. 星期标签 (周日开始)
days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

# 3. 定义我们要绘制的小时序列 (4 AM to 3 AM next day)
#    - 实际小时值: [4, 5, 6, ..., 23, 0, 1, 2, 3]
#    - 绘图位置:   [0, 1, 2, ..., 19, 20, 21, 22, 23] (共24个位置)
plot_positions = np.arange(24) # 24 bars to plot
plot_hour_sequence = list(range(4, 24)) + list(range(0, 4)) # The actual hours these bars represent

# 生成对应的小时标签 (4a, 5a, ... 11p, 12a, 1a, 2a, 3a)
hour_labels = [f'{h % 12 if h % 12 != 0 else 12}{"a" if h < 12 else "p"}' for h in plot_hour_sequence]

# 创建稀疏标签 (4a, 6a, 9a, 12p, 3p, 6p, 9p, 12a, 3a)
# 找到这些小时在 plot_positions (0-23) 中的索引
sparse_hours_to_label = [4, 6, 9, 12, 15, 18, 21, 0, 3] # Actual hours we want labels for
sparse_plot_indices = [plot_hour_sequence.index(h) for h in sparse_hours_to_label]
sparse_labels_display = {idx: hour_labels[idx] for idx in sparse_plot_indices}
final_sparse_labels = [sparse_labels_display.get(i, '') for i in plot_positions] # Get label if plot index matches, else empty string


# 4. 创建图表
fig, axes = plt.subplots(nrows=7, ncols=1, figsize=(10, 12), sharex=True, sharey=True)
plt.ylim(0, 105)

# 5. 循环绘制每一天的图 (4 AM to 3 AM next day)
for i, ax in enumerate(axes):
    # --- 数据准备：合并当天 4AM-11PM 和第二天 12AM-3AM ---
    current_day_data = data[i][4:] # Data from 4 AM to 11 PM of current day
    next_day_index = (i + 1) % 7 # Handle wrap around from Saturday to Sunday
    next_day_early_data = data[next_day_index][:4] # Data from 12 AM to 3 AM of next day
    plot_data = current_day_data + next_day_early_data # Combine to get 24 data points
    # --- 数据准备完毕 ---

    # 绘制柱状图
    ax.bar(plot_positions, plot_data, color='teal', width=0.8)

    # 设置标题
    ax.set_title(days[i])

    # 设置 Y 轴
    ax.yaxis.grid(True, linestyle='--', linewidth=0.5, color='gray')
    ax.set_yticks(np.arange(0, 101, 25))

    # 设置 X 轴
    ax.set_xticks(plot_positions) # Ticks at every bar position
    if i == len(axes) - 1:
        ax.set_xticklabels(final_sparse_labels, rotation=0, ha='center') # Show sparse labels only on the last plot
        ax.tick_params(axis='x', which='major', length=6) # Show major tick lines

        # --- 可选：只在有标签的位置显示刻度线下方的小标记 ---
        ticks = ax.xaxis.get_major_ticks()
        for idx in range(len(ticks)):
             if idx not in sparse_plot_indices:
                  ticks[idx].tick1line.set_markersize(0) # Hide upper tick part
                  ticks[idx].tick2line.set_markersize(0) # Hide lower tick part
        # --- 可选结束 ---

        ax.tick_params(axis='x', which='minor', length=0) # Hide minor ticks
    else:
        ax.set_xticklabels([''] * 24) # Hide labels on other plots
        ax.tick_params(axis='x', length=0) # Hide tick lines on other plots

    # 移除边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

# 调整布局
plt.tight_layout(h_pad=2.0)

# 添加整体 Y 轴标签
fig.text(0.01, 0.5, 'Relative Popularity (%)', ha='center', va='center', rotation='vertical')

# 6. 保存图表
output_filename = "popular_times_charts_4am_start.png"
plt.savefig(output_filename)
print(f"✅ 图表已保存到: {output_filename}")

# 7. (可选) 显示图表
# plt.show()