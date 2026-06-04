# import_template.py — Full Source

**Path**: `/root/projects/drug-distribution-system/gaofang-v2/import_template.py`
**Last updated**: 2026-05-04 (session: gaofang-import-revisions-v3)

## Key Design Decisions

- **Column map** matches the 广积德系统「代煎导出」format (not the built-in system import template)
- **Duplicate handling**: overwrite + notify (not skip)
- **Sort order**: `id DESC` — user explicitly rejected changing to `updated_at DESC`. **Do NOT change this.**
- **Fixed defaults**: status='欠药', is_prescription_sent='已传方', assistant='-' when empty
- **Result message**: returns detailed count string (e.g. "新增 5 条, 覆盖更新 3 条") instead of generic "数据导入成功"

## Full Code

```python
# -*- coding: utf-8 -*-
"""
膏方Excel导入模板模块
按 prescriptions.py 中 import_data() 的约定提供：
  - excel_file: 模块级变量，Excel文件路径
  - main(): 主入口，解析Excel并写入数据库

调用方式：
  import import_template
  import_template.excel_file = '/path/to/file.xlsx'
  import_template.main()

注意事项：
  - 重复的代煎号(prescription_id)覆盖更新（保留复诊和审计字段）
  - 自动计算"通知至取药天数"
  - 日期支持多种格式：yyyy-mm-dd, yyyy/mm/dd, yyyy.mm.dd, 含时间的完整格式
"""

import logging
from datetime import datetime, date
from database import db
from models.prescription import PrescriptionRecord

logger = logging.getLogger(__name__)

# 模块级变量：当前要处理的Excel文件路径
excel_file = None


# ============================================================
# 列名 → 模型字段映射
# ============================================================
# 注意：此映射匹配「代煎导出」格式（从广积德系统导出），
#      不是系统内置的导入模板格式。
COLUMN_MAP = {
    '处方日期':   ('date', True),
    '处方编号':   ('prescription_id', False),
    '患者姓名':   ('patient_name', False),
    '患者性别':   ('gender', False),
    '患者年龄':   ('age', False),
    '处方模板':   ('prescription_type', False),
    '代煎料型':   ('decoction_material_type', False),
    '代煎方型':   ('decoction_prescription_type', False),
    '料数':       ('quantity', False),
    '医生姓名':   ('doctor', False),
    '医助':       ('assistant', False),
    '支付状态':   ('payment_status', False),
    '收款状态':   ('collection_status', False),
    '代煎克重':   ('decoction_weight', False),
    '饮片费用':   ('herbal_medicine_cost', False),
    '加工费用':   ('processing_cost', False),
    '患者手机号': ('patient_phone', False),
    '快递地址':   ('express_address', False),
}

# 必填字段（导入时不能为空）
REQUIRED_FIELDS = ['处方编号', '患者姓名', '患者性别', '患者年龄', '医生姓名']

# 默认值映射（空值时填充）
DEFAULT_VALUES = {
    '料数': 1,
    '医助': '-',          # 数据库 NOT NULL，空时填占位符
    '是否传方': '已传方',   # 模型字段名，不在 COLUMN_MAP 中，在构建记录时单独处理
}


# ============================================================
# 日期解析
# ============================================================

def _parse_date(value):
    """将各种格式的日期字符串转为 date 对象"""
    if value is None or str(value).strip() == '':
        return None

    value = str(value).strip()

    if value.isdigit() and len(value) == 8:
        try:
            return datetime.strptime(value, '%Y%m%d').date()
        except ValueError:
            pass

    if isinstance(value, (datetime, date)):
        return value if isinstance(value, date) else value.date()

    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    for sep in ['-', '/', '.', '年', '月', '日']:
        value = value.replace(sep, '-')

    parts = [p for p in value.split('-') if p]
    if len(parts) >= 3:
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            if year < 100:
                year += 2000
            return date(year, month, day)
        except (ValueError, TypeError):
            pass

    logger.warning(f"无法解析日期: {value}")
    return None


def _parse_age(value):
    """解析年龄，去除"岁"后缀"""
    if value is None or str(value).strip() == '':
        return None
    s = str(value).strip().replace('岁', '').replace(' ', '')
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _calc_days(start_date, end_date):
    """计算两个日期之间的天数差"""
    if start_date and end_date:
        delta = end_date - start_date
        return delta.days
    return None


def _parse_excel(filepath):
    """
    解析Excel文件，返回行数据列表
    每行为 { '列名': 值 } 字典
    不依赖固定的列顺序，通过表头名称自动匹配
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active

    headers = []
    for col in range(1, ws.max_column + 1):
        header_value = ws.cell(row=1, column=col).value
        if header_value is not None:
            headers.append(str(header_value).strip())
        else:
            headers.append('')

    actual_headers = set(headers)
    mapped_headers = set(COLUMN_MAP.keys())
    found_headers = mapped_headers & actual_headers
    missing_required = set(REQUIRED_FIELDS) - actual_headers

    logger.info(f"Excel表头数: {len(headers)}, 匹配到 {len(found_headers)} 个映射列")

    if missing_required:
        raise ValueError(
            f"Excel缺少必填列: {', '.join(sorted(missing_required))}"
        )

    col_index = {h: idx for idx, h in enumerate(headers) if h in mapped_headers}

    rows = []
    for row_idx in range(2, ws.max_row + 1):
        row_data = {}
        is_empty = True

        for header_name, (field, is_date) in COLUMN_MAP.items():
            col_idx = col_index.get(header_name)
            if col_idx is not None:
                value = ws.cell(row=row_idx, column=col_idx + 1).value
                row_data[header_name] = value
                if value is not None and str(value).strip() != '':
                    is_empty = False

        if not is_empty:
            rows.append(row_data)

    wb.close()
    return rows


def _validate_row(row, row_num):
    """验证一行数据，返回 (是否有效, 错误消息)"""
    for field_name in REQUIRED_FIELDS:
        value = row.get(field_name)
        if value is None or str(value).strip() == '':
            return False, f"第{row_num}行「{field_name}」为空"
    return True, None


# ============================================================
# 数据导入（核心入口）
# ============================================================

def main():
    """
    主入口：解析Excel并写入数据库
    在 prescriptions.py 的 import_data() 中被调用
    """
    global excel_file

    if not excel_file:
        raise ValueError("excel_file 未设置")

    logger.info(f"开始导入Excel: {excel_file}")

    raw_rows = _parse_excel(excel_file)
    total_rows = len(raw_rows)

    if total_rows == 0:
        raise ValueError("Excel文件中没有数据行")

    logger.info(f"读取到 {total_rows} 行数据")

    session = db.session
    existing_ids = set()
    try:
        results = session.query(PrescriptionRecord.prescription_id).all()
        existing_ids = {r[0] for r in results if r[0]}
    except Exception as e:
        logger.warning(f"查询已有代煎号失败: {e}")

    success_count = 0
    update_count = 0
    error_rows = []

    for idx, row in enumerate(raw_rows):
        row_num = idx + 2

        is_valid, err_msg = _validate_row(row, row_num)
        if not is_valid:
            error_rows.append(f"{err_msg}")
            continue

        prescription_id = str(row.get('处方编号', '')).strip()

        try:
            # ----- 构建模型字段字典 (必须在覆盖判断之前) -----
            record_data = {}

            for header_name, (field_name, is_date) in COLUMN_MAP.items():
                raw_value = row.get(header_name)

                if raw_value is None or str(raw_value).strip() == '':
                    if header_name in DEFAULT_VALUES:
                        record_data[field_name] = DEFAULT_VALUES[header_name]
                    else:
                        record_data[field_name] = None
                    continue

                if is_date:
                    record_data[field_name] = _parse_date(raw_value)
                else:
                    if field_name == 'age':
                        record_data[field_name] = _parse_age(raw_value)
                    elif field_name == 'quantity':
                        try:
                            record_data[field_name] = int(float(str(raw_value)))
                        except (ValueError, TypeError):
                            record_data[field_name] = DEFAULT_VALUES.get('料数', 1)
                    elif field_name in ('herbal_medicine_cost', 'processing_cost', 'decoction_weight'):
                        record_data[field_name] = str(raw_value)
                    else:
                        record_data[field_name] = str(raw_value).strip()

            # 固定值字段
            record_data['status'] = '欠药'
            record_data['is_prescription_sent'] = '已传方'

            # 自动计算天数
            shipping = record_data.get('shipping_time')
            notification = record_data.get('notification_pickup_date')
            pickup = record_data.get('pickup_date')

            if notification and pickup:
                record_data['days_from_notification_to_pickup'] = _calc_days(
                    notification, pickup
                )

            # ----- 去重检查 → 覆盖更新 or 新增 -----
            if prescription_id in existing_ids:
                existing = session.query(PrescriptionRecord).filter(
                    PrescriptionRecord.prescription_id == prescription_id
                ).first()
                if existing:
                    preserve_fields = [
                        'id', 'created_at', 'updated_at',
                        'follow_up_status', 'follow_up_1_status', 'follow_up_1_date',
                        'follow_up_2_status', 'follow_up_2_date',
                        'follow_up_3_status', 'follow_up_3_date',
                    ]
                    update_fields = {k: v for k, v in record_data.items()
                                     if k not in preserve_fields}
                    for key, val in update_fields.items():
                        setattr(existing, key, val)
                    existing.status = '欠药'
                    update_count += 1
                    logger.debug(f"覆盖更新代煎号: {prescription_id} (第{row_num}行)")
            else:
                record = PrescriptionRecord(**record_data)
                session.add(record)
                session.flush()
                existing_ids.add(prescription_id)
                success_count += 1

        except Exception as e:
            error_rows.append(f"第{row_num}行(编号:{prescription_id})导入失败: {str(e)}")
            logger.error(f"导入第{row_num}行失败: {e}")

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"批量提交失败: {e}")
        raise

    parts = [f"导入完成: 新增 {success_count} 条"]
    if update_count > 0:
        parts.append(f", 覆盖更新 {update_count} 条")
    if error_rows:
        limited_errors = error_rows[:5]
        parts.append(f", 失败 {len(error_rows)} 条")
        parts.append("\n详情:\n" + "\n".join(limited_errors))
        if len(error_rows) > 5:
            parts.append(f"\n...(还有{len(error_rows) - 5}条错误)")

    result_msg = "".join(parts)
    logger.info(result_msg)

    if error_rows:
        raise ValueError(result_msg)

    return result_msg
```
