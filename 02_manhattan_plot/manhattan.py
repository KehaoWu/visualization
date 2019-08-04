from pandas import DataFrame
from scipy.stats import uniform
from scipy.stats import randint
import numpy as np
import matplotlib.pyplot as plt

# 生成一些随机数据用来示例
# 真正使用的时候，可以生成一个DataFrame，分两列，一列是pvalue，一列是chromosome
df = DataFrame({
    'pvalue': uniform.rvs(size=10000),
    'chromosome': ['chr%i' % i for i in randint.rvs(0, 12, size=10000)]
})

# -log_10(pvalue)
df['P-Value(-log10)'] = -np.log10(df.pvalue)

# 将染色体转换为类型变量，并且设定按找1-12排序
df.chromosome = df.chromosome.astype('category')
df.chromosome = df.chromosome.cat.set_categories(
    ['chr%i' % i for i in range(12)], ordered=True)
df = df.sort_values('chromosome')

# How to plot gene vs. -log10(pvalue) and colour it by chromosome?
df['ind'] = range(len(df))
df_grouped = df.groupby(('chromosome'))

fig = plt.figure()
ax = fig.add_subplot()
colors = ['red', 'green', 'blue', 'yellow']
x_labels = []
x_labels_pos = []

for num, (name, group) in enumerate(df_grouped):
    group.plot(kind='scatter', x='ind', y='P-Value(-log10)',
               color=colors[num % len(colors)], ax=ax)
    x_labels.append(name)
    x_labels_pos.append(
        (group['ind'].iloc[-1] - (group['ind'].iloc[-1] - group['ind'].iloc[0])/2))

ax.set_xticks(x_labels_pos)
ax.set_xticklabels(x_labels)
ax.set_xlim([0, len(df)])
ax.set_ylim([0, 3.5])
ax.set_xlabel('Chromosome')
plt.show()
# 如果要保存图片可以使用下面这行代码
# plt.savefig('manhattan.png')
