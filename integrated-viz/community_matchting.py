# 基础社区演化链构建 - 保存所有非零连接用于可视化
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class BasicEvolutionChainBuilder:
    """构建基础社区演化链 - 保存所有非零连接"""
    
    def __init__(self, similarity_file, output_dir=None):
        """
        Parameters:
        -----------
        similarity_file : str
            相似度矩阵文件路径
        output_dir : str, optional
            输出目录
        """
        self.similarity_file = Path(similarity_file)
        self.df = None
        
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
        """创建节点数据"""
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
        
        # 节点大小（用于可视化）
        nodes['size'] = nodes['total_degree'].apply(lambda x: min(max(x, 5), 50))
        
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
    
    def run(self, year_gap=1):
        """运行完整流程"""
        logging.info("\n" + "="*80)
        logging.info("基础演化链构建")
        logging.info("="*80)
        
        # 加载数据
        self.load_similarity_matrix()
        
        # 构建演化链
        chains = self.build_basic_chains(year_gap=year_gap, include_zero=False)
        
        # 添加统计信息
        chains = self.add_statistics(chains)
        
        # 导出可视化数据
        files = self.export_for_visualization(chains, prefix=f'basic_gap{year_gap}')
        
        logging.info("\n" + "="*80)
        logging.info("演化链构建完成！")
        logging.info("="*80)
        
        return chains, files


def main():
    """主函数"""
    # 输入文件
    similarity_file = "./similarity_matrices_complete/similarity_matrix_level1_complete.parquet"
    
    # 输出目录
    output_dir = "./evolution_chains_basic"
    
    # 创建构建器
    builder = BasicEvolutionChainBuilder(similarity_file, output_dir)
    
    # 运行（只处理相邻年份）
    chains, files = builder.run(year_gap=1)
    
    # 打印摘要
    print("\n" + "="*80)
    print("输出文件:")
    print("="*80)
    for key, filepath in files.items():
        print(f"  {key:20s}: {filepath}")
    print("="*80)
    
    return builder, chains, files


if __name__ == "__main__":
    builder, chains, files = main()