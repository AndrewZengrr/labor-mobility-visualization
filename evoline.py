"""
准备社区连接可视化数据 - 包含详细属性版本（支持多层级）
从相似度矩阵生成可视化所需的JSON格式，并从社区检测结果中提取详细属性
"""
import pandas as pd
import json
import logging
from pathlib import Path
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ConnectionDataPreparerWithAttributes:
    """准备社区连接可视化数据 - 包含详细社区属性（支持多层级）"""

    def __init__(self, similarity_file, community_data_dir, level=1, output_file=None):
        """
        Parameters:
        -----------
        similarity_file : str
            相似度矩阵文件路径（.parquet格式）
        community_data_dir : str
            社区检测结果CSV文件所在目录
            预期文件命名格式: workforce_geo_community_YYYY_results.csv
        level : int
            社区层级 (1, 2, 3, ...)
        output_file : str, optional
            输出JSON文件路径
        """
        self.similarity_file = Path(similarity_file)
        self.community_data_dir = Path(community_data_dir)
        self.level = level
        self.level_column = f'community_level{level}'

        if output_file:
            self.output_file = Path(output_file)
        else:
            # 根据层级自动生成输出文件名
            self.output_file = self.similarity_file.parent / f"community_connections_level{level}_with_attributes.json"

        # 过滤阈值
        self.min_overlap_size = 20
        self.min_retention_forward = 0.03
        self.min_retention_backward = 0.03
        self.min_jaccard = 0.01

        # 社区属性缓存
        self.community_attributes = {}  # {(year, community_id): attributes_dict}

    def load_similarity_matrix(self):
        """加载相似度矩阵"""
        logging.info(f"Loading similarity matrix from {self.similarity_file}")

        if not self.similarity_file.exists():
            raise FileNotFoundError(f"Similarity matrix not found: {self.similarity_file}")

        df = pd.read_parquet(self.similarity_file)
        logging.info(f"Loaded {len(df):,} similarity pairs")

        return df

    def load_community_data_for_year(self, year):
        """
        加载指定年份的社区检测结果

        支持两种目录结构：
        1. 扁平结构：community_data_dir/workforce_geo_community_YYYY_results.csv
        2. 嵌套结构：community_data_dir/results_YYYY_YYYY/*.csv

        Parameters:
        -----------
        year : int
            年份

        Returns:
        --------
        pd.DataFrame or None
        """
        # 方法1：尝试嵌套目录结构（优先）
        # 格式：./workforce_community_results_adaptive_4d/results_2023_2024/xxx.csv
        year_folder_patterns = [
            f"results_{year}_{year+1}",  # results_2023_2024
            f"results_{year-1}_{year}",  # results_2022_2023（如果数据年度是跨年的）
            f"results_{year}",           # results_2023
            f"{year}_{year+1}",          # 2023_2024
            f"{year}"                    # 2023
        ]

        for folder_pattern in year_folder_patterns:
            year_folder = self.community_data_dir / folder_pattern
            if year_folder.exists() and year_folder.is_dir():
                # 在年份文件夹中查找CSV文件
                csv_files = list(year_folder.glob("*.csv"))
                if csv_files:
                    # 优先选择包含关键词的文件
                    priority_keywords = ['result']
                    for csv_file in csv_files:
                        if any(kw in csv_file.name.lower() for kw in priority_keywords):
                            logging.info(f"Loading community data for year {year} from {csv_file}")
                            df = pd.read_csv(csv_file)
                            logging.info(f"  Loaded {len(df):,} records from {csv_file.name}")
                            return df

                    # 如果没有找到包含关键词的，使用第一个CSV文件
                    csv_file = csv_files[0]
                    logging.info(f"Loading community data for year {year} from {csv_file}")
                    df = pd.read_csv(csv_file)
                    logging.info(f"  Loaded {len(df):,} records from {csv_file.name}")
                    return df

        # 方法2：尝试扁平目录结构（向后兼容）
        file_patterns = [
            f"workforce_geo_community_{year}_results.csv",
            f"community_{year}_results.csv",
            f"community_detection_{year}.csv",
            f"{year}_community_results.csv",
            f"results_{year}.csv"
        ]

        for pattern in file_patterns:
            file_path = self.community_data_dir / pattern
            if file_path.exists():
                logging.info(f"Loading community data for year {year} from {file_path}")
                df = pd.read_csv(file_path)
                logging.info(f"  Loaded {len(df):,} records")
                return df

        logging.warning(f"No community data file found for year {year}")
        logging.warning(f"  Searched in: {self.community_data_dir}")
        logging.warning(f"  Year folder patterns: {year_folder_patterns}")
        logging.warning(f"  File patterns: {file_patterns}")
        return None

    def extract_community_attributes(self, df, community_id):
        """
        从社区检测结果中提取指定社区的属性（使用当前层级）

        Parameters:
        -----------
        df : pd.DataFrame
            社区检测结果数据
        community_id : str
            社区ID

        Returns:
        --------
        dict: 包含社区详细属性的字典
        """
        if self.level_column not in df.columns:
            logging.warning(f"Column {self.level_column} not found in dataframe")
            return self._get_empty_attributes()

        # 筛选属于该社区的所有记录
        community_df = df[df[self.level_column].astype(str) == str(community_id)]

        if len(community_df) == 0:
            logging.warning(f"No records found for community {community_id} at level {self.level}")
            return self._get_empty_attributes()

        # 计算各种属性分布
        attributes = {
            'size': len(community_df),
            'total_workforce': 0,
            'states': {},
            'metros': {},
            'naics_2digit': {},
            'naics_4digit': {},
            'rics_k50': {},
            'rics_k200': {},
            'rics_k400': {},
            'top_companies': {}
        }

        # 州分布
        if 'real_state' in community_df.columns:
            state_counts = community_df['real_state'].value_counts()
            attributes['states'] = self._format_distribution(state_counts)

        # 都市区分布
        if 'real_metro_area' in community_df.columns:
            metro_counts = community_df['real_metro_area'].value_counts()
            attributes['metros'] = self._format_distribution(metro_counts)

        # NAICS产业分布
        if 'naics_code' in community_df.columns:
            # 2位NAICS代码
            naics_2digit = community_df['naics_code'].astype(str).str[:2]
            naics_2digit_counts = naics_2digit.value_counts()
            attributes['naics_2digit'] = self._format_distribution(naics_2digit_counts)

            # 4位NAICS代码
            naics_4digit = community_df['naics_code'].astype(str).str[:4]
            naics_4digit_counts = naics_4digit.value_counts()
            attributes['naics_4digit'] = self._format_distribution(naics_4digit_counts)

        # RICS分类
        for rics_col in ['rics_k50', 'rics_k200', 'rics_k400']:
            if rics_col in community_df.columns:
                rics_counts = community_df[rics_col].value_counts()
                attributes[rics_col] = self._format_distribution(rics_counts)

        # 公司分布
        if 'company_name' in community_df.columns:
            company_counts = community_df['company_name'].value_counts()
            attributes['top_companies'] = self._format_distribution(company_counts, top_n=10)

        # 劳动力总数
        if 'workforce_total_people' in community_df.columns:
            attributes['total_workforce'] = int(community_df['workforce_total_people'].sum())

        return attributes

    def _format_distribution(self, counts, top_n=None):
        """
        将计数转换为标准分布格式

        Parameters:
        -----------
        counts : pd.Series
            计数数据
        top_n : int, optional
            只保留前N个

        Returns:
        --------
        list: [{'value': name, 'count': count, 'percentage': pct}, ...]
        """
        if top_n:
            counts = counts.head(top_n)

        total = counts.sum()
        distribution = []

        for value, count in counts.items():
            if pd.notna(value) and str(value).strip():
                distribution.append({
                    'value': str(value),
                    'count': int(count),
                    'percentage': round(count / total * 100, 2) if total > 0 else 0
                })

        return distribution

    def _get_empty_attributes(self):
        """返回空属性字典"""
        return {
            'size': 0,
            'total_workforce': 0,
            'states': [],
            'metros': [],
            'naics_2digit': [],
            'naics_4digit': [],
            'rics_k50': [],
            'rics_k200': [],
            'rics_k400': [],
            'top_companies': []
        }

    def load_all_community_attributes(self, years):
        """
        预加载所有需要的年份的社区属性（使用当前层级）

        Parameters:
        -----------
        years : set
            需要加载的年份集合
        """
        logging.info("\n" + "="*80)
        logging.info(f"Loading community attributes for all years (Level {self.level})")
        logging.info("="*80)

        for year in sorted(years):
            df = self.load_community_data_for_year(year)

            if df is None:
                continue

            # 检查当前层级列是否存在
            if self.level_column not in df.columns:
                logging.warning(f"Column {self.level_column} not found in {year} data")
                logging.warning(f"Available columns: {[col for col in df.columns if col.startswith('community_')]}")
                continue

            # 获取该年份所有社区ID（排除"-1"）
            community_ids = df[self.level_column].unique()
            community_ids = [cid for cid in community_ids if str(cid) != "-1"]

            logging.info(f"Processing {len(community_ids)} communities for year {year} at level {self.level}")

            # 为每个社区提取属性
            for comm_id in community_ids:
                key = (int(year), str(comm_id))
                attributes = self.extract_community_attributes(df, comm_id)
                self.community_attributes[key] = attributes

        logging.info(f"\nTotal communities loaded: {len(self.community_attributes):,}")
        logging.info("="*80)

    def filter_noise(self, df):
        """剔除明显噪音"""
        logging.info("\n" + "="*80)
        logging.info("Filtering obvious noise")
        logging.info("="*80)

        initial_count = len(df)

        noise_mask = (
            (df['overlap_size'] < self.min_overlap_size) &
            (df['retention_forward'] < self.min_retention_forward) &
            (df['retention_backward'] < self.min_retention_backward) &
            (df['jaccard'] < self.min_jaccard)
        )

        df_filtered = df[~noise_mask].copy()
        removed_count = initial_count - len(df_filtered)

        logging.info(f"Removed: {removed_count:,} ({removed_count/initial_count*100:.2f}%)")
        logging.info(f"Retained: {len(df_filtered):,} ({len(df_filtered)/initial_count*100:.2f}%)")

        return df_filtered

    def prepare_data(self, df):
        """
        准备可视化数据（包含详细属性）

        Returns:
        --------
        dict: {'nodes': [...], 'links': [...], 'stats': {...}}
        """
        logging.info("\n" + "="*80)
        logging.info(f"Preparing visualization data with attributes (Level {self.level})")
        logging.info("="*80)

        # 只保留相邻年份的连接
        df_adjacent = df[df['year_gap'] == 1].copy()
        logging.info(f"Adjacent year pairs: {len(df_adjacent):,}")

        # 剔除明显噪音
        df_filtered = self.filter_noise(df_adjacent)

        if len(df_filtered) == 0:
            logging.warning("No connections remaining after filtering!")
            return {'nodes': [], 'links': [], 'stats': {}}

        # 获取所有涉及的年份
        years = set(df_filtered['year1'].unique()) | set(df_filtered['year2'].unique())
        years = {int(y) for y in years}

        # 预加载所有社区属性
        self.load_all_community_attributes(years)

        # 创建节点（包含属性）
        nodes = self._create_nodes_with_attributes(df_filtered)
        logging.info(f"Created {len(nodes)} nodes with attributes")

        # 创建边
        links = self._create_links(df_filtered)
        logging.info(f"Created {len(links)} links")

        # 统计信息
        stats = self._compute_stats(df_filtered, nodes, links)

        return {
            'nodes': nodes,
            'links': links,
            'stats': stats
        }

    def _create_nodes_with_attributes(self, df):
        """创建包含详细属性的节点列表"""
        nodes_dict = {}

        # 从源社区收集
        for _, row in df.iterrows():
            source_id = f"{int(row['year1'])}_{row['community1']}"
            if source_id not in nodes_dict:
                year = int(row['year1'])
                comm_id = str(row['community1'])

                # 获取社区属性
                key = (year, comm_id)
                attributes = self.community_attributes.get(key, self._get_empty_attributes())

                nodes_dict[source_id] = {
                    'id': source_id,
                    'year': year,
                    'community': comm_id,
                    'level': self.level,
                    'size': int(row['size1']),
                    'out_degree': 0,
                    'in_degree': 0,
                    # 详细属性
                    'attributes': {
                        'total_workforce': attributes['total_workforce'],
                        'top3_states': attributes['states'][:3],
                        'top5_metros': attributes['metros'][:5],
                        'top3_naics_2digit': attributes['naics_2digit'][:3],
                        'top5_naics_4digit': attributes['naics_4digit'][:5],
                        'top3_rics_k50': attributes['rics_k50'][:3],
                        'top3_rics_k200': attributes['rics_k200'][:3],
                        'top10_companies': attributes['top_companies'][:10]
                    }
                }
            nodes_dict[source_id]['out_degree'] += 1

        # 从目标社区收集
        for _, row in df.iterrows():
            target_id = f"{int(row['year2'])}_{row['community2']}"
            if target_id not in nodes_dict:
                year = int(row['year2'])
                comm_id = str(row['community2'])

                # 获取社区属性
                key = (year, comm_id)
                attributes = self.community_attributes.get(key, self._get_empty_attributes())

                nodes_dict[target_id] = {
                    'id': target_id,
                    'year': year,
                    'community': comm_id,
                    'level': self.level,
                    'size': int(row['size2']),
                    'out_degree': 0,
                    'in_degree': 0,
                    # 详细属性
                    'attributes': {
                        'total_workforce': attributes['total_workforce'],
                        'top3_states': attributes['states'][:3],
                        'top5_metros': attributes['metros'][:5],
                        'top3_naics_2digit': attributes['naics_2digit'][:3],
                        'top5_naics_4digit': attributes['naics_4digit'][:5],
                        'top3_rics_k50': attributes['rics_k50'][:3],
                        'top3_rics_k200': attributes['rics_k200'][:3],
                        'top10_companies': attributes['top_companies'][:10]
                    }
                }
            nodes_dict[target_id]['in_degree'] += 1

        # 添加总度数
        for node in nodes_dict.values():
            node['total_degree'] = node['out_degree'] + node['in_degree']

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
                # 核心指标
                'jaccard': float(row['jaccard']),
                'retention_forward': float(row['retention_forward']),
                'retention_backward': float(row['retention_backward']),
                'overlap_size': int(row['overlap_size']),
                'union_size': int(row['union_size']),
                'size1': int(row['size1']),
                'size2': int(row['size2']),
                'growth_rate': float(row['growth_rate']) if pd.notna(row['growth_rate']) else None,
                'year_gap': int(row['year_gap']),
                # 属性相似度
                'naics_cosine_similarity': float(row['naics_cosine_similarity']) if pd.notna(row.get('naics_cosine_similarity')) else None,
                'naics_overlap_index': float(row['naics_overlap_index']) if pd.notna(row.get('naics_overlap_index')) else None,
                'state_cosine_similarity': float(row['state_cosine_similarity']) if pd.notna(row.get('state_cosine_similarity')) else None,
                'state_overlap_index': float(row['state_overlap_index']) if pd.notna(row.get('state_overlap_index')) else None,
                'metro_cosine_similarity': float(row['metro_cosine_similarity']) if pd.notna(row.get('metro_cosine_similarity')) else None,
                'metro_overlap_index': float(row['metro_overlap_index']) if pd.notna(row.get('metro_overlap_index')) else None
            }

            links.append(link)

        return links

    def _compute_stats(self, df, nodes, links):
        """计算统计信息"""
        stats = {
            'level': self.level,
            'total_nodes': len(nodes),
            'total_links': len(links),
            'year_range': {
                'min': int(df['year1'].min()),
                'max': int(df['year2'].max())
            },
            'jaccard_distribution': {
                'mean': float(df['jaccard'].mean()),
                'median': float(df['jaccard'].median()),
                'std': float(df['jaccard'].std()),
                'min': float(df['jaccard'].min()),
                'max': float(df['jaccard'].max()),
                'q25': float(df['jaccard'].quantile(0.25)),
                'q75': float(df['jaccard'].quantile(0.75))
            },
            'overlap_size_distribution': {
                'mean': float(df['overlap_size'].mean()),
                'median': float(df['overlap_size'].median()),
                'min': int(df['overlap_size'].min()),
                'max': int(df['overlap_size'].max())
            },
            'degree_distribution': {
                'out_degree_mean': sum(n['out_degree'] for n in nodes) / len(nodes),
                'in_degree_mean': sum(n['in_degree'] for n in nodes) / len(nodes),
                'max_out_degree': max(n['out_degree'] for n in nodes),
                'max_in_degree': max(n['in_degree'] for n in nodes)
            },
            'attributes_loaded': len(self.community_attributes)
        }

        return stats

    def save_json(self, data):
        """保存为JSON文件"""
        logging.info(f"\nSaving to {self.output_file}")

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        file_size_kb = self.output_file.stat().st_size / 1024

        logging.info(f"✓ Data saved successfully!")
        logging.info(f"  Level: {self.level}")
        logging.info(f"  Nodes: {len(data['nodes']):,}")
        logging.info(f"  Links: {len(data['links']):,}")
        logging.info(f"  Attributes: {data['stats']['attributes_loaded']:,} communities")
        logging.info(f"  File size: {file_size_kb:.2f} KB")

    def print_summary(self, data):
        """打印数据摘要"""
        if len(data['nodes']) == 0:
            return

        nodes = data['nodes']
        links = data['links']
        stats = data['stats']

        print("\n" + "="*80)
        print(f"DATA SUMMARY - LEVEL {self.level} WITH DETAILED ATTRIBUTES")
        print("="*80)
        print(f"Total nodes: {len(nodes):,}")
        print(f"Total links: {len(links):,}")
        print(f"Communities with attributes: {stats['attributes_loaded']:,}")

        # 示例：显示第一个节点的属性
        if len(nodes) > 0:
            sample_node = nodes[0]
            print(f"\nSample node attributes ({sample_node['id']}):")
            attrs = sample_node['attributes']
            print(f"  Workforce: {attrs['total_workforce']:,}")
            print(f"  Top states: {len(attrs['top3_states'])} loaded")
            print(f"  Top metros: {len(attrs['top5_metros'])} loaded")
            print(f"  Top NAICS (2-digit): {len(attrs['top3_naics_2digit'])} loaded")
            print(f"  Top NAICS (4-digit): {len(attrs['top5_naics_4digit'])} loaded")

        print("="*80 + "\n")

    def run(self):
        """运行完整流程"""
        logging.info("\n" + "="*80)
        logging.info(f"COMMUNITY CONNECTION DATA PREPARATION - LEVEL {self.level} WITH ATTRIBUTES")
        logging.info("="*80)
        logging.info(f"Similarity matrix: {self.similarity_file}")
        logging.info(f"Community data dir: {self.community_data_dir}")
        logging.info(f"Community level: {self.level}")
        logging.info(f"Output file: {self.output_file}")
        logging.info("="*80)

        # 加载数据
        df = self.load_similarity_matrix()

        # 准备可视化数据（包含属性）
        data = self.prepare_data(df)

        if len(data['nodes']) == 0:
            logging.error("No data to save!")
            return None

        # 打印摘要
        self.print_summary(data)

        # 保存
        self.save_json(data)

        logging.info(f"\n✓ Data preparation with attributes for Level {self.level} completed!\n")

        return data


def main():
    """主函数 - 支持多层级"""
    # 配置参数
    level = 2  # ← 修改这里选择不同层级 (1, 2, 3, ...)
    
    similarity_file = f"./similarity_matrices_complete/similarity_matrix_level{level}_complete.parquet"
    community_data_dir = "./workforce_community_results_adaptive_4d"
    output_file = f"./community_connections_level{level}_with_attributes.json"

    # 创建准备器
    preparer = ConnectionDataPreparerWithAttributes(
        similarity_file=similarity_file,
        community_data_dir=community_data_dir,
        level=level,
        output_file=output_file
    )

    # 运行
    try:
        data = preparer.run()

        if data:
            print("\n" + "="*80)
            print("NEXT STEPS:")
            print("="*80)
            print(f"1. Open: community-connection-explorer.html")
            print(f"2. Load: {output_file}")
            print(f"3. Explore Level {level} communities with detailed attributes:")
            print(f"   - Geographic distribution (states, metros)")
            print(f"   - Industry distribution (NAICS codes)")
            print(f"   - Company composition")
            print(f"   - Workforce statistics")
            print("="*80 + "\n")

        return preparer, data

    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    preparer, data = main()