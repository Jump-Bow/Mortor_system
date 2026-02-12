# Schema Mapping Guide

This document maps the **Current Codebase Schema** to the **New Target Schema** defined in `DB_SCHEMA.txt`.

> [!IMPORTANT]
> The new schema introduces `snake_case` with underscores for many fields that were previously lowercase or camelCase. This is a BREAKING CHANGE.

## 1. Table Renaming

| Current Model | Current Table | New Table (Target) | Action |
| :--- | :--- | :--- | :--- |
| `SystemLog` | `system_log` | `sys_log` | **RENAME** |
| `UserActionLog` | `user_action_log` | `user_log` | **RENAME** |

## 2. Column Renaming

### `t_job` (Inspection Task)
| Current Field | New Field | Note |
| :--- | :--- | :--- |
| `actdesc` | `act_desc` | |
| `actkey` | `act_key` | |
| `actmemid` | `act_mem_id` | FK to `hr_account` |
| `actmemname` | `act_mem` | |
| `group_level` | `group` | **Keyword Warning** (group is SQL reserved) |

### `equit_check_item` (Check Items)
| Current Field | New Field | Note |
| :--- | :--- | :--- |
| `itemid` | `item_id` | PK |
| `sortorder` | `sort_order` | |
| `itemname` | `item_name` | |
| `itemdesc` | `item_desc` | |
| `statustype` | `status_type` | |
| `maxv` | `max_v` | |
| `minv` | `min_v` | |
| `group_level` | `group` | **Keyword Warning** |

### `inspection_result` (Results)
| Current Field | New Field | Note |
| :--- | :--- | :--- |
| `itemid` | `item_id` | FK |
| `measuredvalue` | `measured_value` | |
| `actmemid` | `act_mem_id` | |
| `acttime` | `act_time` | |
| `resultphoto` | `result_photo` | |
| `isoutofspec` | `is_out_of_spec` | |

### `AbnormalCases`
| Current Field | New Field | Note |
| :--- | :--- | :--- |
| `itemid` | `item_id` | FK |
| `measuredvalue` | `measured_value` | |
| `isprocessed` | `is_processed` | |
| `abnmsg` | `abn_msg` | |
| `abnsolution` | `abn_solution` | |
| `processedmemid` | `processed_memid` | |
| `processedtime` | `processed_time` | |

### `sys_log` (ex-SystemLog)
| Current Field | New Field | Note |
| :--- | :--- | :--- |
| `logid` | `log_id` | |

### `user_log` (ex-UserActionLog)
| Current Field | New Field | Note |
| :--- | :--- | :--- |
| `userid` | `user_id` | |

## 3. Unchanged Tables
- `t_organization` (unitid, parentunitid, unitname, unittype) - *Wait, check DB_SCHEMA.txt* -> Matches.
- `t_equipment` (id, name, assetid, unitid) - Matches.
- `hr_organization` (id, parentid, name) - Matches.
- `hr_account` (id, name, organizationid, email, password) - Matches.

## 4. Derived Changes
- API Response formats MUST be updated to return new field names (e.g., `item_id` instead of `itemid`).
- Frontend Templates MUST be updated to display new field names.
