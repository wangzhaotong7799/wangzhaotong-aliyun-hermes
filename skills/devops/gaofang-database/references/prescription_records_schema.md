# prescription_records 完整表结构

```
Table "public.prescription_records"
               Column               |            Type             | Nullable 
------------------------------------+-----------------------------+----------
 id                                 | integer                     | not null 
 date                               | date                        | not null    -- 处方日期
 prescription_id                    | character varying(50)       | not null    -- 处方编号(代煎号)
 patient_name                       | character varying(50)       | not null    -- 患者姓名
 gender                             | character varying(10)       | not null    -- 患者性别
 age                                | integer                     | not null    -- 患者年龄
 prescription_type                  | character varying(100)      |             -- 处方模板
 quantity                           | integer                     |             -- 料数(⚠️ 这是用户要的"料数")
 doctor                             | character varying(50)       | not null    -- 医生姓名
 assistant                          | character varying(50)       | not null    -- 医助
 notification_pickup_date           | date                        |             -- 通知取药日期
 status                             | character varying(20)       |             -- 状态
 is_prescription_sent               | character varying(10)       |             -- 是否传方
 is_mailed                          | character varying(10)       |             -- 是否邮寄
 shipping_time                      | date                        |             -- 发货时间
 days_from_prescription_to_shipping | integer                     |             -- 传方至发货天数
 pickup_date                        | date                        |             -- 取药日期
 days_from_notification_to_pickup   | integer                     |             -- 通知至取药天数
 decoction_material_type            | character varying(50)       |             -- 代煎料型
 decoction_prescription_type        | character varying(50)       |             -- 代煎方型
 decoction_weight                   | character varying(10)       |             -- 代煎克重(⚠️ 不是料数,这是重量)
 herbal_medicine_cost               | character varying(10)       |             -- 饮片费用
 processing_cost                    | character varying(10)       |             -- 加工费用
 payment_status                     | character varying(20)       |             -- 支付状态
 collection_status                  | character varying(20)       |             -- 收款状态
 patient_phone                      | character varying(20)       |             -- 患者手机号
 express_address                    | character varying(500)      |             -- 快递地址
 follow_up_status                   | character varying(20)       |             -- 回访总状态
 follow_up_1_status                 | character varying(20)       |             -- 第一次回访状态
 follow_up_1_date                   | date                        |             -- 第一次回访日期
 follow_up_2_status                 | character varying(20)       |             -- 第二次回访状态
 follow_up_2_date                   | date                        |             -- 第二次回访日期
 follow_up_3_status                 | character varying(20)       |             -- 第三次回访状态
 follow_up_3_date                   | date                        |             -- 第三次回访日期
 created_at                         | timestamp without time zone |             -- 记录创建时间(⚠️ 用户要的"导入时间")
 updated_at                         | timestamp without time zone |             -- 记录更新时间

Indexes:
    "prescription_records_pkey" PRIMARY KEY, btree (id)
    "ix_prescription_records_prescription_id" UNIQUE, btree (prescription_id)
    B-tree indexes on: date, patient_name, doctor, assistant, status
```

## status_change_logs 表

```
Table "public.status_change_logs"
     Column      |            Type             | Nullable 
-----------------+-----------------------------+----------
 id              | integer                     | not null 
 patient_name    | character varying(50)       | not null 
 prescription_id | character varying(50)       | not null 
 old_status      | character varying(20)       |  
 new_status      | character varying(20)       | not null 
 change_reason   | character varying(255)      |  
 operator        | character varying(50)       | not null 
 changed_at      | timestamp without time zone | not null 
```

## Other tables

- `users` — 系统用户
- `roles`, `permissions`, `role_permissions`, `user_roles` — 权限管理
