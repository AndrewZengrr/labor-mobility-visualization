"""
生成示例社区连接数据用于测试可视化
"""
import json
import random
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SampleDataGenerator:
    """生成示例社区连接数据"""

    def __init__(self, start_year=2000, num_years=5, communities_per_year=10, connection_prob=0.3):
        """
        Parameters:
        -----------
        start_year : int
            起始年份
        num_years : int
            年份数量
        communities_per_year : int
            每年的社区数量
        connection_prob : float
            相邻年份社区之间有连接的概率
        """
        self.start_year = start_year
        self.num_years = num_years
        self.communities_per_year = communities_per_year
        self.connection_prob = connection_prob

    def generate(self):
        """生成示例数据"""
        logging.info("\n" + "="*80)
        logging.info("GENERATING SAMPLE DATA")
        logging.info("="*80)
        logging.info(f"Years: {self.start_year} - {self.start_year + self.num_years - 1}")
        logging.info(f"Communities per year: {self.communities_per_year}")
        logging.info(f"Connection probability: {self.connection_prob}")
        logging.info("="*80 + "\n")

        nodes = []
        links = []

        # 生成每年的社区节点
        for year_offset in range(self.num_years):
            year = self.start_year + year_offset

            for comm_id in range(self.communities_per_year):
                node_id = f"{year}_{comm_id}"
                nodes.append({
                    'id': node_id,
                    'year': year,
                    'community': str(comm_id),
                    'out_degree': 0,
                    'in_degree': 0,
                    'total_degree': 0,
                    'size': 10
                })

        # 生成相邻年份之间的连接
        for year_offset in range(self.num_years - 1):
            year1 = self.start_year + year_offset
            year2 = year1 + 1

            for comm1 in range(self.communities_per_year):
                # 每个社区可能连接到下一年的多个社区
                num_connections = random.randint(0, min(5, self.communities_per_year))

                if random.random() > self.connection_prob:
                    num_connections = 0

                # 选择目标社区
                possible_targets = list(range(self.communities_per_year))
                random.shuffle(possible_targets)
                targets = possible_targets[:num_connections]

                for comm2 in targets:
                    source_id = f"{year1}_{comm1}"
                    target_id = f"{year2}_{comm2}"

                    # 生成随机的相似度指标
                    jaccard = random.uniform(0.05, 0.5)
                    retention_forward = random.uniform(0.1, 0.8)
                    retention_backward = random.uniform(0.1, 0.8)

                    # 基于相似度计算合理的节点数
                    size1 = random.randint(50, 200)
                    overlap_size = int(size1 * retention_forward)
                    size2 = int(overlap_size / retention_backward) if retention_backward > 0 else size1

                    link = {
                        'source': source_id,
                        'target': target_id,
                        'jaccard': round(jaccard, 4),
                        'retention_forward': round(retention_forward, 4),
                        'retention_backward': round(retention_backward, 4),
                        'overlap_size': overlap_size,
                        'size1': size1,
                        'size2': size2,
                        'growth_rate': round((size2 - size1) / size1, 4),
                        'year_gap': 1
                    }

                    links.append(link)

        # 更新节点的度数
        node_dict = {n['id']: n for n in nodes}

        for link in links:
            if link['source'] in node_dict:
                node_dict[link['source']]['out_degree'] += 1
            if link['target'] in node_dict:
                node_dict[link['target']]['in_degree'] += 1

        for node in nodes:
            node['total_degree'] = node['out_degree'] + node['in_degree']
            node['size'] = min(max(node['total_degree'] * 2, 8), 30)

        logging.info(f"✓ Generated {len(nodes)} nodes")
        logging.info(f"✓ Generated {len(links)} links")

        return {
            'nodes': nodes,
            'links': links
        }

    def save(self, data, output_file):
        """保存数据"""
        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logging.info(f"\n✓ Data saved to: {output_path}")
        logging.info(f"  File size: {output_path.stat().st_size / 1024:.2f} KB\n")

    def print_summary(self, data):
        """打印数据摘要"""
        nodes = data['nodes']
        links = data['links']

        years = sorted(set(n['year'] for n in nodes))

        print("\n" + "="*80)
        print("DATA SUMMARY")
        print("="*80)
        print(f"Total nodes: {len(nodes)}")
        print(f"Total links: {len(links)}")
        print(f"Year range: {min(years)} - {max(years)}")

        for year in years:
            year_nodes = [n for n in nodes if n['year'] == year]
            year_links = [l for l in links if l['source'].startswith(f"{year}_")]
            print(f"  {year}: {len(year_nodes)} communities, {len(year_links)} outgoing links")

        print("="*80 + "\n")


def main():
    """主函数"""
    # 生成较小的示例数据用于测试
    generator = SampleDataGenerator(
        start_year=2000,
        num_years=5,
        communities_per_year=10,
        connection_prob=0.4
    )

    data = generator.generate()
    generator.print_summary(data)

    output_file = "./sample_community_connections.json"
    generator.save(data, output_file)

    print("="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Open: community-connection-explorer.html")
    print(f"2. Load the sample data: {output_file}")
    print("3. Click on year 2000 communities to start exploring")
    print("="*80 + "\n")

    return generator, data


if __name__ == "__main__":
    generator, data = main()
