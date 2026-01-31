# 改进的社区演化链构建 - 包含完整属性用于可视化
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class EnhancedEvolutionChainBuilder:
    """构建增强的社区演化链 - 包含完整属性数据"""

    def __init__(self, similarity_file, community_results_dir, output_dir=None):
        """
        Parameters:
        -----------
        similarity_file : str
            相似度矩阵文件路径
        community_results_dir : str
            社区检测结果目录
        output_dir : str, optional
            输出目录
        """
        self.similarity_file = Path(similarity_file)
        self.community_results_dir = Path(community_results_dir)
        self.df = None
        self.community_data = {}  # 存储每年的社区详细数据

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.similarity_file.parent / "evolution_chains"
        self.output_dir.mkdir(exist_ok=True)
        
    def load_similarity_matrix(self):
        """加载相似度矩阵"""
        logging.info(f"Loading similarity matrix from {self.similarity_file}")
        self.df = pd.read_parquet(self.similarity_file)
        logging.info(f"Loaded {len(self.df):,} similarity pairs")
        return self.df

    def load_community_data(self, level=1):
        """加载所有年份的社区检测结果"""
        logging.info(f"Loading community data from {self.community_results_dir}")
        community_col = f'community_level{level}'

        # 获取所有年份
        years = set(self.df['year1'].unique()) | set(self.df['year2'].unique())
        years = sorted(years)

        for year in years:
            window_start = year - 1
            window_end = year
            result_dir = self.community_results_dir / f"results_{window_start}_{window_end}"
            result_file = result_dir / f"workforce_geo_community_{window_start}_{window_end}_results.parquet"

            if not result_file.exists():
                logging.warning(f"Year {year} data not found: {result_file}")
                continue

            df = pd.read_parquet(result_file)
            df_valid = df[df[community_col] != "-1"].copy()

            # 按社区分组并提取属性
            communities = {}
            for comm_id in df_valid[community_col].unique():
                comm_data = df_valid[df_valid[community_col] == comm_id]
                communities[comm_id] = {
                    'data': comm_data,
                    'size': len(comm_data),
                    'nodes': set(comm_data['geo_rcid'].values)
                }

            self.community_data[year] = communities
            logging.info(f"Loaded year {year}: {len(communities)} communities, {len(df_valid)} nodes")

        return self.community_data
    
    def extract_community_attributes(self, year, comm_id):
        """提取社区的详细属性用于可视化"""
        if year not in self.community_data or comm_id not in self.community_data[year]:
            return {}

        comm = self.community_data[year][comm_id]
        comm_data = comm['data']

        # 提取State分布 (Top 3)
        state_counts = comm_data['real_state'].value_counts()
        total = len(comm_data)
        top3_states = [
            {
                'value': str(state),
                'count': int(count),
                'percentage': round(count / total * 100, 1)
            }
            for state, count in state_counts.head(3).items()
            if str(state) != 'unknown'
        ]

        # 提取Metro Area分布 (Top 5)
        metro_counts = comm_data['real_metro_area'].value_counts()
        top5_metros = [
            {
                'value': str(metro),
                'count': int(count),
                'percentage': round(count / total * 100, 1)
            }
            for metro, count in metro_counts.head(5).items()
            if str(metro) != 'unknown'
        ]

        # 提取NAICS 2-digit (Top 3)
        naics_2d = comm_data['naics_code'].apply(
            lambda x: str(x)[:2] if pd.notna(x) and str(x) != 'unknown' and len(str(x)) >= 2 else None
        ).dropna()
        naics_2d_counts = naics_2d.value_counts()
        top3_naics_2digit = [
            {
                'value': str(naics),
                'count': int(count),
                'percentage': round(count / len(naics_2d) * 100, 1) if len(naics_2d) > 0 else 0
            }
            for naics, count in naics_2d_counts.head(3).items()
        ]

        # 提取NAICS 4-digit (Top 5)
        naics_4d = comm_data['naics_code'].apply(
            lambda x: str(x)[:4] if pd.notna(x) and str(x) != 'unknown' and len(str(x)) >= 4 else None
        ).dropna()
        naics_4d_counts = naics_4d.value_counts()
        top5_naics_4digit = [
            {
                'value': str(naics),
                'count': int(count),
                'percentage': round(count / len(naics_4d) * 100, 1) if len(naics_4d) > 0 else 0
            }
            for naics, count in naics_4d_counts.head(5).items()
        ]

        # 提取Top 10 Roles (如果有role_k1500_vector)
        top10_roles = []
        if 'role_k1500_vector' in comm_data.columns:
            # 解析role_k1500_vector (格式: "role1:count1|role2:count2|...")
            role_counter = Counter()
            for role_vec in comm_data['role_k1500_vector'].dropna():
                if role_vec and str(role_vec) != 'unknown':
                    for item in str(role_vec).split('|'):
                        if ':' in item:
                            role, count = item.split(':', 1)
                            role_counter[role] += int(count)

            total_roles = sum(role_counter.values())
            top10_roles = [
                {
                    'role': role,
                    'count': count,
                    'percentage': round(count / total_roles * 100, 1) if total_roles > 0 else 0
                }
                for role, count in role_counter.most_common(10)
            ]

        return {
            'size': comm['size'],
            'top3_states': top3_states,
            'top5_metros': top5_metros,
            'top3_naics_2digit': top3_naics_2digit,
            'top5_naics_4digit': top5_naics_4digit,
            'top10_roles': top10_roles
        }

    def build_basic_chains(self, year_gap=1, include_zero=False):
        """
        构建基础演化链
        
        Parameters:
        -----------
        year_gap : int
            时间间隔（1=相邻年份）
        include_zero : bool
            是否包含零值连接（默认False，只保留非零）
        
        Returns:
        --------
        pd.DataFrame: 演化链数据
        """
        logging.info("\n" + "="*80)
        logging.info(f"构建基础演化链 (year_gap={year_gap})")
        logging.info("="*80)
        
        # 筛选指定时间间隔
        chains = self.df[self.df['year_gap'] == year_gap].copy()
        logging.info(f"时间间隔={year_gap}的总对数: {len(chains):,}")
        
        # 筛选非零连接
        if not include_zero:
            chains = chains[chains['jaccard'] > 0].copy()
            logging.info(f"非零连接数: {len(chains):,} ({len(chains)/len(self.df[self.df['year_gap']==year_gap])*100:.2f}%)")
        
        # 重命名列以便理解
        chains = chains.rename(columns={
            'year1': 'source_year',
            'community1': 'source_community',
            'year2': 'target_year',
            'community2': 'target_community'
        })
        
        # 创建唯一ID
        chains['edge_id'] = range(len(chains))
        chains['source_id'] = chains['source_year'].astype(str) + '_' + chains['source_community']
        chains['target_id'] = chains['target_year'].astype(str) + '_' + chains['target_community']
        
        logging.info(f"\n构建完成:")
        logging.info(f"  边数量: {len(chains):,}")
        logging.info(f"  源社区数: {chains['source_id'].nunique():,}")
        logging.info(f"  目标社区数: {chains['target_id'].nunique():,}")
        
        return chains
    
    def add_statistics(self, chains):
        """添加统计信息"""
        logging.info("\n计算统计信息...")
        
        # 计算每个社区的出度和入度
        out_degree = chains.groupby('source_id').size().to_dict()
        in_degree = chains.groupby('target_id').size().to_dict()
        
        chains['source_out_degree'] = chains['source_id'].map(out_degree)
        chains['target_in_degree'] = chains['target_id'].map(in_degree)
        
        # 计算在源社区的所有后继中的排名
        chains['rank_in_source'] = chains.groupby('source_id')['jaccard'].rank(
            method='dense', ascending=False).astype(int)
        
        # 计算在目标社区的所有前驱中的排名
        chains['rank_in_target'] = chains.groupby('target_id')['jaccard'].rank(
            method='dense', ascending=False).astype(int)
        
        # 组合得分 (可调整权重)
        chains['score'] = 0.6 * chains['jaccard'] + 0.4 * chains['retention_forward']
        
        # 标记是否是双向最优
        best_forward = chains.groupby('source_id')['jaccard'].idxmax()
        best_backward = chains.groupby('target_id')['jaccard'].idxmax()
        
        chains['is_best_forward'] = chains.index.isin(best_forward)
        chains['is_best_backward'] = chains.index.isin(best_backward)
        chains['is_mutual_best'] = chains['is_best_forward'] & chains['is_best_backward']
        
        logging.info(f"统计信息:")
        logging.info(f"  双向最优连接数: {chains['is_mutual_best'].sum():,}")
        logging.info(f"  前向最优连接数: {chains['is_best_forward'].sum():,}")
        logging.info(f"  后向最优连接数: {chains['is_best_backward'].sum():,}")
        
        return chains
    
    def export_for_visualization(self, chains, prefix='basic'):
        """导出用于可视化的数据"""
        logging.info("\n" + "="*80)
        logging.info("导出可视化数据")
        logging.info("="*80)
        
        # 1. 导出节点数据
        nodes = self._create_nodes(chains)
        nodes_file = self.output_dir / f"{prefix}_nodes.json"
        nodes.to_json(nodes_file, orient='records', indent=2)
        logging.info(f"节点数据已保存: {nodes_file} ({len(nodes):,} nodes)")
        
        # 2. 导出边数据
        edges = self._create_edges(chains)
        edges_file = self.output_dir / f"{prefix}_edges.json"
        edges.to_json(edges_file, orient='records', indent=2)
        logging.info(f"边数据已保存: {edges_file} ({len(edges):,} edges)")
        
        # 3. 导出完整数据表（用于进一步分析）
        full_file = self.output_dir / f"{prefix}_chains_full.parquet"
        chains.to_parquet(full_file, index=False)
        logging.info(f"完整数据已保存: {full_file}")
        
        # 4. 导出元数据
        metadata = self._create_metadata(chains)
        metadata_file = self.output_dir / f"{prefix}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logging.info(f"元数据已保存: {metadata_file}")
        
        # 5. 导出D3.js格式（nodes+links）
        d3_data = {
            'nodes': json.loads(nodes.to_json(orient='records')),
            'links': json.loads(edges.to_json(orient='records'))
        }
        d3_file = self.output_dir / f"{prefix}_d3_format.json"
        with open(d3_file, 'w') as f:
            json.dump(d3_data, f, indent=2)
        logging.info(f"D3.js格式已保存: {d3_file}")
        
        return {
            'nodes_file': str(nodes_file),
            'edges_file': str(edges_file),
            'full_file': str(full_file),
            'metadata_file': str(metadata_file),
            'd3_file': str(d3_file)
        }
    
    def _create_nodes(self, chains):
        """创建节点数据（包含完整属性）"""
        # 收集所有唯一节点
        source_nodes = chains[['source_id', 'source_year', 'source_community',
                               'source_out_degree']].drop_duplicates()
        source_nodes.columns = ['id', 'year', 'community', 'out_degree']
        source_nodes['in_degree'] = 0

        target_nodes = chains[['target_id', 'target_year', 'target_community',
                              'target_in_degree']].drop_duplicates()
        target_nodes.columns = ['id', 'year', 'community', 'in_degree']
        target_nodes['out_degree'] = 0

        # 合并节点
        nodes = pd.concat([source_nodes, target_nodes], ignore_index=True)
        nodes = nodes.groupby('id').agg({
            'year': 'first',
            'community': 'first',
            'out_degree': 'max',
            'in_degree': 'max'
        }).reset_index()

        # 添加节点类型
        nodes['total_degree'] = nodes['out_degree'] + nodes['in_degree']

        # 为每个节点添加详细属性
        nodes['attributes'] = nodes.apply(
            lambda row: self.extract_community_attributes(row['year'], row['community']),
            axis=1
        )

        # 节点大小（用于可视化）
        nodes['size'] = nodes.apply(
            lambda row: row['attributes'].get('size', 0) if isinstance(row['attributes'], dict) else 0,
            axis=1
        )

        return nodes
    
    def _create_edges(self, chains):
        """创建边数据"""
        edges = chains[[
            'edge_id', 'source_id', 'target_id',
            'jaccard', 'retention_forward', 'retention_backward',
            'overlap_size', 'size1', 'size2', 'growth_rate',
            'source_out_degree', 'target_in_degree',
            'rank_in_source', 'rank_in_target',
            'score', 'is_best_forward', 'is_best_backward', 'is_mutual_best'
        ]].copy()
        
        # 添加边类型
        def classify_edge(row):
            if row['is_mutual_best']:
                return 'mutual_best'
            elif row['is_best_forward']:
                return 'best_forward'
            elif row['is_best_backward']:
                return 'best_backward'
            elif row['rank_in_source'] <= 3:
                return 'top3_forward'
            else:
                return 'other'
        
        edges['edge_type'] = edges.apply(classify_edge, axis=1)
        
        # 边宽度（用于可视化，基于Jaccard）
        edges['width'] = edges['jaccard'].apply(lambda x: min(max(x * 1000, 0.5), 10))
        
        return edges
    
    def _create_metadata(self, chains):
        """创建元数据"""
        metadata = {
            'total_edges': len(chains),
            'total_nodes': chains['source_id'].nunique() + chains['target_id'].nunique(),
            'year_range': [int(chains['source_year'].min()), int(chains['target_year'].max())],
            'years_covered': sorted([int(y) for y in chains['source_year'].unique()]),
            'statistics': {
                'jaccard': {
                    'mean': float(chains['jaccard'].mean()),
                    'median': float(chains['jaccard'].median()),
                    'min': float(chains['jaccard'].min()),
                    'max': float(chains['jaccard'].max())
                },
                'retention_forward': {
                    'mean': float(chains['retention_forward'].mean()),
                    'median': float(chains['retention_forward'].median())
                },
                'retention_backward': {
                    'mean': float(chains['retention_backward'].mean()),
                    'median': float(chains['retention_backward'].median())
                },
                'degree_distribution': {
                    'out_degree': {
                        'mean': float(chains.groupby('source_id').size().mean()),
                        'max': int(chains.groupby('source_id').size().max())
                    },
                    'in_degree': {
                        'mean': float(chains.groupby('target_id').size().mean()),
                        'max': int(chains.groupby('target_id').size().max())
                    }
                }
            },
            'edge_types': {
                'mutual_best': int(chains['is_mutual_best'].sum()),
                'best_forward': int(chains['is_best_forward'].sum()),
                'best_backward': int(chains['is_best_backward'].sum())
            }
        }
        return metadata
    
    def build_evolution_chains_with_attributes(self, chains):
        """
        构建包含完整属性的演化链数据
        输出格式符合前端可视化需求
        """
        logging.info("Building evolution chains with detailed attributes...")

        # 基于最优匹配构建演化链路径
        # 使用双向最优或前向最优来连接社区
        evolution_chains = []

        # 获取所有年份
        all_years = sorted(set(chains['source_year']) | set(chains['target_year']))

        # 为每个起始社区构建演化链
        start_communities = chains[chains['source_year'] == all_years[0]]

        for _, start_comm in start_communities.iterrows():
            chain = self._trace_evolution_chain(chains, start_comm, all_years)
            if chain:
                evolution_chains.append(chain)

        logging.info(f"Built {len(evolution_chains)} evolution chains")
        return evolution_chains

    def _trace_evolution_chain(self, chains, start_comm, all_years):
        """追踪单个社区的演化链"""
        chain_communities = []
        current_year = start_comm['source_year']
        current_comm_id = start_comm['source_community']

        # 添加起始社区
        chain_communities.append({
            'year': int(current_year),
            'community_id': str(current_comm_id),
            'attributes': self.extract_community_attributes(current_year, current_comm_id),
            'node_composition': self._calculate_node_composition(current_year, current_comm_id, None)
        })

        # 追踪后续年份
        for next_year in all_years[1:]:
            # 查找最佳匹配
            candidates = chains[
                (chains['source_year'] == current_year) &
                (chains['source_community'] == current_comm_id) &
                (chains['target_year'] == next_year)
            ]

            if candidates.empty:
                break

            # 选择Jaccard最高的匹配
            best_match = candidates.loc[candidates['jaccard'].idxmax()]
            next_comm_id = best_match['target_community']

            # 添加到链中
            chain_communities.append({
                'year': int(next_year),
                'community_id': str(next_comm_id),
                'attributes': self.extract_community_attributes(next_year, next_comm_id),
                'node_composition': self._calculate_node_composition(
                    next_year, next_comm_id,
                    self.community_data[current_year][current_comm_id]['nodes'] if current_year in self.community_data and current_comm_id in self.community_data[current_year] else None
                )
            })

            current_year = next_year
            current_comm_id = next_comm_id

        # 只返回长度>1的链
        if len(chain_communities) > 1:
            return {
                'stable_id': f"S{start_comm['source_year']}_{start_comm['source_community']}",
                'length': len(chain_communities),
                'score': self._calculate_chain_score(chain_communities),
                'communities': chain_communities
            }
        return None

    def _calculate_node_composition(self, year, comm_id, prev_nodes):
        """计算节点组成（核心节点vs新节点）"""
        if year not in self.community_data or comm_id not in self.community_data[year]:
            return {'type': 'normal'}

        current_nodes = self.community_data[year][comm_id]['nodes']

        if prev_nodes is None or len(prev_nodes) == 0:
            return {
                'type': 'new_born',
                'core_node_ratio': 0.0,
                'new_node_ratio': 1.0,
                'avg_node_weight': 1.0,
                'core_nodes': 0,
                'new_nodes': len(current_nodes)
            }

        core_nodes = current_nodes & prev_nodes
        new_nodes = current_nodes - prev_nodes

        core_ratio = len(core_nodes) / len(current_nodes) if len(current_nodes) > 0 else 0
        new_ratio = len(new_nodes) / len(current_nodes) if len(current_nodes) > 0 else 0

        # 确定类型
        if core_ratio >= 0.7:
            comm_type = 'established'
        elif core_ratio >= 0.3:
            comm_type = 'transitional'
        else:
            comm_type = 'new_born'

        return {
            'type': comm_type,
            'core_node_ratio': round(core_ratio, 3),
            'new_node_ratio': round(new_ratio, 3),
            'avg_node_weight': round(core_ratio, 3),
            'core_nodes': len(core_nodes),
            'new_nodes': len(new_nodes)
        }

    def _calculate_chain_score(self, communities):
        """计算演化链的整体得分"""
        # 简单的得分：基于链长度和社区大小
        if not communities:
            return 0.0

        avg_size = np.mean([c['attributes'].get('size', 0) for c in communities])
        length = len(communities)

        # 归一化得分 (0-1)
        score = min(1.0, (length / 25.0) * 0.6 + (avg_size / 500.0) * 0.4)
        return round(score, 4)

    def run(self, year_gap=1, level=1):
        """运行完整流程"""
        logging.info("\n" + "="*80)
        logging.info("增强演化链构建（包含完整属性）")
        logging.info("="*80)

        # 加载数据
        self.load_similarity_matrix()

        # 加载社区数据
        self.load_community_data(level=level)

        # 构建演化链
        chains = self.build_basic_chains(year_gap=year_gap, include_zero=False)

        # 添加统计信息
        chains = self.add_statistics(chains)

        # 导出基础可视化数据
        files = self.export_for_visualization(chains, prefix=f'basic_gap{year_gap}')

        # 构建包含完整属性的演化链
        evolution_chains = self.build_evolution_chains_with_attributes(chains)

        # 导出演化链详细数据
        chains_file = self.output_dir / f'weighted_chain_details_level{level}.json'
        with open(chains_file, 'w') as f:
            json.dump(evolution_chains, f, indent=2)
        logging.info(f"Saved evolution chains with attributes: {chains_file}")
        files['chains_detail_file'] = str(chains_file)

        logging.info("\n" + "="*80)
        logging.info("增强演化链构建完成！")
        logging.info("="*80)

        return chains, files, evolution_chains


def main():
    """主函数"""
    # 输入文件
    similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"

    # 社区检测结果目录
    community_results_dir = "./workforce_community_results_adaptive_4d"

    # 输出目录
    output_dir = "./evolution_chains_enhanced"

    # 创建构建器
    builder = EnhancedEvolutionChainBuilder(
        similarity_file,
        community_results_dir,
        output_dir
    )

    # 运行（只处理相邻年份，level 1社区）
    chains, files, evolution_chains = builder.run(year_gap=1, level=1)

    # 打印摘要
    print("\n" + "="*80)
    print("输出文件:")
    print("="*80)
    for key, filepath in files.items():
        print(f"  {key:20s}: {filepath}")
    print("="*80)
    print(f"\n构建了 {len(evolution_chains)} 条演化链")
    print(f"链长度分布:")
    lengths = [c['length'] for c in evolution_chains]
    print(f"  最短: {min(lengths) if lengths else 0}")
    print(f"  最长: {max(lengths) if lengths else 0}")
    print(f"  平均: {np.mean(lengths) if lengths else 0:.1f}")
    print("="*80)

    return builder, chains, files, evolution_chains


if __name__ == "__main__":
    builder, chains, files, evolution_chains = main()