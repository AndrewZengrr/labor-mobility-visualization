# 简化的社区相似度矩阵构建器 - 优化版
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from collections import defaultdict
import pickle
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OptimizedSimilarityMatrixBuilder:
    """构建社区相似度矩阵 - 优化版"""
    
    def __init__(self, results_dir, level=1, output_dir=None, n_workers=None):
        self.results_dir = Path(results_dir)
        self.level = level
        self.community_col = f'community_level{level}'
        
        # 输出目录
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(results_dir).parent / "similarity_matrices"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 并行处理
        self.n_workers = n_workers or max(1, mp.cpu_count() - 1)
        
        self.yearly_data = {}
        self.yearly_communities = {}
        
        # 【优化1】预计算并缓存属性分布
        self.attribute_distributions = {}
        
    def load_year_data(self, year):
        """加载指定年份的社区检测结果"""
        window_start = year - 1
        window_end = year
        
        result_dir = self.results_dir / f"results_{window_start}_{window_end}"
        result_file = result_dir / f"workforce_geo_community_{window_start}_{window_end}_results.parquet"
        
        if not result_file.exists():
            logging.warning(f"Year {year} data not found: {result_file}")
            return None
        
        df = pd.read_parquet(result_file)
        df_valid = df[df[self.community_col] != "-1"].copy()
        
        logging.info(f"Loaded year {year}: {len(df_valid)} nodes in {df_valid[self.community_col].nunique()} communities")
        
        return df_valid
    
    def load_all_years(self, year_range):
        """加载所有年份的数据"""
        logging.info(f"Loading data for years {year_range[0]}-{year_range[1]}...")
        
        available_years = []
        for year in range(year_range[0], year_range[1] + 1):
            data = self.load_year_data(year)
            if data is not None:
                self.yearly_data[year] = data
                available_years.append(year)
                
                # 构建社区字典：存储节点集合
                communities = {}
                for comm_id in data[self.community_col].unique():
                    comm_nodes = data[data[self.community_col] == comm_id]
                    communities[comm_id] = {
                        'nodes': set(comm_nodes['geo_rcid'].values),
                        'size': len(comm_nodes)
                    }
                self.yearly_communities[year] = communities
        
        logging.info(f"Successfully loaded {len(available_years)} years: {available_years}")
        return available_years
    
    def precompute_attribute_distributions(self, years):
        """
        【优化1】预计算所有社区的属性分布
        这样每个社区的分布只计算一次
        """
        logging.info("Precomputing attribute distributions for all communities...")
        
        for year in years:
            if year not in self.yearly_data:
                continue
            
            self.attribute_distributions[year] = {}
            
            df = self.yearly_data[year]
            
            # 【优化2】按社区分组，避免重复过滤
            grouped = df.groupby(self.community_col)
            
            for comm_id, comm_data in grouped:
                # 提取NAICS 2位码
                naics_values = comm_data['naics_code'].apply(
                    lambda x: str(x)[:2] if pd.notna(x) and str(x) != 'unknown' and len(str(x)) >= 2 else None
                ).dropna()
                naics_dist = naics_values.value_counts(normalize=True).to_dict() if len(naics_values) > 0 else {}
                
                # 提取State
                state_values = comm_data['real_state'].replace('unknown', None).dropna()
                state_dist = state_values.value_counts(normalize=True).to_dict() if len(state_values) > 0 else {}
                
                # 提取Metro
                metro_values = comm_data['real_metro_area'].replace('unknown', None).dropna()
                metro_dist = metro_values.value_counts(normalize=True).to_dict() if len(metro_values) > 0 else {}
                
                # 预计算主导属性
                dominant_naics = max(naics_dist.items(), key=lambda x: x[1])[0] if naics_dist else None
                dominant_state = max(state_dist.items(), key=lambda x: x[1])[0] if state_dist else None
                
                self.attribute_distributions[year][comm_id] = {
                    'naics_dist': naics_dist,
                    'state_dist': state_dist,
                    'metro_dist': metro_dist,
                    'dominant_naics': dominant_naics,
                    'dominant_state': dominant_state
                }
            
            logging.info(f"  Precomputed distributions for year {year}: {len(self.attribute_distributions[year])} communities")
    
    def compute_distribution_similarity(self, dist1, dist2):
        """计算两个分布的相似度（余弦相似度）"""
        if not dist1 or not dist2:
            return 0.0
        
        # 获取所有键
        all_keys = set(dist1.keys()) | set(dist2.keys())
        
        # 【优化3】向量化计算
        vec1 = np.array([dist1.get(k, 0.0) for k in all_keys])
        vec2 = np.array([dist2.get(k, 0.0) for k in all_keys])
        
        # 余弦相似度
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        return similarity
    
    def compute_overlap_index(self, dist1, dist2):
        """计算重叠指数（共同类别的占比）"""
        if not dist1 or not dist2:
            return 0.0
        
        common_keys = set(dist1.keys()) & set(dist2.keys())
        
        if len(common_keys) == 0:
            return 0.0
        
        # 计算共同类别在两个分布中的总权重
        overlap1 = sum(dist1[k] for k in common_keys)
        overlap2 = sum(dist2[k] for k in common_keys)
        
        # 返回平均重叠度
        return (overlap1 + overlap2) / 2.0
    
    def compute_similarity(self, year1, comm1, year2, comm2):
        """
        计算两个社区之间的完整相似度指标
        
        Returns:
        --------
        dict: 包含所有指标的字典
        """
        nodes1 = self.yearly_communities[year1][comm1]['nodes']
        nodes2 = self.yearly_communities[year2][comm2]['nodes']
        
        intersection = nodes1 & nodes2
        union = nodes1 | nodes2
        
        size1 = len(nodes1)
        size2 = len(nodes2)
        overlap_size = len(intersection)
        union_size = len(union)
        
        # 核心指标1: Jaccard相似度
        jaccard = overlap_size / union_size if union_size > 0 else 0.0
        
        # 核心指标2: 前向保留率（year1 → year2）
        retention_forward = overlap_size / size1 if size1 > 0 else 0.0
        
        # 核心指标3: 后向保留率（year2 ← year1）
        retention_backward = overlap_size / size2 if size2 > 0 else 0.0
        
        # 规模变化
        if size1 > 0:
            growth_rate = (size2 - size1) / size1
        else:
            growth_rate = None
        
        # 【优化4】直接从缓存获取属性分布
        dist1 = self.attribute_distributions[year1][comm1]
        dist2 = self.attribute_distributions[year2][comm2]
        
        naics_dist1 = dist1['naics_dist']
        naics_dist2 = dist2['naics_dist']
        state_dist1 = dist1['state_dist']
        state_dist2 = dist2['state_dist']
        metro_dist1 = dist1['metro_dist']
        metro_dist2 = dist2['metro_dist']
        
        # 计算产业接近度（NAICS）
        naics_cosine_sim = self.compute_distribution_similarity(naics_dist1, naics_dist2)
        naics_overlap_index = self.compute_overlap_index(naics_dist1, naics_dist2)
        
        # 计算地理接近度（State）
        state_cosine_sim = self.compute_distribution_similarity(state_dist1, state_dist2)
        state_overlap_index = self.compute_overlap_index(state_dist1, state_dist2)
        
        # 计算地理接近度（Metro）
        metro_cosine_sim = self.compute_distribution_similarity(metro_dist1, metro_dist2)
        metro_overlap_index = self.compute_overlap_index(metro_dist1, metro_dist2)
        
        # 主导属性（直接从缓存获取）
        dominant_naics1 = dist1['dominant_naics']
        dominant_naics2 = dist2['dominant_naics']
        dominant_state1 = dist1['dominant_state']
        dominant_state2 = dist2['dominant_state']
        
        # 主导属性是否一致
        dominant_naics_match = (dominant_naics1 == dominant_naics2) if (dominant_naics1 and dominant_naics2) else None
        dominant_state_match = (dominant_state1 == dominant_state2) if (dominant_state1 and dominant_state2) else None
        
        return {
            # 核心节点重叠指标
            'jaccard': jaccard,
            'retention_forward': retention_forward,
            'retention_backward': retention_backward,
            'overlap_size': overlap_size,
            'union_size': union_size,
            'size1': size1,
            'size2': size2,
            'growth_rate': growth_rate,
            
            # 产业接近度（参考指标）
            'naics_cosine_similarity': naics_cosine_sim,
            'naics_overlap_index': naics_overlap_index,
            'dominant_naics_match': dominant_naics_match,
            
            # 地理接近度（参考指标）
            'state_cosine_similarity': state_cosine_sim,
            'state_overlap_index': state_overlap_index,
            'metro_cosine_similarity': metro_cosine_sim,
            'metro_overlap_index': metro_overlap_index,
            'dominant_state_match': dominant_state_match,
            
            # 主导属性
            'dominant_naics1': dominant_naics1,
            'dominant_naics2': dominant_naics2,
            'dominant_state1': dominant_state1,
            'dominant_state2': dominant_state2
        }
    
    def compute_year_pair_similarities(self, year1, year2):
        """
        计算两个年份之间所有社区对的相似度（无阈值筛选）
        
        Returns:
        --------
        list: 相似度记录列表
        """
        logging.info(f"  Computing similarities: {year1} ↔ {year2}")
        
        similarities = []
        year_gap = abs(year2 - year1)
        
        total_pairs = len(self.yearly_communities[year1]) * len(self.yearly_communities[year2])
        
        # 【优化5】批量构建记录，减少列表append开销
        for comm1 in self.yearly_communities[year1].keys():
            for comm2 in self.yearly_communities[year2].keys():
                result = self.compute_similarity(year1, comm1, year2, comm2)
                
                # 构建记录
                record = {
                    'year1': year1,
                    'community1': comm1,
                    'year2': year2,
                    'community2': comm2,
                    'year_gap': year_gap,
                    **result
                }
                
                similarities.append(record)
        
        logging.info(f"  Computed {len(similarities):,} pairs (total: {total_pairs:,})")
        return similarities
    
    def build_similarity_matrix(self, year_range, adjacent_only=True, parallel=False):
        """
        构建相似度矩阵（保存完整数据）
        
        【优化6】默认关闭并行，因为预计算后串行更快
        
        Parameters:
        -----------
        year_range : tuple
            年份范围 (start, end)
        adjacent_only : bool
            是否只计算相邻年份
        parallel : bool
            是否使用并行计算（预计算后通常不需要）
        
        Returns:
        --------
        pd.DataFrame: 相似度矩阵
        """
        logging.info("="*80)
        logging.info("Building Optimized Similarity Matrix (Complete Data)")
        logging.info(f"Level: {self.level}")
        logging.info(f"Adjacent only: {adjacent_only}")
        logging.info(f"Parallel: {parallel}")
        logging.info("="*80)
        
        available_years = sorted(self.yearly_communities.keys())
        logging.info(f"Available years: {available_years}")
        
        # 【优化核心】预计算所有属性分布
        self.precompute_attribute_distributions(available_years)
        
        # 生成年份对
        if adjacent_only:
            year_pairs = [(available_years[i], available_years[i+1]) 
                         for i in range(len(available_years)-1)]
            logging.info(f"Computing {len(year_pairs)} adjacent year pairs")
        else:
            from itertools import combinations
            year_pairs = list(combinations(available_years, 2))
            logging.info(f"Computing {len(year_pairs)} total year pairs")
        
        all_similarities = []
        
        # 【优化7】预计算后串行通常更快，避免进程间通信开销
        if parallel and len(year_pairs) > 1:
            logging.warning("Parallel mode may be slower after precomputation. Consider using serial mode.")
            # 并行计算逻辑保留但不推荐
            with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                future_to_pair = {
                    executor.submit(
                        self._compute_pair_wrapper, year1, year2
                    ): (year1, year2)
                    for year1, year2 in year_pairs
                }
                
                completed = 0
                for future in as_completed(future_to_pair):
                    year1, year2 = future_to_pair[future]
                    try:
                        pair_similarities = future.result()
                        all_similarities.extend(pair_similarities)
                        completed += 1
                        
                        if completed % 5 == 0 or completed == len(year_pairs):
                            logging.info(f"Progress: {completed}/{len(year_pairs)} pairs completed")
                    
                    except Exception as e:
                        logging.error(f"Error computing {year1}-{year2}: {e}")
        
        else:
            # 串行计算（推荐）
            logging.info("Using serial processing (recommended after precomputation)...")
            
            for idx, (year1, year2) in enumerate(year_pairs, 1):
                try:
                    pair_similarities = self.compute_year_pair_similarities(year1, year2)
                    all_similarities.extend(pair_similarities)
                    
                    if idx % 5 == 0 or idx == len(year_pairs):
                        logging.info(f"Progress: {idx}/{len(year_pairs)} pairs completed")
                
                except Exception as e:
                    logging.error(f"Error computing {year1}-{year2}: {e}")
        
        # 【优化8】批量创建DataFrame
        df = pd.DataFrame(all_similarities)
        
        logging.info("="*80)
        logging.info(f"Similarity matrix built: {len(df):,} total pairs")
        logging.info("="*80)
        
        return df
    
    def _compute_pair_wrapper(self, year1, year2):
        """包装函数用于并行计算（不推荐使用）"""
        # 注意：并行模式下需要重新加载数据和预计算
        self.yearly_data[year1] = self.load_year_data(year1)
        self.yearly_data[year2] = self.load_year_data(year2)
        
        # 重建社区字典
        for year in [year1, year2]:
            if year not in self.yearly_communities and self.yearly_data[year] is not None:
                communities = {}
                data = self.yearly_data[year]
                for comm_id in data[self.community_col].unique():
                    comm_nodes = data[data[self.community_col] == comm_id]
                    communities[comm_id] = {
                        'nodes': set(comm_nodes['geo_rcid'].values),
                        'size': len(comm_nodes)
                    }
                self.yearly_communities[year] = communities
        
        # 重新预计算属性分布
        self.precompute_attribute_distributions([year1, year2])
        
        return self.compute_year_pair_similarities(year1, year2)
    
    def analyze_similarity_matrix(self, df):
        """分析相似度矩阵的统计信息"""
        logging.info("\nAnalyzing similarity matrix...")

        if df.empty:
            logging.warning("Empty similarity matrix")
            return {}

        # 基础统计
        analysis = {
            'total_pairs': len(df),
            # 【修复】将元组键转换为字符串
            'year_pairs': {f"{k[0]}-{k[1]}": int(v) for k, v in df.groupby(['year1', 'year2']).size().to_dict().items()},
            'jaccard_stats': {
                'mean': float(df['jaccard'].mean()),
                'median': float(df['jaccard'].median()),
                'std': float(df['jaccard'].std()),
                'min': float(df['jaccard'].min()),
                'max': float(df['jaccard'].max()),
                'q25': float(df['jaccard'].quantile(0.25)),
                'q75': float(df['jaccard'].quantile(0.75))
            },
            'retention_forward_stats': {
                'mean': float(df['retention_forward'].mean()),
                'median': float(df['retention_forward'].median()),
                'std': float(df['retention_forward'].std())
            },
            'retention_backward_stats': {
                'mean': float(df['retention_backward'].mean()),
                'median': float(df['retention_backward'].median()),
                'std': float(df['retention_backward'].std())
            },
            'attribute_proximity': {
                'naics_cosine_mean': float(df['naics_cosine_similarity'].mean()),
                'state_cosine_mean': float(df['state_cosine_similarity'].mean()),
                'metro_cosine_mean': float(df['metro_cosine_similarity'].mean()),
                'naics_overlap_mean': float(df['naics_overlap_index'].mean()),
                'state_overlap_mean': float(df['state_overlap_index'].mean())
            }
        }

        # 打印统计信息
        print("\n" + "="*80)
        print("SIMILARITY MATRIX ANALYSIS")
        print("="*80)
        print(f"Total pairs: {analysis['total_pairs']:,}")

        print(f"\nJaccard similarity statistics:")
        print(f"  Mean: {analysis['jaccard_stats']['mean']:.4f}")
        print(f"  Median: {analysis['jaccard_stats']['median']:.4f}")
        print(f"  Std: {analysis['jaccard_stats']['std']:.4f}")
        print(f"  Range: [{analysis['jaccard_stats']['min']:.4f}, {analysis['jaccard_stats']['max']:.4f}]")

        print(f"\nRetention forward statistics:")
        print(f"  Mean: {analysis['retention_forward_stats']['mean']:.4f}")
        print(f"  Median: {analysis['retention_forward_stats']['median']:.4f}")

        print(f"\nRetention backward statistics:")
        print(f"  Mean: {analysis['retention_backward_stats']['mean']:.4f}")
        print(f"  Median: {analysis['retention_backward_stats']['median']:.4f}")

        print(f"\nAttribute proximity (reference):")
        print(f"  NAICS cosine similarity: {analysis['attribute_proximity']['naics_cosine_mean']:.4f}")
        print(f"  State cosine similarity: {analysis['attribute_proximity']['state_cosine_mean']:.4f}")
        print(f"  Metro cosine similarity: {analysis['attribute_proximity']['metro_cosine_mean']:.4f}")

        print("="*80 + "\n")

        return analysis
    
    def save_similarity_matrix(self, df, suffix='adjacent'):
        """
        保存相似度矩阵
        
        Parameters:
        -----------
        df : pd.DataFrame
            相似度矩阵
        suffix : str
            文件名后缀
        """
        logging.info(f"Saving similarity matrix to {self.output_dir}...")
        
        # 保存为parquet（主格式）
        parquet_file = self.output_dir / f"similarity_matrix_level{self.level}_{suffix}.parquet"
        df.to_parquet(parquet_file, engine='pyarrow', compression='snappy', index=False)
        logging.info(f"Saved parquet: {parquet_file} ({len(df):,} rows)")
        
        # 保存为pickle（用于快速加载）
        pickle_file = self.output_dir / f"similarity_matrix_level{self.level}_{suffix}.pkl"
        with open(pickle_file, 'wb') as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
        logging.info(f"Saved pickle: {pickle_file}")
        
        # 保存元数据
        metadata = {
            'level': self.level,
            'total_pairs': len(df),
            'columns': list(df.columns),
            'year_pairs_computed': {str(k): int(v) for k, v in df.groupby(['year1', 'year2']).size().to_dict().items()},
            'years_covered': sorted([int(x) for x in set(df['year1'].unique()) | set(df['year2'].unique())]),
            'creation_time': pd.Timestamp.now().isoformat(),
            'data_description': {
                'jaccard': 'Jaccard similarity coefficient (node overlap)',
                'retention_forward': 'Retention rate from year1 to year2',
                'retention_backward': 'Retention rate from year2 to year1',
                'naics_cosine_similarity': 'Cosine similarity of NAICS distributions (reference)',
                'state_cosine_similarity': 'Cosine similarity of state distributions (reference)',
                'metro_cosine_similarity': 'Cosine similarity of metro area distributions (reference)',
                'naics_overlap_index': 'Overlap index of NAICS categories (reference)',
                'state_overlap_index': 'Overlap index of states (reference)',
                'metro_overlap_index': 'Overlap index of metro areas (reference)'
            }
        }
        
        metadata_file = self.output_dir / f"similarity_matrix_metadata_level{self.level}_{suffix}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logging.info(f"Saved metadata: {metadata_file}")


def main():
    """主函数 - 构建优化的相似度矩阵"""
    
    results_dir = "./workforce_community_results_adaptive_4d"
    output_dir = "./similarity_matrices_complete"
    
    year_range = (2000, 2024)
    level = 1
    
    # 参数设置
    params = {
        'adjacent_only': False,    # True: 只计算相邻年份, False: 计算所有年份对
        'parallel': False,        # 预计算后串行更快
        'n_workers': None
    }
    
    logging.info("="*80)
    logging.info("OPTIMIZED SIMILARITY MATRIX BUILDER")
    logging.info("="*80)
    logging.info(f"Results directory: {results_dir}")
    logging.info(f"Output directory: {output_dir}")
    logging.info(f"Year range: {year_range[0]}-{year_range[1]}")
    logging.info(f"Community level: {level}")
    logging.info(f"Parameters: {params}")
    logging.info("="*80 + "\n")
    
    # 创建构建器
    builder = OptimizedSimilarityMatrixBuilder(
        results_dir, 
        level=level, 
        output_dir=output_dir,
        n_workers=params['n_workers']
    )
    
    # 加载数据
    available_years = builder.load_all_years(year_range)
    
    if len(available_years) < 2:
        logging.error("Need at least 2 years of data")
        return
    
    # 构建相似度矩阵
    start_time = time.time()
    df_similarity = builder.build_similarity_matrix(
        year_range,
        adjacent_only=params['adjacent_only'],
        parallel=params['parallel']
    )
    computation_time = time.time() - start_time
    
    logging.info(f"Computation completed in {computation_time:.2f} seconds")
    
    # 分析矩阵
    analysis = builder.analyze_similarity_matrix(df_similarity)
    
    # 保存结果
    suffix = 'adjacent' if params['adjacent_only'] else 'complete'
    builder.save_similarity_matrix(df_similarity, suffix=suffix)
    
    # 保存分析结果
    analysis['computation_time_seconds'] = computation_time
    with open(builder.output_dir / f"similarity_analysis_level{level}_{suffix}.json", 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    logging.info("\nOptimized similarity matrix construction completed successfully!")
    
    return df_similarity, analysis


if __name__ == "__main__":
    df_similarity, analysis = main()