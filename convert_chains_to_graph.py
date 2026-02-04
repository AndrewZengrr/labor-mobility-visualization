"""
将演化链数据转换为图可视化格式
Converts evolution chain data to graph visualization format
"""
import json
import logging
from pathlib import Path
from collections import defaultdict
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ChainToGraphConverter:
    """将演化链数据转换为图可视化格式"""

    def __init__(self, chains_file, community_results_dir, level=1):
        """
        Parameters:
        -----------
        chains_file : str
            演化链JSON文件路径
        community_results_dir : str
            社区检测结果目录（用于提取社区属性）
        level : int
            社区层级
        """
        self.chains_file = Path(chains_file)
        self.community_results_dir = Path(community_results_dir)
        self.level = level
        self.level_column = f'community_level{level}'

        # 缓存
        self.yearly_dataframes = {}
        self.community_attributes_cache = {}

        logging.info(f"Initialized Chain to Graph Converter")
        logging.info(f"  Chains file: {self.chains_file}")
        logging.info(f"  Community results dir: {self.community_results_dir}")
        logging.info(f"  Level: {level}")

    def load_chains(self):
        """加载演化链数据"""
        logging.info(f"Loading evolution chains from {self.chains_file}")

        if not self.chains_file.exists():
            raise FileNotFoundError(f"Chains file not found: {self.chains_file}")

        with open(self.chains_file, 'r', encoding='utf-8') as f:
            chains = json.load(f)

        logging.info(f"Loaded {len(chains)} evolution chains")
        return chains

    def load_community_data_for_year(self, year):
        """加载指定年份的社区检测结果"""
        if year in self.yearly_dataframes:
            return self.yearly_dataframes[year]

        # 尝试多种文件路径模式
        year_folder_patterns = [
            f"results_{year}_{year+1}",
            f"results_{year-1}_{year}",
            f"results_{year}",
            f"{year}_{year+1}",
            f"{year}"
        ]

        for folder_pattern in year_folder_patterns:
            year_folder = self.community_results_dir / folder_pattern
            if year_folder.exists() and year_folder.is_dir():
                result_files = list(year_folder.glob("*results.parquet")) + \
                              list(year_folder.glob("*results.csv"))

                if result_files:
                    result_file = result_files[0]
                    logging.info(f"Loading data for year {year} from {result_file}")

                    if result_file.suffix == '.parquet':
                        df = pd.read_parquet(result_file)
                    else:
                        df = pd.read_csv(result_file)

                    self.yearly_dataframes[year] = df
                    return df

        # 尝试扁平目录结构
        file_patterns = [
            f"workforce_geo_community_{year}_results.parquet",
            f"workforce_geo_community_{year}_results.csv",
            f"community_{year}_results.parquet",
            f"community_{year}_results.csv"
        ]

        for pattern in file_patterns:
            file_path = self.community_results_dir / pattern
            if file_path.exists():
                logging.info(f"Loading data for year {year} from {file_path}")

                if file_path.suffix == '.parquet':
                    df = pd.read_parquet(file_path)
                else:
                    df = pd.read_csv(file_path)

                self.yearly_dataframes[year] = df
                return df

        logging.warning(f"No data file found for year {year}")
        return None

    def get_community_attributes(self, year, community_id):
        """
        获取社区的聚合属性

        Returns:
        --------
        dict: 社区属性（total_workforce, top3_states, top5_metros等）
        """
        cache_key = (year, community_id)

        if cache_key in self.community_attributes_cache:
            return self.community_attributes_cache[cache_key]

        df = self.load_community_data_for_year(year)

        if df is None or self.level_column not in df.columns:
            return self._get_empty_attributes()

        # 筛选社区数据
        community_df = df[df[self.level_column].astype(str) == str(community_id)].copy()

        if len(community_df) == 0:
            return self._get_empty_attributes()

        # 计算聚合属性
        attributes = {
            'total_workforce': len(community_df),
            'top3_states': self._get_top_n(community_df, 'real_state', 3),
            'top5_metros': self._get_top_n(community_df, 'real_metro_area', 5),
            'top3_naics_2digit': self._get_top_n_naics(community_df, 'naics_code', 2, 3),
            'top3_naics_4digit': self._get_top_n_naics(community_df, 'naics_code', 4, 3),
            'avg_wage': float(community_df['wage'].mean()) if 'wage' in community_df.columns else None,
            'total_companies': community_df['rcid'].nunique() if 'rcid' in community_df.columns else None
        }

        self.community_attributes_cache[cache_key] = attributes
        return attributes

    def _get_empty_attributes(self):
        """返回空的属性结构"""
        return {
            'total_workforce': 0,
            'top3_states': [],
            'top5_metros': [],
            'top3_naics_2digit': [],
            'top3_naics_4digit': [],
            'avg_wage': None,
            'total_companies': None
        }

    def _get_top_n(self, df, column, n):
        """获取指定列的Top N值及其计数"""
        if column not in df.columns:
            return []

        counts = df[column].replace('unknown', None).dropna().value_counts()

        result = []
        for value, count in counts.head(n).items():
            result.append({
                'value': str(value),
                'count': int(count),
                'percentage': round(count / len(df) * 100, 2)
            })

        return result

    def _get_top_n_naics(self, df, column, digits, n):
        """获取NAICS码的Top N（截取指定位数）"""
        if column not in df.columns:
            return []

        naics_codes = df[column].apply(
            lambda x: str(x)[:digits] if pd.notna(x) and str(x) != 'unknown' and len(str(x)) >= digits else None
        ).dropna()

        counts = naics_codes.value_counts()

        result = []
        for value, count in counts.head(n).items():
            result.append({
                'value': str(value),
                'count': int(count),
                'percentage': round(count / len(df) * 100, 2)
            })

        return result

    def convert_to_graph(self, chains):
        """
        将演化链转换为图可视化格式

        Returns:
        --------
        dict: {'nodes': [...], 'links': [...]}
        """
        logging.info("\nConverting evolution chains to graph format...")

        # 存储所有节点和边
        nodes_dict = {}  # key: "year_community", value: node object
        links_list = []

        # 遍历所有演化链
        for chain in chains:
            # 添加节点
            for comm in chain['communities']:
                year = comm['year']
                community = str(comm['community'])
                node_id = f"{year}_{community}"

                if node_id not in nodes_dict:
                    # 获取社区属性
                    attributes = self.get_community_attributes(year, community)

                    nodes_dict[node_id] = {
                        'id': node_id,
                        'year': year,
                        'community': community,
                        'attributes': attributes
                    }

            # 添加边
            for trans in chain['transitions']:
                source_id = f"{trans['from_year']}_{trans['from_community']}"
                target_id = f"{trans['to_year']}_{trans['to_community']}"

                link = {
                    'source': source_id,
                    'target': target_id,
                    'jaccard': trans.get('jaccard'),
                    'retention_forward': trans.get('retention_forward'),
                    'retention_backward': trans.get('retention_backward'),
                    'overlap_size': trans.get('overlap_size', 0),
                    'overlap_attributes': trans.get('overlap_attributes', {})
                }

                links_list.append(link)

        # 转换为列表
        nodes_list = list(nodes_dict.values())

        logging.info(f"Converted to {len(nodes_list)} nodes and {len(links_list)} links")

        return {
            'nodes': nodes_list,
            'links': links_list
        }

    def save_graph(self, graph_data, output_file):
        """保存图数据"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logging.info(f"✓ Saved graph data: {output_path}")
        logging.info(f"  File size: {file_size_mb:.2f} MB")
        logging.info(f"  Nodes: {len(graph_data['nodes'])}")
        logging.info(f"  Links: {len(graph_data['links'])}")

    def convert(self, output_file):
        """
        执行完整的转换流程

        Parameters:
        -----------
        output_file : str
            输出文件路径

        Returns:
        --------
        dict: 图数据 {'nodes': [...], 'links': [...]}
        """
        # 加载演化链
        chains = self.load_chains()

        if not chains:
            logging.warning("No chains to convert")
            return {'nodes': [], 'links': []}

        # 预加载所有需要的年份数据
        required_years = set()
        for chain in chains:
            for comm in chain['communities']:
                required_years.add(comm['year'])

        required_years = sorted(required_years)
        logging.info(f"Pre-loading {len(required_years)} years: {required_years}")

        for year in required_years:
            self.load_community_data_for_year(year)

        # 转换为图格式
        graph_data = self.convert_to_graph(chains)

        # 保存结果
        self.save_graph(graph_data, output_file)

        return graph_data


def main():
    """主函数 - 转换所有层级的数据"""

    # 基础配置
    evolution_chains_base = Path("./evolution_chains")
    community_results_dir = Path("./workforce_community_results_adaptive_4d")
    output_base_dir = Path("./graph_data")

    # 处理每个层级
    levels_to_process = [1, 2, 3]

    for level in levels_to_process:
        print(f"\n{'='*80}")
        print(f"Processing Level {level}")
        print(f"{'='*80}")

        # 输入文件
        chains_file = evolution_chains_base / f"level{level}" / "evolution_chains_with_overlap_attributes.json"

        if not chains_file.exists():
            logging.warning(f"Chains file not found for level {level}: {chains_file}")
            logging.warning(f"Skipping level {level}")
            continue

        # 输出文件
        output_file = output_base_dir / f"level{level}" / "community_connections_with_attributes.json"

        try:
            # 创建转换器
            converter = ChainToGraphConverter(
                chains_file=chains_file,
                community_results_dir=community_results_dir,
                level=level
            )

            # 执行转换
            graph_data = converter.convert(output_file)

            print(f"\n✓ Successfully converted Level {level}")
            print(f"  Output: {output_file}")
            print(f"  Nodes: {len(graph_data['nodes'])}")
            print(f"  Links: {len(graph_data['links'])}")

        except Exception as e:
            logging.error(f"Error processing level {level}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'='*80}")
    print("Conversion Complete")
    print(f"{'='*80}")
    print(f"Graph data saved to: {output_base_dir}/")
    print(f"Files ready for visualization:")
    for level in levels_to_process:
        output_file = output_base_dir / f"level{level}" / "community_connections_with_attributes.json"
        if output_file.exists():
            print(f"  - level{level}/community_connections_with_attributes.json")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
