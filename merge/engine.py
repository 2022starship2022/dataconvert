#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据合并引擎
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any
import pandas as pd

from .config import MergeConfig, MergeResult
from .field_mapper import FieldMapper
from core.unified_format_processor import UnifiedFormatProcessor

logger = logging.getLogger(__name__)


class MergeEngine:
    """数据合并引擎"""

    def __init__(self, config=None):
        """
        初始化合并引擎

        Args:
            config: 配置对象
        """
        self.config = config
        self.format_processor = UnifiedFormatProcessor()
        self.field_mapper = FieldMapper()

    def merge_files(self, input_files: List[str], output_file: str,
                   merge_config: Optional[MergeConfig] = None) -> MergeResult:
        """
        合并多个文件

        Args:
            input_files: 输入文件列表
            output_file: 输出文件路径
            merge_config: 合并配置

        Returns:
            合并结果
        """
        start_time = time.time()

        try:
            # 使用提供的配置或默认配置
            config = merge_config or MergeConfig()
            config.sources = input_files[1:] if len(input_files) > 1 else []
            config.target = input_files[0] if input_files else ''
            config.output = output_file

            # 验证配置
            is_valid, error_msg = config.validate()
            if not is_valid:
                return MergeResult(
                    success=False,
                    output_path=output_file,
                    message=f"配置无效: {error_msg}"
                )

            # 执行合并
            if config.mode == 'append':
                result = self._merge_append(config)
            elif config.mode == 'join':
                result = self._merge_join(config)
            elif config.mode == 'update':
                result = self._merge_update(config)
            elif config.mode == 'cross':
                result = self._merge_cross(config)
            else:
                return MergeResult(
                    success=False,
                    output_path=output_file,
                    message=f"不支持的合并模式: {config.mode}"
                )

            # 计算耗时
            result.duration = time.time() - start_time

            logger.info(f"合并完成: {result.success}, 耗时: {result.duration:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"合并操作失败: {e}", exc_info=True)
            return MergeResult(
                success=False,
                output_path=output_file,
                message=f"合并失败: {str(e)}",
                duration=time.time() - start_time
            )

    def preview_merge(self, merge_config: MergeConfig, preview_rows: int = 50) -> pd.DataFrame:
        """
        预览合并结果

        Args:
            merge_config: 合并配置
            preview_rows: 预览行数

        Returns:
            预览数据
        """
        try:
            # 读取样本数据
            sample_data = {}

            # 读取目标文件
            if merge_config.target and os.path.exists(merge_config.target):
                target_data = self._read_file_sample(merge_config.target, preview_rows)
                sample_data['target'] = target_data

            # 读取源文件
            for source_file in merge_config.sources[:3]:  # 限制源文件数量
                if os.path.exists(source_file):
                    source_data = self._read_file_sample(source_file, preview_rows)
                    sample_data[source_file] = source_data

            # 执行样本合并
            if merge_config.mode == 'append':
                return self._preview_append(sample_data, preview_rows)
            elif merge_config.mode == 'join':
                return self._preview_join(sample_data, merge_config, preview_rows)
            elif merge_config.mode == 'update':
                return self._preview_update(sample_data, merge_config, preview_rows)
            elif merge_config.mode == 'cross':
                return self._preview_cross(sample_data, preview_rows)
            else:
                raise ValueError(f"不支持的合并模式: {merge_config.mode}")

        except Exception as e:
            logger.error(f"预览合并失败: {e}")
            return pd.DataFrame()

    def _merge_append(self, config: MergeConfig) -> MergeResult:
        """追加合并"""
        logger.info("开始追加合并")

        try:
            # 读取目标文件
            target_df = self._read_file(config.target)
            if target_df is None:
                return MergeResult(
                    success=False,
                    output_path=config.output,
                    message="无法读取目标文件"
                )

            all_data = [target_df]
            total_records = len(target_df)

            # 读取并追加源文件
            for source_file in config.sources:
                try:
                    source_df = self._read_file(source_file)
                    if source_df is not None:
                        # 字段映射
                        if config.field_mappings:
                            source_df = self._apply_field_mapping(source_df, config.field_mappings)

                        all_data.append(source_df)
                        total_records += len(source_df)
                        logger.info(f"追加文件: {source_file}, 记录数: {len(source_df)}")

                except Exception as e:
                    error_msg = f"读取源文件失败 {source_file}: {e}"
                    if config.tolerant:
                        logger.warning(error_msg)
                        continue
                    else:
                        return MergeResult(
                            success=False,
                            output_path=config.output,
                            message=error_msg
                        )

            # 合并所有数据
            if all_data:
                result_df = pd.concat(all_data, ignore_index=True, sort=False)
                
                # 处理去重
                if config.handle_duplicates:
                    # 如果指定了键字段，则基于这些字段去重
                    if config.key_fields:
                        # 检查键字段是否都存在
                        existing_keys = [key for key in config.key_fields if key in result_df.columns]
                        if existing_keys:
                            result_df = result_df.drop_duplicates(subset=existing_keys, keep='first')
                            logger.info(f"基于字段 {existing_keys} 去重，剩余记录数: {len(result_df)}")
                    else:
                        # 如果没有指定键字段，则基于所有列去重
                        result_df = result_df.drop_duplicates(keep='first')
                        logger.info(f"基于所有列去重，剩余记录数: {len(result_df)}")
            else:
                result_df = pd.DataFrame()

            # 写入结果
            success = self._write_file(result_df, config.output, config.output_format)

            return MergeResult(
                success=success,
                output_path=config.output,
                message=f"追加合并完成，总记录数: {len(result_df)}",
                total_records=total_records,
                processed_records=len(result_df)
            )

        except Exception as e:
            logger.error(f"追加合并失败: {e}")
            return MergeResult(
                success=False,
                output_path=config.output,
                message=f"追加合并失败: {str(e)}"
            )

    def _merge_join(self, config: MergeConfig) -> MergeResult:
        """关联合并"""
        logger.info("开始关联合并")

        try:
            # 读取目标文件
            target_df = self._read_file(config.target)
            if target_df is None:
                return MergeResult(
                    success=False,
                    output_path=config.output,
                    message="无法读取目标文件"
                )

            # 检查关键字段
            missing_keys = [key for key in config.key_fields if key not in target_df.columns]
            if missing_keys:
                return MergeResult(
                    success=False,
                    output_path=config.output,
                    message=f"目标文件缺少关键字段: {missing_keys}"
                )

            result_df = target_df.copy()

            # 逐个合并源文件
            for source_file in config.sources:
                try:
                    source_df = self._read_file(source_file)
                    if source_df is None:
                        continue

                    # 检查源文件关键字段
                    missing_keys = [key for key in config.key_fields if key not in source_df.columns]
                    if missing_keys:
                        error_msg = f"源文件缺少关键字段 {source_file}: {missing_keys}"
                        if config.tolerant:
                            logger.warning(error_msg)
                            continue
                        else:
                            return MergeResult(
                                success=False,
                                output_path=config.output,
                                message=error_msg
                            )

                    # 字段映射
                    if config.field_mappings:
                        source_df = self._apply_field_mapping(source_df, config.field_mappings)

                    # 执行连接
                    if config.ignore_case:
                        for key in config.key_fields:
                            if key in result_df.columns and key in source_df.columns:
                                result_df[key] = result_df[key].astype(str).str.lower()
                                source_df[key] = source_df[key].astype(str).str.lower()

                    result_df = pd.merge(
                        result_df,
                        source_df,
                        on=config.key_fields,
                        how='left',
                        suffixes=('', f'_{os.path.basename(source_file)}')
                    )

                    logger.info(f"合并文件: {source_file}")

                except Exception as e:
                    error_msg = f"合并源文件失败 {source_file}: {e}"
                    if config.tolerant:
                        logger.warning(error_msg)
                        continue
                    else:
                        return MergeResult(
                            success=False,
                            output_path=config.output,
                            message=error_msg
                        )

            # 写入结果
            success = self._write_file(result_df, config.output, config.output_format)

            return MergeResult(
                success=success,
                output_path=config.output,
                message=f"关联合并完成，记录数: {len(result_df)}",
                processed_records=len(result_df)
            )

        except Exception as e:
            logger.error(f"关联合并失败: {e}")
            return MergeResult(
                success=False,
                output_path=config.output,
                message=f"关联合并失败: {str(e)}"
            )

    def _merge_update(self, config: MergeConfig) -> MergeResult:
        """更新合并"""
        logger.info("开始更新合并")

        try:
            # 读取目标文件
            target_df = self._read_file(config.target)
            if target_df is None:
                return MergeResult(
                    success=False,
                    output_path=config.output,
                    message="无法读取目标文件"
                )

            result_df = target_df.copy()
            updated_count = 0

            # 逐个更新源文件
            for source_file in config.sources:
                try:
                    source_df = self._read_file(source_file)
                    if source_df is None:
                        continue

                    # 字段映射
                    if config.field_mappings:
                        source_df = self._apply_field_mapping(source_df, config.field_mappings)

                    # 创建更新映射
                    for _, source_row in source_df.iterrows():
                        # 构建查询条件
                        conditions = []
                        for key in config.key_fields:
                            if key in source_row and key in result_df.columns:
                                value = source_row[key]
                                if config.ignore_case and isinstance(value, str):
                                    value = value.lower()
                                    conditions.append(f"result_df['{key}'].astype(str).str.lower() == '{value}'")
                                else:
                                    conditions.append(f"result_df['{key}'] == {repr(value)}")

                        if conditions:
                            # 查找匹配的行
                            mask = eval(' & '.join(conditions))
                            matching_indices = result_df[mask].index

                            # 更新匹配的行
                            for idx in matching_indices:
                                for col in source_df.index:
                                    if col != 'index' and col in result_df.columns:
                                        result_df.at[idx, col] = source_row[col]
                                        updated_count += 1

                    logger.info(f"更新文件: {source_file}")

                except Exception as e:
                    error_msg = f"更新源文件失败 {source_file}: {e}"
                    if config.tolerant:
                        logger.warning(error_msg)
                        continue
                    else:
                        return MergeResult(
                            success=False,
                            output_path=config.output,
                            message=error_msg
                        )

            # 写入结果
            success = self._write_file(result_df, config.output, config.output_format)

            return MergeResult(
                success=success,
                output_path=config.output,
                message=f"更新合并完成，更新记录数: {updated_count}",
                processed_records=len(result_df)
            )

        except Exception as e:
            logger.error(f"更新合并失败: {e}")
            return MergeResult(
                success=False,
                output_path=config.output,
                message=f"更新合并失败: {str(e)}"
            )

    def _merge_cross(self, config: MergeConfig) -> MergeResult:
        """横向合并"""
        logger.info("开始横向合并")

        try:
            # 读取所有文件
            all_data = []
            total_records = None

            files_to_merge = [config.target] + config.sources if config.target else config.sources

            for file_path in files_to_merge:
                try:
                    df = self._read_file(file_path)
                    if df is None:
                        continue

                    # 检查记录数一致性
                    if total_records is None:
                        total_records = len(df)
                    elif len(df) != total_records:
                        error_msg = f"文件记录数不一致: {file_path} ({len(df)} != {total_records})"
                        if config.tolerant:
                            logger.warning(error_msg)
                            # 填充缺失值
                            if len(df) < total_records:
                                additional_rows = pd.DataFrame(index=range(total_records - len(df)))
                                df = pd.concat([df, additional_rows], ignore_index=True)
                            else:
                                df = df.head(total_records)
                        else:
                            return MergeResult(
                                success=False,
                                output_path=config.output,
                                message=error_msg
                            )

                    # 字段映射
                    if config.field_mappings:
                        df = self._apply_field_mapping(df, config.field_mappings)

                    all_data.append(df)
                    logger.info(f"处理文件: {file_path}")

                except Exception as e:
                    error_msg = f"读取文件失败 {file_path}: {e}"
                    if config.tolerant:
                        logger.warning(error_msg)
                        continue
                    else:
                        return MergeResult(
                            success=False,
                            output_path=config.output,
                            message=error_msg
                        )

            if not all_data:
                return MergeResult(
                    success=False,
                    output_path=config.output,
                    message="没有可合并的数据"
                )

            # 横向合并
            result_df = pd.concat(all_data, axis=1)

            # 写入结果
            success = self._write_file(result_df, config.output, config.output_format)

            return MergeResult(
                success=success,
                output_path=config.output,
                message=f"横向合并完成，记录数: {len(result_df)}, 字段数: {len(result_df.columns)}",
                processed_records=len(result_df)
            )

        except Exception as e:
            logger.error(f"横向合并失败: {e}")
            return MergeResult(
                success=False,
                output_path=config.output,
                message=f"横向合并失败: {str(e)}"
            )

    def _read_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """读取文件"""
        try:
            # 直接使用UnifiedFormatProcessor读取文件
            result = self.format_processor.read(file_path)
            return result

        except Exception as e:
            logger.error(f"读取文件异常 {file_path}: {e}")
            return None

    def _read_file_sample(self, file_path: str, sample_rows: int) -> Optional[pd.DataFrame]:
        """读取文件样本"""
        try:
            df = self._read_file(file_path)
            if df is not None and len(df) > sample_rows:
                return df.head(sample_rows)
            return df

        except Exception as e:
            logger.error(f"读取文件样本失败 {file_path}: {e}")
            return None

    def _write_file(self, data: pd.DataFrame, file_path: str,
                   output_format: Optional[str] = None) -> bool:
        """写入文件"""
        try:
            if data.empty:
                logger.warning("数据为空，跳过写入")
                return True

            # 确保输出目录存在
            output_dir = os.path.dirname(file_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 直接使用UnifiedFormatProcessor写入文件
            result = self.format_processor.write(data, file_path)
            return result

        except Exception as e:
            logger.error(f"写入文件失败 {file_path}: {e}")
            return False

    def _apply_field_mapping(self, data: pd.DataFrame,
                           field_mappings: Dict[str, str]) -> pd.DataFrame:
        """应用字段映射"""
        try:
            mapped_data = data.copy()

            for target_field, source_field in field_mappings.items():
                if source_field in mapped_data.columns:
                    mapped_data = mapped_data.rename(columns={source_field: target_field})

            return mapped_data

        except Exception as e:
            logger.error(f"应用字段映射失败: {e}")
            return data

    def _preview_append(self, sample_data: Dict[str, pd.DataFrame],
                       preview_rows: int) -> pd.DataFrame:
        """预览追加合并"""
        all_data = []
        for name, df in sample_data.items():
            if not df.empty:
                all_data.append(df.head(preview_rows))

        if all_data:
            return pd.concat(all_data, ignore_index=True, sort=False).head(preview_rows)
        return pd.DataFrame()

    def _preview_join(self, sample_data: Dict[str, pd.DataFrame],
                     config: MergeConfig, preview_rows: int) -> pd.DataFrame:
        """预览关联合并"""
        if 'target' not in sample_data:
            return pd.DataFrame()

        result_df = sample_data['target'].copy()

        for name, df in sample_data.items():
            if name == 'target' or df.empty:
                continue

            # 简化的连接预览
            try:
                common_cols = list(set(result_df.columns) & set(df.columns))
                if common_cols and config.key_fields:
                    key_cols = [col for col in config.key_fields if col in common_cols]
                    if key_cols:
                        result_df = pd.merge(
                            result_df.head(preview_rows),
                            df.head(preview_rows),
                            on=key_cols,
                            how='left',
                            suffixes=('', f'_{name}')
                        )
            except Exception as e:
                logger.warning(f"预览连接失败: {e}")

        return result_df.head(preview_rows)

    def _preview_update(self, sample_data: Dict[str, pd.DataFrame],
                       config: MergeConfig, preview_rows: int) -> pd.DataFrame:
        """预览更新合并"""
        if 'target' not in sample_data:
            return pd.DataFrame()

        # 简化的更新预览 - 返回目标数据
        return sample_data['target'].head(preview_rows)

    def _preview_cross(self, sample_data: Dict[str, pd.DataFrame],
                      preview_rows: int) -> pd.DataFrame:
        """预览横向合并"""
        all_data = []
        for name, df in sample_data.items():
            if not df.empty:
                all_data.append(df.head(preview_rows))

        if all_data:
            # 取最小的长度
            min_length = min(len(df) for df in all_data)
            truncated_data = [df.head(min_length) for df in all_data]
            return pd.concat(truncated_data, axis=1).head(preview_rows)
        return pd.DataFrame()