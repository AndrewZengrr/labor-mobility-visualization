"""
社区演化链分析 - 包含重叠节点属性统计
从相似度矩阵构建演化链，并分析重叠节点的属性分布
"""
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from collections import defaultdict, Counter
import gc
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class EvolutionChainAnalyzerWithOverlapAttributes:
    """社区演化链分析器 - 包含重叠节点属性统计"""
    
    def __init__(self, similarity_file, community_results_dir, level=1, output_base_dir=None):
        """
        Parameters:
        -----------
        similarity_file : str
            相似度矩阵文件路径
        community_results_dir : str
            社区检测结果目录
        level : int
            社区层级
        output_base_dir : str
            输出基础目录（默认为相似度矩阵所在目录的evolution_chains目录）
            实际输出会在 output_base_dir/level{N}/ 下
        """
        self.similarity_file = Path(similarity_file)
        self.community_results_dir = Path(community_results_dir)
        self.level = level
        self.level_column = f'community_level{level}'
        
        # 设置输出目录：统一的evolution_chains文件夹，每层一个子文件夹
        if output_base_dir:
            base_dir = Path(output_base_dir)
        else:
            base_dir = self.similarity_file.parent / "evolution_chains"
        
        self.output_dir = base_dir / f"level{level}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存：年份DataFrame（避免重复加载文件）
        self.yearly_dataframes = {}
        
        # 缓存：年份-社区ID -> 节点集合和属性
        self.community_nodes_cache = {}
        self.community_attributes_cache = {}
        
        logging.info(f"Initialized Evolution Chain Analyzer")
        logging.info(f"  Level: {level}")
        logging.info(f"  Similarity file: {self.similarity_file}")
        logging.info(f"  Community results dir: {self.community_results_dir}")
        logging.info(f"  Output directory: {self.output_dir} (level{level} subdirectory)")
    
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
        加载指定年份的社区检测结果（使用缓存）
        
        支持嵌套和扁平两种目录结构
        """
        # 先检查缓存
        if year in self.yearly_dataframes:
            return self.yearly_dataframes[year]
        
        # 尝试嵌套目录结构
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
                # 查找parquet或csv文件
                result_files = list(year_folder.glob("*results.parquet")) + \
                              list(year_folder.glob("*results.csv"))
                
                if result_files:
                    result_file = result_files[0]
                    logging.info(f"Loading data for year {year} from {result_file}")
                    
                    if result_file.suffix == '.parquet':
                        df = pd.read_parquet(result_file)
                    else:
                        df = pd.read_csv(result_file)
                    
                    logging.info(f"  Loaded {len(df):,} records")
                    # 缓存结果
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
                
                logging.info(f"  Loaded {len(df):,} records")
                # 缓存结果
                self.yearly_dataframes[year] = df
                return df
        
        logging.warning(f"No data file found for year {year}")
        return None
    
    def get_community_nodes_and_attributes(self, year, community_id):
        """
        获取指定社区的节点集合和属性数据
        
        Returns:
        --------
        tuple: (nodes_set, attributes_df)
            - nodes_set: 节点geo_rcid的集合
            - attributes_df: 包含节点属性的DataFrame
        """
        cache_key = (year, community_id)
        
        if cache_key in self.community_nodes_cache:
            return self.community_nodes_cache[cache_key], self.community_attributes_cache[cache_key]
        
        # 加载年份数据
        df = self.load_community_data_for_year(year)
        
        if df is None:
            return set(), pd.DataFrame()
        
        # 检查层级列
        if self.level_column not in df.columns:
            logging.warning(f"Column {self.level_column} not found in year {year} data")
            return set(), pd.DataFrame()
        
        # 筛选社区
        community_df = df[df[self.level_column].astype(str) == str(community_id)].copy()
        
        if len(community_df) == 0:
            logging.warning(f"No records found for community {community_id} in year {year}")
            return set(), pd.DataFrame()
        
        # 提取节点集合
        nodes_set = set(community_df['geo_rcid'].values)
        
        # 选择需要的属性列
        attribute_columns = ['geo_rcid', 'naics_code', 'real_state', 'real_metro_area']
        available_columns = [col for col in attribute_columns if col in community_df.columns]
        
        attributes_df = community_df[available_columns].copy()
        
        # 缓存结果
        self.community_nodes_cache[cache_key] = nodes_set
        self.community_attributes_cache[cache_key] = attributes_df
        
        return nodes_set, attributes_df
    
    def analyze_overlap_attributes(self, overlap_nodes, year1, comm1, year2, comm2):
        """
        分析重叠节点的属性分布
        
        Parameters:
        -----------
        overlap_nodes : set
            重叠节点的geo_rcid集合
        year1, comm1, year2, comm2 : 社区标识
        
        Returns:
        --------
        dict: 包含各维度属性分布的字典
        """
        if not overlap_nodes:
            return self._get_empty_overlap_stats()
        
        # 获取两个社区的属性数据
        _, attrs1 = self.get_community_nodes_and_attributes(year1, comm1)
        _, attrs2 = self.get_community_nodes_and_attributes(year2, comm2)
        
        if attrs1.empty or attrs2.empty:
            return self._get_empty_overlap_stats()
        
        # 筛选重叠节点的属性
        overlap_attrs1 = attrs1[attrs1['geo_rcid'].isin(overlap_nodes)]
        overlap_attrs2 = attrs2[attrs2['geo_rcid'].isin(overlap_nodes)]
        
        # 合并两个时期的属性（优先使用year2的数据）
        overlap_attrs = overlap_attrs2.copy()
        missing_in_year2 = overlap_nodes - set(overlap_attrs2['geo_rcid'])
        if missing_in_year2:
            overlap_attrs = pd.concat([
                overlap_attrs,
                overlap_attrs1[overlap_attrs1['geo_rcid'].isin(missing_in_year2)]
            ], ignore_index=True)
        
        # 统计各维度分布
        stats = {
            'overlap_size': len(overlap_nodes),
            'naics_2digit': self._get_empty_distribution(),
            'naics_4digit': self._get_empty_distribution(),
            'state': self._get_empty_distribution(),
            'metro_area': self._get_empty_distribution()
        }
        
        # NAICS 2位码
        if 'naics_code' in overlap_attrs.columns:
            naics_2d = overlap_attrs['naics_code'].apply(
                lambda x: str(x)[:2] if pd.notna(x) and str(x) != 'unknown' and len(str(x)) >= 2 else None
            ).dropna()
            
            if len(naics_2d) > 0:
                naics_2d_counts = naics_2d.value_counts()
                stats['naics_2digit'] = self._format_distribution(naics_2d_counts, len(overlap_nodes))
        
        # NAICS 4位码
        if 'naics_code' in overlap_attrs.columns:
            naics_4d = overlap_attrs['naics_code'].apply(
                lambda x: str(x)[:4] if pd.notna(x) and str(x) != 'unknown' and len(str(x)) >= 4 else None
            ).dropna()
            
            if len(naics_4d) > 0:
                naics_4d_counts = naics_4d.value_counts()
                stats['naics_4digit'] = self._format_distribution(naics_4d_counts, len(overlap_nodes))
        
        # State
        if 'real_state' in overlap_attrs.columns:
            states = overlap_attrs['real_state'].replace('unknown', None).dropna()
            
            if len(states) > 0:
                state_counts = states.value_counts()
                stats['state'] = self._format_distribution(state_counts, len(overlap_nodes))
        
        # Metro Area
        if 'real_metro_area' in overlap_attrs.columns:
            metros = overlap_attrs['real_metro_area'].replace('unknown', None).dropna()
            
            if len(metros) > 0:
                metro_counts = metros.value_counts()
                stats['metro_area'] = self._format_distribution(metro_counts, len(overlap_nodes))
        
        return stats
    
    def _get_empty_distribution(self):
        """返回空的分布结构"""
        return {
            'distribution': [],
            'coverage': 0.0,
            'entropy': 0.0,
            'unique_values': 0
        }
    
    def _format_distribution(self, counts, total_nodes):
        """
        格式化分布数据
        
        Returns:
        --------
        dict: {'distribution': [...], 'coverage': float, 'entropy': float}
        """
        distribution = []
        total_count = counts.sum()
        
        for value, count in counts.items():
            if pd.notna(value) and str(value).strip():
                distribution.append({
                    'value': str(value),
                    'count': int(count),
                    'percentage': round(count / total_count * 100, 2) if total_count > 0 else 0
                })
        
        # 计算覆盖率（有效数据占重叠节点的比例）
        coverage = total_count / total_nodes if total_nodes > 0 else 0
        
        # 计算熵（多样性指标）
        entropy = 0.0
        if total_count > 0:
            probs = counts / total_count
            entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        return {
            'distribution': distribution,
            'coverage': round(coverage, 4),
            'entropy': round(entropy, 4),
            'unique_values': len(distribution)
        }
    
    def _get_empty_overlap_stats(self):
        """返回空的重叠统计"""
        return {
            'overlap_size': 0,
            'naics_2digit': self._get_empty_distribution(),
            'naics_4digit': self._get_empty_distribution(),
            'state': self._get_empty_distribution(),
            'metro_area': self._get_empty_distribution()
        }
    
    def filter_connections(self, df, min_jaccard=0.05, min_overlap=20, 
                          min_retention_either=0.05):
        """
        分层筛选连接
        
        Parameters:
        -----------
        df : pd.DataFrame
            相似度矩阵
        min_jaccard : float
            最小Jaccard相似度
        min_overlap : int
            最小重叠节点数
        min_retention_either : float
            前向或后向保留率至少一个要达到的阈值
        
        Returns:
        --------
        pd.DataFrame: 筛选后的连接
        """
        logging.info("\n" + "="*80)
        logging.info("Filtering connections with hierarchical criteria")
        logging.info("="*80)
        
        initial_count = len(df)
        
        # 只保留相邻年份
        df_adjacent = df[df['year_gap'] == 1].copy()
        logging.info(f"Step 1 - Adjacent years only: {len(df_adjacent):,} / {initial_count:,} "
                    f"({len(df_adjacent)/initial_count*100:.1f}%)")
        
        # 基本质量筛选
        df_filtered = df_adjacent[
            (df_adjacent['jaccard'] >= min_jaccard) &
            (df_adjacent['overlap_size'] >= min_overlap) &
            ((df_adjacent['retention_forward'] >= min_retention_either) | 
             (df_adjacent['retention_backward'] >= min_retention_either))
        ].copy()
        
        logging.info(f"Step 2 - Quality filter (jaccard>={min_jaccard}, overlap>={min_overlap}, "
                    f"retention_either>={min_retention_either}):")
        logging.info(f"  {len(df_filtered):,} / {len(df_adjacent):,} "
                    f"({len(df_filtered)/len(df_adjacent)*100:.1f}%)")
        
        if len(df_filtered) == 0:
            logging.warning("No connections remaining after filtering!")
            return df_filtered
        
        # 统计信息
        logging.info(f"\nFiltering summary:")
        logging.info(f"  Input pairs: {initial_count:,}")
        logging.info(f"  Adjacent year pairs: {len(df_adjacent):,}")
        logging.info(f"  Final pairs: {len(df_filtered):,}")
        logging.info(f"  Overall retention: {len(df_filtered)/initial_count*100:.1f}%")
        
        return df_filtered
    
    def build_evolution_chains_with_overlap_stats(self, df_filtered):
        """
        构建演化链并计算重叠节点属性统计
        
        Returns:
        --------
        list: 演化链列表，每条链包含重叠节点的属性分布
        """
        logging.info("\n" + "="*80)
        logging.info("Building evolution chains with overlap attribute analysis")
        logging.info("="*80)
        
        # 构建图结构
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        all_nodes = set()
        
        for _, row in df_filtered.iterrows():
            source = (int(row['year1']), str(row['community1']))
            target = (int(row['year2']), str(row['community2']))
            
            graph[source].append({
                'target': target,
                'jaccard': row['jaccard'],
                'retention_forward': row['retention_forward'],
                'retention_backward': row['retention_backward'],
                'overlap_size': row['overlap_size'],
                'size1': row['size1'],
                'size2': row['size2']
            })
            
            in_degree[target] += 1
            all_nodes.add(source)
            all_nodes.add(target)
        
        # 找起点（入度为0的节点）
        start_nodes = [node for node in all_nodes if in_degree[node] == 0]
        logging.info(f"Found {len(start_nodes)} chain starting points")
        
        # DFS构建链
        chains = []
        visited = set()
        
        def dfs(node, current_chain):
            if node in visited:
                return
            
            visited.add(node)
            current_chain.append(node)
            
            if node in graph and len(graph[node]) > 0:
                # 有后继节点
                for edge in graph[node]:
                    new_chain = current_chain.copy()
                    dfs(edge['target'], new_chain)
            else:
                # 链的终点
                if len(current_chain) >= 2:
                    chains.append(current_chain.copy())
        
        for start in start_nodes:
            dfs(start, [])
        
        logging.info(f"Built {len(chains)} initial chains")
        
        # 为每条链添加重叠节点属性统计
        chains_with_stats = []
        
        logging.info("\nAnalyzing overlap attributes for each chain...")
        for idx, chain in enumerate(chains, 1):
            if idx % 100 == 0 or idx == len(chains):
                logging.info(f"  Progress: {idx}/{len(chains)} chains processed")
            
            chain_data = {
                'chain_id': idx,
                'length': len(chain),
                'start_year': chain[0][0],
                'end_year': chain[-1][0],
                'duration': chain[-1][0] - chain[0][0] + 1,
                'communities': [
                    {'year': node[0], 'community': node[1]}
                    for node in chain
                ],
                'transitions': []
            }
            
            # 分析每个转换的重叠节点属性
            for i in range(len(chain) - 1):
                source = chain[i]
                target = chain[i + 1]
                
                # 获取节点集合
                nodes1, _ = self.get_community_nodes_and_attributes(source[0], source[1])
                nodes2, _ = self.get_community_nodes_and_attributes(target[0], target[1])
                
                overlap_nodes = nodes1 & nodes2
                
                # 分析重叠节点属性
                overlap_stats = self.analyze_overlap_attributes(
                    overlap_nodes, source[0], source[1], target[0], target[1]
                )
                
                # 找到对应的边信息
                edge_info = None
                if source in graph:
                    for edge in graph[source]:
                        if edge['target'] == target:
                            edge_info = edge
                            break
                
                transition = {
                    'from_year': source[0],
                    'from_community': source[1],
                    'to_year': target[0],
                    'to_community': target[1],
                    'jaccard': edge_info['jaccard'] if edge_info else None,
                    'retention_forward': edge_info['retention_forward'] if edge_info else None,
                    'retention_backward': edge_info['retention_backward'] if edge_info else None,
                    'overlap_size': edge_info['overlap_size'] if edge_info else len(overlap_nodes),
                    'size_from': edge_info['size1'] if edge_info else len(nodes1),
                    'size_to': edge_info['size2'] if edge_info else len(nodes2),
                    # 重叠节点属性统计
                    'overlap_attributes': overlap_stats
                }
                
                chain_data['transitions'].append(transition)
            
            chains_with_stats.append(chain_data)
        
        logging.info(f"\nCompleted overlap analysis for {len(chains_with_stats)} chains")
        
        return chains_with_stats
    
    def analyze_chain_statistics(self, chains):
        """分析演化链的统计特征"""
        if not chains:
            return {}
        
        chain_lengths = [c['length'] for c in chains]
        chain_durations = [c['duration'] for c in chains]
        
        # 收集重叠属性多样性统计
        naics_2d_diversity = []
        naics_4d_diversity = []
        state_diversity = []
        metro_diversity = []
        
        for chain in chains:
            for trans in chain['transitions']:
                overlap_attrs = trans.get('overlap_attributes', {})
                
                # 安全地获取unique_values，如果不存在则使用0
                naics_2d_diversity.append(
                    overlap_attrs.get('naics_2digit', {}).get('unique_values', 0)
                )
                naics_4d_diversity.append(
                    overlap_attrs.get('naics_4digit', {}).get('unique_values', 0)
                )
                state_diversity.append(
                    overlap_attrs.get('state', {}).get('unique_values', 0)
                )
                metro_diversity.append(
                    overlap_attrs.get('metro_area', {}).get('unique_values', 0)
                )
        
        stats = {
            'total_chains': len(chains),
            'chain_length': {
                'mean': np.mean(chain_lengths),
                'median': np.median(chain_lengths),
                'min': np.min(chain_lengths),
                'max': np.max(chain_lengths),
                'std': np.std(chain_lengths)
            },
            'chain_duration': {
                'mean': np.mean(chain_durations),
                'median': np.median(chain_durations),
                'min': np.min(chain_durations),
                'max': np.max(chain_durations),
                'std': np.std(chain_durations)
            },
            'overlap_attribute_diversity': {
                'naics_2digit': {
                    'mean': np.mean(naics_2d_diversity) if naics_2d_diversity else 0,
                    'median': np.median(naics_2d_diversity) if naics_2d_diversity else 0,
                    'max': np.max(naics_2d_diversity) if naics_2d_diversity else 0
                },
                'naics_4digit': {
                    'mean': np.mean(naics_4d_diversity) if naics_4d_diversity else 0,
                    'median': np.median(naics_4d_diversity) if naics_4d_diversity else 0,
                    'max': np.max(naics_4d_diversity) if naics_4d_diversity else 0
                },
                'state': {
                    'mean': np.mean(state_diversity) if state_diversity else 0,
                    'median': np.median(state_diversity) if state_diversity else 0,
                    'max': np.max(state_diversity) if state_diversity else 0
                },
                'metro_area': {
                    'mean': np.mean(metro_diversity) if metro_diversity else 0,
                    'median': np.median(metro_diversity) if metro_diversity else 0,
                    'max': np.max(metro_diversity) if metro_diversity else 0
                }
            }
        }
        
        return stats
    
    def save_results(self, chains, stats, filter_params):
        """保存分析结果"""
        logging.info(f"\nSaving results to {self.output_dir}")
        
        # 保存完整的演化链数据（包含重叠属性）
        chains_file = self.output_dir / "evolution_chains_with_overlap_attributes.json"
        with open(chains_file, 'w', encoding='utf-8') as f:
            json.dump(chains, f, indent=2, ensure_ascii=False, default=str)
        
        file_size_mb = chains_file.stat().st_size / (1024 * 1024)
        logging.info(f"✓ Saved chains: {chains_file}")
        logging.info(f"  File size: {file_size_mb:.2f} MB")
        
        # 保存统计摘要
        summary = {
            'level': self.level,
            'filter_parameters': filter_params,
            'statistics': stats,
            'analysis_timestamp': pd.Timestamp.now().isoformat()
        }
        
        summary_file = self.output_dir / "chain_analysis_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logging.info(f"✓ Saved summary: {summary_file}")
        
        # 生成简化版本（不含详细属性分布，便于快速浏览）
        chains_simple = []
        for chain in chains:
            chain_simple = {
                'chain_id': chain['chain_id'],
                'length': chain['length'],
                'start_year': chain['start_year'],
                'end_year': chain['end_year'],
                'duration': chain['duration'],
                'communities': chain['communities'],
                'transitions_summary': [
                    {
                        'from': f"{t['from_year']}_{t['from_community']}",
                        'to': f"{t['to_year']}_{t['to_community']}",
                        'overlap_size': t['overlap_size'],
                        'jaccard': t['jaccard'],
                        'retention_forward': t['retention_forward'],
                        # 只保留最主要的属性
                        'top_naics_2digit': t['overlap_attributes']['naics_2digit']['distribution'][:3] if t['overlap_attributes']['naics_2digit']['distribution'] else [],
                        'top_states': t['overlap_attributes']['state']['distribution'][:3] if t['overlap_attributes']['state']['distribution'] else []
                    }
                    for t in chain['transitions']
                ]
            }
            chains_simple.append(chain_simple)
        
        simple_file = self.output_dir / "evolution_chains_simple.json"
        with open(simple_file, 'w', encoding='utf-8') as f:
            json.dump(chains_simple, f, indent=2, ensure_ascii=False, default=str)
        
        logging.info(f"✓ Saved simple version: {simple_file}")
    
    def print_summary(self, chains, stats):
        """打印分析摘要"""
        print("\n" + "="*80)
        print(f"EVOLUTION CHAIN ANALYSIS SUMMARY - LEVEL {self.level}")
        print("="*80)
        print(f"Total chains: {stats['total_chains']}")
        print(f"\nChain length:")
        print(f"  Mean: {stats['chain_length']['mean']:.2f}")
        print(f"  Median: {stats['chain_length']['median']:.0f}")
        print(f"  Range: [{stats['chain_length']['min']:.0f}, {stats['chain_length']['max']:.0f}]")
        print(f"\nChain duration (years):")
        print(f"  Mean: {stats['chain_duration']['mean']:.2f}")
        print(f"  Median: {stats['chain_duration']['median']:.0f}")
        print(f"  Range: [{stats['chain_duration']['min']:.0f}, {stats['chain_duration']['max']:.0f}]")
        
        print(f"\nOverlap Attribute Diversity (unique values per transition):")
        print(f"  NAICS 2-digit: {stats['overlap_attribute_diversity']['naics_2digit']['mean']:.2f} (mean), "
              f"{stats['overlap_attribute_diversity']['naics_2digit']['max']:.0f} (max)")
        print(f"  NAICS 4-digit: {stats['overlap_attribute_diversity']['naics_4digit']['mean']:.2f} (mean), "
              f"{stats['overlap_attribute_diversity']['naics_4digit']['max']:.0f} (max)")
        print(f"  States: {stats['overlap_attribute_diversity']['state']['mean']:.2f} (mean), "
              f"{stats['overlap_attribute_diversity']['state']['max']:.0f} (max)")
        print(f"  Metro Areas: {stats['overlap_attribute_diversity']['metro_area']['mean']:.2f} (mean), "
              f"{stats['overlap_attribute_diversity']['metro_area']['max']:.0f} (max)")
        
        # 展示一个示例链
        if chains:
            sample_chain = chains[0]
            print(f"\nSample Chain (ID: {sample_chain['chain_id']}):")
            print(f"  Length: {sample_chain['length']} communities")
            print(f"  Duration: {sample_chain['start_year']}-{sample_chain['end_year']}")
            
            if sample_chain['transitions']:
                sample_trans = sample_chain['transitions'][0]
                overlap_attrs = sample_trans['overlap_attributes']
                print(f"\n  Sample Transition:")
                print(f"    From: {sample_trans['from_year']}_{sample_trans['from_community']}")
                print(f"    To: {sample_trans['to_year']}_{sample_trans['to_community']}")
                print(f"    Overlap size: {sample_trans['overlap_size']}")
                print(f"    Jaccard: {sample_trans['jaccard']:.3f}")
                
                if overlap_attrs['naics_2digit']['distribution']:
                    print(f"    Top NAICS 2-digit in overlap:")
                    for item in overlap_attrs['naics_2digit']['distribution'][:3]:
                        print(f"      {item['value']}: {item['count']} ({item['percentage']:.1f}%)")
                
                if overlap_attrs['state']['distribution']:
                    print(f"    Top States in overlap:")
                    for item in overlap_attrs['state']['distribution'][:3]:
                        print(f"      {item['value']}: {item['count']} ({item['percentage']:.1f}%)")
        
        print("="*80 + "\n")
    
    def run(self, min_jaccard=0.05, min_overlap=20, min_retention_either=0.05):
        """
        运行完整的演化链分析流程
        
        Parameters:
        -----------
        min_jaccard : float
            最小Jaccard相似度阈值
        min_overlap : int
            最小重叠节点数阈值
        min_retention_either : float
            前向或后向保留率阈值（至少一个达到）
        
        Returns:
        --------
        tuple: (chains, statistics)
        """
        start_time = time.time()
        
        logging.info("="*80)
        logging.info("EVOLUTION CHAIN ANALYSIS WITH OVERLAP ATTRIBUTES")
        logging.info("="*80)
        logging.info(f"Level: {self.level}")
        logging.info(f"Similarity file: {self.similarity_file}")
        logging.info(f"Output directory: {self.output_dir}")
        logging.info(f"Filter parameters:")
        logging.info(f"  min_jaccard: {min_jaccard}")
        logging.info(f"  min_overlap: {min_overlap}")
        logging.info(f"  min_retention_either: {min_retention_either}")
        logging.info("="*80)
        
        # 加载相似度矩阵
        df = self.load_similarity_matrix()
        
        # 筛选连接
        df_filtered = self.filter_connections(
            df, 
            min_jaccard=min_jaccard,
            min_overlap=min_overlap,
            min_retention_either=min_retention_either
        )
        
        if len(df_filtered) == 0:
            logging.error("No connections remaining after filtering!")
            return [], {}
        
        # 预加载所有需要的年份数据
        logging.info("\n" + "="*80)
        logging.info("Pre-loading all required year data...")
        logging.info("="*80)
        
        required_years = set(df_filtered['year1'].unique()) | set(df_filtered['year2'].unique())
        required_years = sorted([int(y) for y in required_years])
        
        logging.info(f"Years to load: {required_years}")
        
        for year in required_years:
            if year not in self.yearly_dataframes:
                self.load_community_data_for_year(year)
        
        logging.info(f"Pre-loaded {len(self.yearly_dataframes)} year files")
        logging.info("="*80)
        
        # 构建演化链并分析重叠属性
        chains = self.build_evolution_chains_with_overlap_stats(df_filtered)
        
        # 统计分析
        stats = self.analyze_chain_statistics(chains)
        
        # 保存结果
        filter_params = {
            'min_jaccard': min_jaccard,
            'min_overlap': min_overlap,
            'min_retention_either': min_retention_either
        }
        self.save_results(chains, stats, filter_params)
        
        # 打印摘要
        self.print_summary(chains, stats)
        
        elapsed_time = time.time() - start_time
        logging.info(f"\n✓ Analysis completed in {elapsed_time:.2f} seconds")
        logging.info(f"✓ Results saved to: {self.output_dir}\n")
        
        return chains, stats


def main():
    """主函数"""
    # 配置参数
    level = 2
    
    similarity_file = f"./similarity_matrices_complete/similarity_matrix_level{level}_complete.parquet"
    community_results_dir = "./workforce_community_results_adaptive_4d"
    output_base_dir = "./evolution_chains"  # 所有层级的演化链都保存在这个文件夹下
    
    # 筛选参数
    filter_params = {
        'min_jaccard': 0.02,          # Jaccard相似度阈值
        'min_overlap': 10,            # 最小重叠节点数
        'min_retention_either': 0.05  # 前向或后向保留率阈值
    }
    
    # 创建分析器
    analyzer = EvolutionChainAnalyzerWithOverlapAttributes(
        similarity_file=similarity_file,
        community_results_dir=community_results_dir,
        level=level,
        output_base_dir=output_base_dir
    )
    
    # 运行分析
    try:
        chains, stats = analyzer.run(**filter_params)
        
        if chains:
            print("\n" + "="*80)
            print("NEXT STEPS:")
            print("="*80)
            print(f"1. Review results in: {output_base_dir}/level{level}/")
            print(f"2. Main output files:")
            print(f"   - evolution_chains_with_overlap_attributes.json (full details)")
            print(f"   - evolution_chains_simple.json (quick overview)")
            print(f"   - chain_analysis_summary.json (statistics)")
            print(f"3. All levels are organized under: {output_base_dir}/")
            print(f"   - level1/, level2/, level3/, etc.")
            print(f"4. Use the chains to:")
            print(f"   - Identify stable labor market communities")
            print(f"   - Track industry/geographic composition changes")
            print(f"   - Analyze community transformation patterns")
            print("="*80 + "\n")
        
        return analyzer, chains, stats
    
    except Exception as e:
        logging.error(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    analyzer, chains, stats = main()
