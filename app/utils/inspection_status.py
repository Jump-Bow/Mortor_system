"""
巡檢結果狀態碼封裝 (inspection_status.py)

is_out_of_spec 欄位語意定義，統一管理魔術數字。
使用 IntEnum 繼承自 int，可直接與整數比較，無需 .value。
與 SQLAlchemy 查詢完全相容。

範例：
    InspectionResult.is_out_of_spec >= InspectionStatus.ABNORMAL
    InspectionResult.is_out_of_spec == InspectionStatus.SHUTDOWN
    InspectionResult.is_out_of_spec != InspectionStatus.CREATED
"""

from enum import IntEnum


class InspectionStatus(IntEnum):
    """巡檢結果狀態碼 (is_out_of_spec)"""
    CREATED  = 0  # 已建立，尚未填寫量測值（空白紀錄）
    NORMAL   = 1  # 正常（在規格範圍內）
    ABNORMAL = 2  # 異常（超出規格範圍）
    SHUTDOWN = 3  # 停機（嚴重異常，需立即處置）
