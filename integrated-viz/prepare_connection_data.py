"""
准备社区连接可视化数据
从相似度矩阵生成可视化所需的JSON格式
"""
import pandas as pd
import json
import logging
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ConnectionDataPreparer:
    """准备社区连接可视化数据"""

    def __init__(self, similarity_file, output_file=None, jaccard_threshold=0.0):
        """
        Parameters:
        -----------
        similarity_file : str
            相似度矩阵文件路径（.parquet格式）
        output_file : str, optional
            输出JSON文件路径
        jaccard_threshold : float
            Jaccard相似度阈值，只保留大于此值的连接（默认0，即保留所有非零连接）
        """
        self.similarity_file = Path(similarity_file)
        self.jaccard_threshold = jaccard_threshold

        if output_file:
            self.output_file = Path(output_file)
        else:
            self.output_file = self.similarity_file.parent / "community_connections.json"

    def load_similarity_matrix(self):
        """加载相似度矩阵"""
        logging.info(f"Loading similarity matrix from {self.similarity_file}")

        if not self.similarity_file.exists():
            raise FileNotFoundError(f"Similarity matrix not found: {self.similarity_file}")

        df = pd.read_parquet(self.similarity_file)
        logging.info(f"Loaded {len(df):,} similarity pairs")

        return df

    def prepare_data(self, df):
        """
        准备可视化数据

        Returns:
        --------
        dict: {'nodes': [...], 'links': [...]}
        """
        logging.info("\n" + "="*80)
        logging.info("Preparing visualization data")
        logging.info("="*80)

        # 筛选相邻年份的连接
        df_adjacent = df[df['year_gap'] == 1].copy()
        logging.info(f"Adjacent year pairs: {len(df_adjacent):,}")

        # 筛选有连接的社区对（jaccard > threshold）
        df_connected = df_adjacent[df_adjacent['jaccard'] > self.jaccard_threshold].copy()
        logging.info(f"Connected pairs (jaccard > {self.jaccard_threshold}): {len(df_connected):,}")

        if len(df_connected) == 0:
            logging.warning("No connections found! Try lowering the jaccard_threshold.")
            return {'nodes': [], 'links': []}

        # 创建节点
        nodes = self._create_nodes(df_connected)
        logging.info(f"Created {len(nodes)} nodes")

        # 创建边
        links = self._create_links(df_connected)
        logging.info(f"Created {len(links)} links")

        return {
            'nodes': nodes,
            'links': links
        }

    def _create_nodes(self, df):
        """创建节点列表"""
        # 收集所有唯一的社区节点
        nodes_dict = {}

        # 从源社区收集
        for _, row in df.iterrows():
            source_id = f"{int(row['year1'])}_{row['community1']}"
            if source_id not in nodes_dict:
                nodes_dict[source_id] = {
                    'id': source_id,
                    'year': int(row['year1']),
                    'community': str(row['community1']),
                    'out_degree': 0,
                    'in_degree': 0
                }
            nodes_dict[source_id]['out_degree'] += 1

        # 从目标社区收集
        for _, row in df.iterrows():
            target_id = f"{int(row['year2'])}_{row['community2']}"
            if target_id not in nodes_dict:
                nodes_dict[target_id] = {
                    'id': target_id,
                    'year': int(row['year2']),
                    'community': str(row['community2']),
                    'out_degree': 0,
                    'in_degree': 0
                }
            nodes_dict[target_id]['in_degree'] += 1

        # 添加总度数
        for node in nodes_dict.values():
            node['total_degree'] = node['out_degree'] + node['in_degree']
            node['size'] = min(max(node['total_degree'] * 2, 8), 30)

        return list(nodes_dict.values())

    def _create_links(self, df):
        """创建边列表"""
        links = []

        for _, row in df.iterrows():
            source_id = f"{int(row['year1'])}_{row['community1']}"
            target_id = f"{int(row['year2'])}_{row['community2']}"

            link = {
                'source': source_id,
                'target': target_id,
                'jaccard': float(row['jaccard']),
                'retention_forward': float(row['retention_forward']),
                'retention_backward': float(row['retention_backward']),
                'overlap_size': int(row['overlap_size']),
                'size1': int(row['size1']),
                'size2': int(row['size2']),
                'growth_rate': float(row['growth_rate']) if pd.notna(row['growth_rate']) else None,
                'year_gap': int(row['year_gap'])
            }

            # 添加属性相似度（如果存在）
            if 'naics_cosine_similarity' in row:
                link['naics_similarity'] = float(row['naics_cosine_similarity'])
            if 'state_cosine_similarity' in row:
                link['state_similarity'] = float(row['state_cosine_similarity'])

            links.append(link)

        return links

    def save_json(self, data):
        """保存为JSON文件"""
        logging.info(f"\nSaving to {self.output_file}")

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logging.info(f"✓ Data saved successfully!")
        logging.info(f"  Nodes: {len(data['nodes'])}")
        logging.info(f"  Links: {len(data['links'])}")
        logging.info(f"  File size: {self.output_file.stat().st_size / 1024:.2f} KB")

    def print_summary(self, data):
        """打印数据摘要"""
        if len(data['nodes']) == 0:
            return

        nodes = data['nodes']
        links = data['links']

        years = sorted(set(n['year'] for n in nodes))
        year_counts = defaultdict(int)
        for n in nodes:
            year_counts[n['year']] += 1

        print("\n" + "="*80)
        print("DATA SUMMARY")
        print("="*80)
        print(f"Total nodes: {len(nodes)}")
        print(f"Total links: {len(links)}")
        print(f"Year range: {min(years)} - {max(years)}")
        print(f"\nNodes per year:")
        for year in years:
            print(f"  {year}: {year_counts[year]} communities")

        # 度数统计
        out_degrees = [n['out_degree'] for n in nodes if n['out_degree'] > 0]
        in_degrees = [n['in_degree'] for n in nodes if n['in_degree'] > 0]

        if out_degrees:
            print(f"\nOut-degree statistics:")
            print(f"  Mean: {sum(out_degrees)/len(out_degrees):.2f}")
            print(f"  Max: {max(out_degrees)}")

        if in_degrees:
            print(f"\nIn-degree statistics:")
            print(f"  Mean: {sum(in_degrees)/len(in_degrees):.2f}")
            print(f"  Max: {max(in_degrees)}")

        # Jaccard统计
        jaccards = [l['jaccard'] for l in links]
        print(f"\nJaccard similarity:")
        print(f"  Mean: {sum(jaccards)/len(jaccards):.4f}")
        print(f"  Min: {min(jaccards):.4f}")
        print(f"  Max: {max(jaccards):.4f}")

        print("="*80 + "\n")

    def run(self):
        """运行完整流程"""
        logging.info("\n" + "="*80)
        logging.info("COMMUNITY CONNECTION DATA PREPARATION")
        logging.info("="*80)
        logging.info(f"Input: {self.similarity_file}")
        logging.info(f"Output: {self.output_file}")
        logging.info(f"Jaccard threshold: {self.jaccard_threshold}")
        logging.info("="*80)

        # 加载数据
        df = self.load_similarity_matrix()

        # 准备可视化数据
        data = self.prepare_data(df)

        if len(data['nodes']) == 0:
            logging.error("No data to save!")
            return None

        # 打印摘要
        self.print_summary(data)

        # 保存
        self.save_json(data)

        logging.info("\n✓ Data preparation completed!\n")

        return data


def main():
    """主函数"""
    # 配置参数
    similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"
    output_file = "./community_connections.json"
    jaccard_threshold = 0.0  # 保留所有非零连接

    # 创建准备器
    preparer = ConnectionDataPreparer(
        similarity_file=similarity_file,
        output_file=output_file,
        jaccard_threshold=jaccard_threshold
    )

    # 运行
    try:
        data = preparer.run()

        if data:
            print("\n" + "="*80)
            print("NEXT STEPS:")
            print("="*80)
            print(f"1. Open the visualization: community-connection-explorer.html")
            print(f"2. Click 'Load Data' and select: {output_file}")
            print(f"3. Click on communities to explore connections year by year")
            print("="*80 + "\n")

        return preparer, data

    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    preparer, data = main()
