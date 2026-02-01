# 自适应劳动力网络社区检测 - 基于4维属性纯净度的停止条件
import igraph as ig
import leidenalg
import pandas as pd
import numpy as np
import logging
from collections import defaultdict, Counter
from pathlib import Path
import json
import gc
import time
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AdaptiveCommunityDetector:
    def __init__(self, data_dir, use_cache=False, cache_dir="./cache"):
        self.data_dir = Path(data_dir)
        self.use_cache = use_cache
        data_dir_name = Path(data_dir).name
        self.cache_dir = Path(cache_dir) / data_dir_name
        if use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== 数据加载和预处理 ====================
    
    def preprocess_graph_data(self, weight_threshold=3):
        """预处理图数据 - 只基于权重筛选"""
        logging.info(f"Preprocessing graph data with weight threshold: {weight_threshold}")
        
        # 加载边数据
        edges_file = self.data_dir / "edges_data.parquet"
        if not edges_file.exists():
            raise FileNotFoundError(f"Edges file not found: {edges_file}")
        
        sample_edges = pd.read_parquet(edges_file, engine='pyarrow').head(1)
        weight_col = 'flow_count' if 'flow_count' in sample_edges.columns else 'weight'
        logging.info(f"Using '{weight_col}' as weight column")
        
        edges_data = pd.read_parquet(edges_file, engine='pyarrow')
        edges_data = edges_data[edges_data[weight_col] >= weight_threshold].copy()
        if weight_col != 'weight':
            edges_data['weight'] = edges_data[weight_col]
        
        logging.info(f"Loaded {len(edges_data)} edges after weight filtering")
        
        # 加载节点数据
        nodes_file = self.data_dir / "nodes_data.parquet"
        if not nodes_file.exists():
            raise FileNotFoundError(f"Nodes file not found: {nodes_file}")
        
        sample_nodes = pd.read_parquet(nodes_file, engine='pyarrow').head(1)
        node_id_field = 'geo_rcid' if 'geo_rcid' in sample_nodes.columns else 'rcid'
        logging.info(f"Using '{node_id_field}' as node ID field")
        
        nodes_data = pd.read_parquet(nodes_file, engine='pyarrow')
        
        # 数据一致性验证
        connected_nodes = set(edges_data['source']) | set(edges_data['target'])
        nodes_filtered = nodes_data[nodes_data[node_id_field].isin(connected_nodes)].copy()
        available_nodes = set(nodes_filtered[node_id_field])
        
        if missing := connected_nodes - available_nodes:
            logging.warning(f"Found {len(missing)} nodes missing from node data")
            edges_data = edges_data[
                edges_data['source'].isin(available_nodes) & 
                edges_data['target'].isin(available_nodes)
            ].copy()
        
        final_connected = set(edges_data['source']) | set(edges_data['target'])
        nodes_final = nodes_filtered[nodes_filtered[node_id_field].isin(final_connected)].copy()
        
        logging.info(f"Final data: {len(nodes_final)} nodes, {len(edges_data)} edges")
        return nodes_final, edges_data, node_id_field

    def build_igraph(self, nodes_data, edges_data, node_id_field):
        """构建igraph对象"""
        logging.info("Building igraph object...")
        start_time = time.time()
        
        # 标准化数据类型
        nodes_data[node_id_field] = nodes_data[node_id_field].astype(str)
        edges_data[['source', 'target']] = edges_data[['source', 'target']].astype(str)
        
        # 创建节点映射
        node_list = nodes_data[node_id_field].tolist()
        node_map = {node: idx for idx, node in enumerate(node_list)}
        
        # 构建边列表
        edges_data['source_idx'] = edges_data['source'].map(node_map)
        edges_data['target_idx'] = edges_data['target'].map(node_map)
        valid_edges = edges_data.dropna(subset=['source_idx', 'target_idx'])
        valid_edges[['source_idx', 'target_idx']] = valid_edges[['source_idx', 'target_idx']].astype(int)
        
        # 构建图
        edge_list = list(zip(valid_edges['source_idx'], valid_edges['target_idx']))
        G_ig = ig.Graph(n=len(node_list), edges=edge_list, directed=True)
        G_ig.es['weight'] = valid_edges['weight'].tolist()
        G_ig.vs['name'] = node_list
        
        # 添加节点属性
        self._add_node_attributes(G_ig, nodes_data, node_id_field, node_list)
        
        logging.info(f"Igraph built in {time.time()-start_time:.2f}s: {G_ig.vcount()} vertices, {G_ig.ecount()} edges")
        return G_ig, node_map

    def _add_node_attributes(self, G_ig, nodes_data, node_id_field, node_list):
        """添加节点属性"""
        numeric_attrs = ['year_founded', 'employee_count', 'role_entropy', 
                        'avg_seniority', 'seniority_p25', 'seniority_median', 'seniority_p75',
                        'avg_salary', 'median_salary', 'avg_total_compensation', 'avg_remote_suitability']
        
        all_attrs = ['rcid', 'company_name', 'ultimate_parent_rcid', 'child_rcid',
                    'real_country', 'real_state', 'real_metro_area',
                    'naics_code', 'rics_k50', 'rics_k200', 'rics_k400',
                    'employee_count', 'year_founded', 'role_k1500_vector', 'role_entropy',
                    'avg_seniority', 'seniority_p25', 'seniority_median', 'seniority_p75',
                    'avg_salary', 'median_salary', 'avg_total_compensation', 'avg_remote_suitability']
        
        available = set(nodes_data.columns)
        for col in all_attrs:
            if col in available:
                fill_value = 0 if col in numeric_attrs else 'unknown'
                attr_dict = dict(zip(nodes_data[node_id_field], nodes_data[col].fillna(fill_value)))
                G_ig.vs[col] = [attr_dict[name] for name in node_list]
                logging.info(f"Added attribute: {col}")
    
    # ==================== 属性纯净度计算 ====================
    
    def calculate_purity(self, values):
        """计算纯净度 = 最高频类别占比"""
        valid = [v for v in values if v and v != 'unknown' and v != '']
        if not valid:
            return 0.0
        return Counter(valid).most_common(1)[0][1] / len(valid)

    def get_dominant_category(self, values):
        """获取主导类别"""
        valid = [v for v in values if v and v != 'unknown' and v != '']
        return Counter(valid).most_common(1)[0][0] if valid else 'unknown'

    def calculate_global_purity_baseline(self, G_ig):
        """计算全局4维属性纯净度基准"""
        logging.info("Calculating global purity baselines...")
        
        collectors = {'naics_2d': [], 'naics_4d': [], 'state': [], 'metro': []}
        
        for v in G_ig.vs:
            naics = v['naics_code']
            if naics != 'unknown' and naics != '':
                naics_str = str(naics)
                if len(naics_str) >= 2:
                    collectors['naics_2d'].append(naics_str[:2])
                if len(naics_str) >= 4:
                    collectors['naics_4d'].append(naics_str[:4])
            
            if (state := v['real_state']) != 'unknown' and state != '':
                collectors['state'].append(state)
            if (metro := v['real_metro_area']) != 'unknown' and metro != '':
                collectors['metro'].append(metro)
        
        baseline = {
            'naics_2digit_purity': self.calculate_purity(collectors['naics_2d']),
            'naics_4digit_purity': self.calculate_purity(collectors['naics_4d']),
            'state_purity': self.calculate_purity(collectors['state']),
            'metro_area_purity': self.calculate_purity(collectors['metro'])
        }
        
        logging.info(f"Global baseline - NAICS 2d: {baseline['naics_2digit_purity']:.4f}, "
                    f"NAICS 4d: {baseline['naics_4digit_purity']:.4f}, "
                    f"State: {baseline['state_purity']:.4f}, Metro: {baseline['metro_area_purity']:.4f}")
        return baseline

    def evaluate_community_attributes(self, G_ig, vertex_indices, global_baseline):
        """评估社区的4维属性纯净度"""
        collectors = {'naics_2d': [], 'naics_4d': [], 'state': [], 'metro': []}
        
        for idx in vertex_indices:
            naics = G_ig.vs[idx]['naics_code']
            if naics != 'unknown' and naics != '':
                naics_str = str(naics)
                if len(naics_str) >= 2:
                    collectors['naics_2d'].append(naics_str[:2])
                if len(naics_str) >= 4:
                    collectors['naics_4d'].append(naics_str[:4])
            
            if (state := G_ig.vs[idx]['real_state']) != 'unknown' and state != '':
                collectors['state'].append(state)
            if (metro := G_ig.vs[idx]['real_metro_area']) != 'unknown' and metro != '':
                collectors['metro'].append(metro)
        
        size = len(vertex_indices)
        return {
            'size': size,
            'naics_2digit_purity': self.calculate_purity(collectors['naics_2d']),
            'naics_4digit_purity': self.calculate_purity(collectors['naics_4d']),
            'state_purity': self.calculate_purity(collectors['state']),
            'metro_area_purity': self.calculate_purity(collectors['metro']),
            'dominant_naics_2digit': self.get_dominant_category(collectors['naics_2d']),
            'dominant_naics_4digit': self.get_dominant_category(collectors['naics_4d']),
            'dominant_state': self.get_dominant_category(collectors['state']),
            'dominant_metro': self.get_dominant_category(collectors['metro']),
            'naics_2digit_coverage': len(collectors['naics_2d']) / size if size else 0,
            'naics_4digit_coverage': len(collectors['naics_4d']) / size if size else 0,
            'state_coverage': len(collectors['state']) / size if size else 0,
            'metro_coverage': len(collectors['metro']) / size if size else 0
        }
    
    # ==================== 社区检测逻辑 ====================
    
    def should_continue_split(self, comm_eval, global_baseline, min_size, purity_multiplier, current_depth, max_depth):
        """判断是否继续细分 - 4维属性都达标才停止"""
        if current_depth >= max_depth:
            return False, f"max_depth_reached_{max_depth}"
        if comm_eval['size'] < min_size:
            return False, f"size_too_small_{comm_eval['size']}"
        
        # 计算阈值
        thresholds = {k: global_baseline[k] * purity_multiplier 
                     for k in ['naics_2digit_purity', 'naics_4digit_purity', 'state_purity', 'metro_area_purity']}
        
        # 检查是否都达标
        meets = {k: comm_eval[k] >= thresholds[k] for k in thresholds}
        
        if all(meets.values()):
            return False, (f"all_four_pure_"
                          f"n2d={comm_eval['naics_2digit_purity']:.3f}({thresholds['naics_2digit_purity']:.3f})_"
                          f"n4d={comm_eval['naics_4digit_purity']:.3f}({thresholds['naics_4digit_purity']:.3f})_"
                          f"st={comm_eval['state_purity']:.3f}({thresholds['state_purity']:.3f})_"
                          f"mt={comm_eval['metro_area_purity']:.3f}({thresholds['metro_area_purity']:.3f})_"
                          f"dom_{comm_eval['dominant_naics_2digit']}_{comm_eval['dominant_state']}_{comm_eval['dominant_metro']}")
        
        # 记录未达标项
        unmet = [f"{k.split('_')[0][:3]}={comm_eval[k]:.3f}<{thresholds[k]:.3f}" 
                for k in thresholds if not meets[k]]
        return True, f"continue_unmet_" + "_".join(unmet)

    def filter_small_communities(self, communities, min_size):
        """过滤小社区"""
        communities = np.array(communities)
        unique, counts = np.unique(communities, return_counts=True)
        small = set(unique[counts < min_size])
        communities[np.isin(communities, list(small))] = -1
        
        valid_count = np.sum(communities != -1)
        unique_count = len(set(communities[communities != -1]))
        if unique_count > 0:
            logging.info(f"Filtered: {unique_count} valid communities, {valid_count} nodes kept")
        return communities.tolist()

    def adaptive_hierarchical_detection(self, min_size=50, purity_multiplier=1.2, resolution=1.0, 
                                       iterations=300, seed=42, weight_threshold=3, max_depth=6):
        """自适应层级社区检测主函数"""
        logging.info("="*80)
        logging.info("Starting ADAPTIVE hierarchical community detection (4-dimension purity)")
        logging.info(f"Parameters: min_size={min_size}, purity_multiplier={purity_multiplier}, "
                    f"resolution={resolution}, max_depth={max_depth}")
        logging.info("="*80)
        
        # 数据准备
        nodes_data, edges_data, node_id_field = self.preprocess_graph_data(weight_threshold)
        G_ig, node_map = self.build_igraph(nodes_data, edges_data, node_id_field)
        global_baseline = self.calculate_global_purity_baseline(G_ig)
        
        # Level 1检测
        logging.info("\n" + "="*60)
        logging.info("Detecting Level 1 communities...")
        logging.info("="*60)
        
        partition = leidenalg.find_partition(G_ig, leidenalg.RBConfigurationVertexPartition,
                                            weights='weight', resolution_parameter=resolution,
                                            n_iterations=iterations, seed=seed)
        communities_l1 = self.filter_small_communities(partition.membership, min_size)
        
        # 初始化
        community_paths = {idx: str(comm) for idx, comm in enumerate(communities_l1) if comm != -1}
        community_metadata = {}
        
        valid_l1 = [c for c in communities_l1 if c != -1]
        logging.info(f"Level 1: {len(set(valid_l1))} communities, {len(valid_l1)} nodes")
        
        # 递归处理
        for l1_comm in set(valid_l1):
            l1_indices = [i for i, c in enumerate(communities_l1) if c == l1_comm]
            logging.info(f"\nProcessing L1 community {l1_comm} ({len(l1_indices)} nodes)...")
            
            self._recursive_split(G_ig, l1_indices, str(l1_comm), 1, max_depth, min_size, 
                                purity_multiplier, resolution, iterations, seed, global_baseline,
                                community_paths, community_metadata)
        
        self._assign_hierarchical_labels(G_ig, community_paths, community_metadata)
        
        logging.info("\n" + "="*80)
        logging.info("Adaptive hierarchical detection completed!")
        logging.info("="*80)
        return G_ig, community_metadata, global_baseline

    def _recursive_split(self, G_ig, vertex_indices, parent_path, current_depth, max_depth, min_size, 
                        purity_multiplier, resolution, iterations, seed, global_baseline, 
                        community_paths, community_metadata):
        """递归分裂社区"""
        comm_eval = self.evaluate_community_attributes(G_ig, vertex_indices, global_baseline)
        
        # 记录元数据
        community_metadata[parent_path] = {
            'depth': current_depth, 'size': comm_eval['size'], 'is_leaf': False,
            **{k: comm_eval[k] for k in ['naics_2digit_purity', 'naics_4digit_purity', 'state_purity', 'metro_area_purity',
                                         'dominant_naics_2digit', 'dominant_naics_4digit', 'dominant_state', 'dominant_metro',
                                         'naics_2digit_coverage', 'naics_4digit_coverage', 'state_coverage', 'metro_coverage']}
        }
        
        # 判断是否停止
        should_split, reason = self.should_continue_split(comm_eval, global_baseline, min_size, 
                                                          purity_multiplier, current_depth, max_depth)
        
        if not should_split:
            logging.info(f"  └─ STOP at {parent_path} (depth {current_depth}): {reason}")
            community_metadata[parent_path].update({'is_leaf': True, 'stop_reason': reason})
            return
        
        # 尝试分裂
        try:
            subgraph = G_ig.subgraph(vertex_indices)
            if subgraph.ecount() == 0:
                logging.info(f"  └─ STOP at {parent_path}: no_internal_edges")
                community_metadata[parent_path].update({'is_leaf': True, 'stop_reason': 'no_internal_edges'})
                return
            
            partition = leidenalg.find_partition(subgraph, leidenalg.RBConfigurationVertexPartition,
                                                weights='weight', resolution_parameter=resolution,
                                                n_iterations=iterations, seed=seed)
            sub_communities = self.filter_small_communities(partition.membership, min_size)
            unique_sub = set([c for c in sub_communities if c != -1])
            
            if len(unique_sub) <= 1:
                logging.info(f"  └─ STOP at {parent_path}: no_effective_split")
                community_metadata[parent_path].update({'is_leaf': True, 'stop_reason': 'no_effective_split'})
                return
            
            logging.info(f"  ├─ SPLIT {parent_path} into {len(unique_sub)} sub-communities")
            
            # 更新路径并递归
            for sub_idx, sub_comm in enumerate(sub_communities):
                if sub_comm != -1:
                    community_paths[vertex_indices[sub_idx]] = f"{parent_path}.{sub_comm}"
            
            for sub_comm in unique_sub:
                sub_indices = [vertex_indices[i] for i, c in enumerate(sub_communities) if c == sub_comm]
                self._recursive_split(G_ig, sub_indices, f"{parent_path}.{sub_comm}", current_depth + 1,
                                    max_depth, min_size, purity_multiplier, resolution, iterations, seed,
                                    global_baseline, community_paths, community_metadata)
        except Exception as e:
            logging.warning(f"  └─ ERROR at {parent_path}: {str(e)[:100]}")
            community_metadata[parent_path].update({'is_leaf': True, 'stop_reason': f"error_{str(e)[:50]}"})

    def _assign_hierarchical_labels(self, G_ig, community_paths, community_metadata):
        """将社区路径转换为各层级属性列"""
        max_depth = max(meta['depth'] for meta in community_metadata.values())
        logging.info(f"\nMaximum community depth reached: {max_depth}")
        
        for depth in range(1, max_depth + 1):
            level_labels = []
            for idx in range(G_ig.vcount()):
                if idx in community_paths:
                    parts = community_paths[idx].split('.')
                    level_labels.append('.'.join(parts[:depth]) if len(parts) >= depth else community_paths[idx])
                else:
                    level_labels.append("-1")
            
            G_ig.vs[f'community_level{depth}'] = level_labels
            valid = [l for l in level_labels if l != "-1"]
            logging.info(f"Level {depth}: {len(set(valid))} communities, {len(valid)} nodes")
    
    # ==================== 结果保存 ====================
    
    def save_results(self, G_ig, community_metadata, global_baseline, output_dir, prefix='workforce_community', params=None):
        """保存结果和社区元数据"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_attributes = G_ig.vs.attributes()
        community_attrs = sorted([a for a in all_attributes if a.startswith('community_level')])
        
        if not community_attrs:
            logging.warning("未找到社区属性")
            return None, None
        
        # 构建结果数据
        results_data = {'geo_rcid': G_ig.vs['name']}
        for attr in community_attrs:
            results_data[attr] = G_ig.vs[attr]
        
        for attr in ['rcid', 'company_name', 'ultimate_parent_rcid', 'child_rcid',
                    'real_country', 'real_state', 'real_metro_area', 'naics_code',
                    'rics_k50', 'rics_k200', 'rics_k400', 'employee_count', 'year_founded',
                    'role_k1500_vector', 'role_entropy', 'avg_seniority', 'seniority_p25',
                    'seniority_median', 'seniority_p75', 'avg_salary', 'median_salary',
                    'avg_total_compensation', 'avg_remote_suitability']:
            if attr in all_attributes:
                results_data[attr] = G_ig.vs[attr]
        
        results_df = pd.DataFrame(results_data)
        
        # 保存主结果
        results_df.to_parquet(output_dir / f"{prefix}_results.parquet", engine='pyarrow', compression='snappy', index=False)
        results_df.to_csv(output_dir / f"{prefix}_results.csv", index=False)
        logging.info(f"Results saved to {output_dir / f'{prefix}_results.parquet'}")
        
        # 保存元数据
        metadata_df = pd.DataFrame([
            {'community_path': path, **meta, 'stop_reason': meta.get('stop_reason', 'continued_to_split')}
            for path, meta in community_metadata.items()
        ])
        metadata_df.to_parquet(output_dir / f"{prefix}_community_metadata.parquet", engine='pyarrow', compression='snappy', index=False)
        metadata_df.to_csv(output_dir / f"{prefix}_community_metadata.csv", index=False)
        logging.info(f"Metadata saved to {output_dir / f'{prefix}_community_metadata.parquet'}")
        
        # 生成摘要
        summary_text = self._generate_readable_summary(results_df, metadata_df, community_attrs, global_baseline, params)
        with open(output_dir / f"{prefix}_summary.txt", 'w', encoding='utf-8') as f:
            f.write(summary_text)
        logging.info(f"Summary saved to {output_dir / f'{prefix}_summary.txt'}")
        
        return results_df, metadata_df

    def _generate_readable_summary(self, results_df, metadata_df, community_attrs, global_baseline, params):
        """生成可读的摘要报告"""
        leaf = metadata_df[metadata_df['is_leaf'] == True]
        
        summary = ["="*80, "ADAPTIVE HIERARCHICAL COMMUNITY DETECTION SUMMARY (4-Dimension)", "="*80, ""]
        
        if params:
            summary.extend([
                "Detection Parameters:",
                f"  Min community size: {params.get('min_size', 'N/A')}",
                f"  Purity multiplier: {params.get('purity_multiplier', 'N/A')}",
                f"  Resolution: {params.get('resolution', 'N/A')}",
                f"  Max depth: {params.get('max_depth', 'N/A')}",
                f"  Weight threshold: {params.get('weight_threshold', 'N/A')}", ""
            ])
        
        multiplier = params.get('purity_multiplier', 1.0) if params else 1.0
        summary.extend([
            "Global Purity Baselines:",
            f"  NAICS 2-digit: {global_baseline['naics_2digit_purity']:.4f}",
            f"  NAICS 4-digit: {global_baseline['naics_4digit_purity']:.4f}",
            f"  State: {global_baseline['state_purity']:.4f}",
            f"  Metro Area: {global_baseline['metro_area_purity']:.4f}",
            f"  Stop thresholds (baseline × {multiplier}):",
            f"    NAICS 2-digit: {global_baseline['naics_2digit_purity'] * multiplier:.4f}",
            f"    NAICS 4-digit: {global_baseline['naics_4digit_purity'] * multiplier:.4f}",
            f"    State: {global_baseline['state_purity'] * multiplier:.4f}",
            f"    Metro Area: {global_baseline['metro_area_purity'] * multiplier:.4f}", ""
        ])
        
        summary.append("Depth Distribution:")
        for depth, count in metadata_df['depth'].value_counts().sort_index().items():
            leaf_count = len(metadata_df[(metadata_df['depth']==depth) & (metadata_df['is_leaf']==True)])
            node_count = len(results_df[results_df[f'community_level{depth}'] != "-1"])
            summary.append(f"  Level {depth}: {count} communities ({leaf_count} leaves), {node_count} nodes")
        summary.append("")
        
        summary.append("Stop Reasons Distribution (Leaf Communities):")
        reason_groups = defaultdict(int)
        for reason in leaf['stop_reason']:
            if 'all_four_pure' in reason:
                reason_groups['All 4 attributes met thresholds'] += 1
            elif 'continue_unmet' in reason:
                reason_groups['Some attributes below threshold'] += 1
            elif 'size_too_small' in reason:
                reason_groups['Size below minimum'] += 1
            elif 'max_depth' in reason:
                reason_groups['Max depth reached'] += 1
            elif 'no_effective_split' in reason:
                reason_groups['No effective split'] += 1
            elif 'no_internal_edges' in reason:
                reason_groups['No internal edges'] += 1
            else:
                reason_groups['Other'] += 1
        
        for reason, count in sorted(reason_groups.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(leaf) * 100 if len(leaf) > 0 else 0
            summary.append(f"  {reason}: {count} ({pct:.1f}%)")
        summary.append("")
        
        summary.extend([
            "Purity Statistics (Leaf Communities):",
            f"  NAICS 2-digit: Mean={leaf['naics_2digit_purity'].mean():.4f}, Median={leaf['naics_2digit_purity'].median():.4f}",
            f"  NAICS 4-digit: Mean={leaf['naics_4digit_purity'].mean():.4f}, Median={leaf['naics_4digit_purity'].median():.4f}",
            f"  State: Mean={leaf['state_purity'].mean():.4f}, Median={leaf['state_purity'].median():.4f}",
            f"  Metro Area: Mean={leaf['metro_area_purity'].mean():.4f}, Median={leaf['metro_area_purity'].median():.4f}", "",
            "Community Size Statistics (Leaf Communities):",
            f"  Mean: {leaf['size'].mean():.1f}, Median: {leaf['size'].median():.1f}",
            f"  Min: {leaf['size'].min()}, Max: {leaf['size'].max()}", "",
            "Attribute Data Coverage (Leaf Communities):",
            f"  NAICS 2-digit: {leaf['naics_2digit_coverage'].mean():.2%}",
            f"  NAICS 4-digit: {leaf['naics_4digit_coverage'].mean():.2%}",
            f"  State: {leaf['state_coverage'].mean():.2%}",
            f"  Metro Area: {leaf['metro_coverage'].mean():.2%}", "",
            "="*80
        ])
        
        return "\n".join(summary)


# ==================== 主处理函数 ====================

def single_adaptive_detection(data_dir, output_dir, prefix='workforce_community', 
                              weight_threshold=3, detector_params=None):
    """单一图数据的自适应社区检测"""
    try:
        logging.info(f"\n{'='*80}\nStarting Adaptive Community Detection\nData: {data_dir}\n{'='*80}")
        
        detector = AdaptiveCommunityDetector(data_dir, use_cache=False)
        
        if detector_params is None:
            detector_params = {
                'min_size': 50, 'purity_multiplier': 1.2, 'resolution': 1.0,
                'iterations': 300, 'seed': 42, 'weight_threshold': weight_threshold, 'max_depth': 6
            }
        
        start_time = time.time()
        G_ig, community_metadata, global_baseline = detector.adaptive_hierarchical_detection(**detector_params)
        processing_time = time.time() - start_time
        
        logging.info(f"Detection completed in {processing_time:.2f}s")
        
        results_df, metadata_df = detector.save_results(
            G_ig, community_metadata, global_baseline, output_dir, prefix=prefix, params=detector_params
        )
        
        result_stats = {
            'data_directory': str(data_dir),
            'processing_time': processing_time,
            'total_nodes': G_ig.vcount(),
            'total_edges': G_ig.ecount(),
            'weight_threshold': weight_threshold,
            'max_depth_reached': max(m['depth'] for m in community_metadata.values()),
            'total_communities': len(community_metadata),
            'leaf_communities': sum(1 for m in community_metadata.values() if m['is_leaf']),
            'parameters': detector_params,
            'global_baseline': global_baseline
        }
        
        logging.info("Adaptive detection completed successfully!")
        del G_ig, detector, results_df, metadata_df
        gc.collect()
        
        return result_stats
        
    except Exception as e:
        logging.error(f"Error during detection: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return {'data_directory': str(data_dir), 'error': str(e), 'processing_time': 0}


def process_multiple_years_adaptive(base_data_dir, base_output_dir, year_range, 
                                    base_prefix='workforce_community', 
                                    weight_threshold=3, detector_params=None):
    """批量处理多年份的自适应社区检测"""
    base_data_path = Path(base_data_dir)
    base_output_path = Path(base_output_dir)
    
    logging.info(f"\n{'='*80}\nStarting Batch Adaptive Community Detection\n"
                f"Years: {year_range[0]}-{year_range[1]}\n{'='*80}")
    
    all_results = {}
    processed_count = failed_count = 0
    
    for year in range(year_range[0], year_range[1] + 1):
        window_start, window_end = year - 1, year
        data_dir = base_data_path / f"graph_{window_start}_{window_end}"
        
        if not data_dir.exists() or not all((data_dir / f).exists() for f in ['nodes_data.parquet', 'edges_data.parquet']):
            logging.warning(f"Skipping year {year}: missing data")
            failed_count += 1
            continue
        
        output_dir = base_output_path / f"results_{window_start}_{window_end}"
        prefix = f"{base_prefix}_{window_start}_{window_end}"
        
        try:
            logging.info(f"\nProcessing year {year} (window {window_start}-{window_end})")
            result_stats = single_adaptive_detection(str(data_dir), str(output_dir), prefix, weight_threshold, detector_params)
            
            if 'error' not in result_stats:
                result_stats.update({'year': year, 'window_start': window_start, 'window_end': window_end})
                all_results[year] = result_stats
                processed_count += 1
                logging.info(f"Year {year} completed: {result_stats['total_nodes']:,} nodes, "
                           f"{result_stats['leaf_communities']} leaf communities")
            else:
                logging.error(f"Year {year} failed: {result_stats.get('error', 'Unknown error')}")
                failed_count += 1
        except Exception as e:
            logging.error(f"Exception processing year {year}: {str(e)}")
            failed_count += 1
    
    # 保存摘要
    base_output_path.mkdir(parents=True, exist_ok=True)
    summary_data = {
        'processing_completed': True,
        'method': 'adaptive_hierarchical_detection_4d',
        'total_years_attempted': year_range[1] - year_range[0] + 1,
        'successfully_processed': processed_count,
        'failed_processing': failed_count,
        'success_rate': processed_count / (processed_count + failed_count) if (processed_count + failed_count) > 0 else 0,
        'weight_threshold': weight_threshold,
        'detector_params': detector_params,
        'results_by_year': all_results
    }
    
    with open(base_output_path / "batch_processing_summary.json", 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    logging.info(f"\n{'='*80}\nBatch processing completed!\n"
                f"Success: {processed_count}/{summary_data['total_years_attempted']} ({summary_data['success_rate']:.1%})\n{'='*80}")
    
    return summary_data


def main():
    """主函数 - 自适应社区检测"""
    base_data_dir = "./graph_data_rolling_windows_updated"
    base_output_dir = "./workforce_community_results_adaptive_4d"
    base_prefix = "workforce_geo_community"
    weight_threshold = 2
    
    BATCH_MODE = True  # True: 批量处理, False: 单个年份
    
    detector_params = {
        'min_size': 10,
        'purity_multiplier': 5,
        'resolution': 1.0,
        'iterations': 300,
        'seed': 42,
        'weight_threshold': weight_threshold,
        'max_depth': 6
    }
    
    if BATCH_MODE:
        year_range = (2000, 2024)
        print("="*80)
        print("ADAPTIVE COMMUNITY DETECTION - BATCH MODE (4-Dimension Purity)")
        print(f"Years: {year_range[0]}-{year_range[1]}")
        print(f"Parameters: min_size={detector_params['min_size']}, "
              f"purity_multiplier={detector_params['purity_multiplier']}")
        print("="*80)
        
        summary_data = process_multiple_years_adaptive(base_data_dir, base_output_dir, year_range, 
                                                      base_prefix, weight_threshold, detector_params)
        print(f"\nCompleted: {summary_data['successfully_processed']} successful, "
              f"{summary_data['failed_processing']} failed ({summary_data['success_rate']:.1%})")
        return summary_data
    
    else:
        target_year = 2018
        data_dir = Path(base_data_dir) / f"graph_{target_year-1}_{target_year}"
        output_dir = Path(base_output_dir) / f"results_{target_year-1}_{target_year}"
        prefix = f"{base_prefix}_{target_year-1}_{target_year}"
        
        print("="*80)
        print(f"ADAPTIVE COMMUNITY DETECTION - SINGLE YEAR ({target_year})")
        print("="*80)
        
        result_stats = single_adaptive_detection(str(data_dir), str(output_dir), prefix, 
                                                weight_threshold, detector_params)
        
        if result_stats and 'error' not in result_stats:
            print(f"\nSuccess! Time: {result_stats['processing_time']:.2f}s")
            print(f"Nodes: {result_stats['total_nodes']:,}, Edges: {result_stats['total_edges']:,}")
            print(f"Max depth: {result_stats['max_depth_reached']}, Leaf communities: {result_stats['leaf_communities']}")
        else:
            print(f"\nFailed: {result_stats.get('error', 'Unknown error')}")
        
        return result_stats


if __name__ == "__main__":
    main()