# 設計仕様：最低保有日数・再エントリー制限 (#174) および 決算・重要イベント回避 (#171)

Date: 2026-04-22  
Issues: #174, #171  
Approach: アプローチ A（フィルタを `signal_generator.py` に集約）

---

## 1. 概要

### #174 最低保有日数・再エントリー制限

- 新規 BUY 後 **5営業日** は、ストップロス以外の理由で SELL しない
- SELL 後 **5営業日** は、同一銘柄の再 BUY を禁止する
- 例外（制限を解除する条件）:
  - ストップロス到達（常に適用済み）
  - Bear レジーム移行（#174-B で追加）
  - 決算回避（#171 完了後に #174-B で追加）
- バックテスト（インメモリ DuckDB）にも同条件を強制適用する

### #171 決算・重要イベント回避

- 決算発表予定銘柄の翌営業日は新規 BUY を禁止する
- 既存保有は決算前に SELL（reason=`earnings_avoidance`）
- FOMC・日銀・CPI 等の主要イベント前営業日は新規 BUY サイズを 50% に縮小する
- Bear レジームと重なる場合は新規建てを全面停止（既存ロジックで対応済み）
- SELL はイベント回避対象外（執行優先）

### 実装順序と PR 分割

| PR | 対象 Issue | 内容 |
|----|-----------|------|
| PR-A | #174 Part 1 | `position_entries` テーブル・最低保有日数・再エントリー制限（例外なし） |
| PR-B | #171 | 決算カレンダー・イベントカレンダー・BUY抑制・SELL強制・サイズ縮小 |
| PR-C | #174 Part 2 | Bear移行・決算回避の保有日数スキップ例外を追加 |

---

## 2. スキーマ変更

### 2.1 新テーブル `position_entries`

```sql
CREATE TABLE IF NOT EXISTS position_entries (
    code        VARCHAR  NOT NULL,
    entry_date  DATE     NOT NULL,
    sell_date   DATE,
    PRIMARY KEY (code, entry_date)
)
```

- BUY 約定時に `(code, entry_date)` を INSERT（sell_date は NULL）
- SELL 約定時に最新の NULL レコードの `sell_date` を UPDATE
- 同一銘柄の再BUY時は新しい `(code, entry_date)` を INSERT

### 2.2 新テーブル `earnings_calendar`

```sql
CREATE TABLE IF NOT EXISTS earnings_calendar (
    code              VARCHAR   NOT NULL,
    announcement_date DATE      NOT NULL,
    fetched_at        TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (code, announcement_date)
)
```

- J-Quants `/equities/earnings-calendar` から取得・保存
- 夜間バッチ（`pipeline.py`）で差分更新（冪等）

### 2.3 `signals` テーブルへの `size_multiplier` カラム追加

```sql
ALTER TABLE signals ADD COLUMN IF NOT EXISTS size_multiplier DOUBLE DEFAULT 1.0
```

- 主要イベント前営業日の BUY シグナルに `size_multiplier=0.5` を付与
- `execution_engine.py` / `simulator.py` が発注サイズ計算時に参照する

---

## 3. #174-A 実装ロジック

### 3.1 最低保有日数チェック（SELL 側）

`signal_generator._generate_sell_signals()` 内に追加。

```
SELL 判定フロー（変更後）:
  1. stop_loss 到達 → 即 SELL（保有日数チェックをスキップ）
  2. position_entries に entry_date がない → チェックをスキップ（安全側: SELL 許可）
  3. entry_date から target_date の営業日数 < 5 → SELL 抑制（スキップ）
  4. それ以外（score_drop 等）→ 通常通り SELL
```

ヘルパー関数：

```python
def _held_days(conn, code, target_date) -> int | None:
    """position_entries から最新 entry_date を取得し営業日数を返す。レコードなしは None。"""
```

営業日数計算は `calendar_management.get_trading_days(entry_date, target_date)` を使用。

### 3.2 再エントリー制限チェック（BUY 側）

`generate_signals()` の BUY ループ内に追加。既存フィルタと同構造。

```python
def _is_reentry_blocked(conn, code, target_date, cooldown_days=5) -> bool:
    """最新の sell_date から target_date までの営業日数 < cooldown_days なら True。
    sell_date が NULL または レコードなしは False。"""
```

### 3.3 `position_entries` 書き込み箇所

| タイミング | 処理 | 担当モジュール |
|-----------|------|--------------|
| BUY 約定時 | `INSERT INTO position_entries (code, entry_date)` | `execution_engine.py` / `simulator.py` |
| SELL 約定時 | `UPDATE position_entries SET sell_date = ? WHERE code = ? AND sell_date IS NULL` | 同上 |

バックテストのインメモリ DB にも `position_entries` を含め、本番と同じロジックを適用する。

---

## 4. #171 実装ロジック

### 4.1 イベントカレンダーファイル

`config/event_calendar.md` に年次で管理。AI アシストで定期更新。

```markdown
## 2026年

### FOMC
- 2026-01-29
- 2026-03-19
...

### 日銀決定会合
- 2026-01-24
...

### 米CPI
- 2026-01-15
...
```

`src/kabusys/data/event_calendar.py`（新規）でパースし `{date: event_name}` の dict を返す。

### 4.2 決算回避（BUY 抑制）

`generate_signals()` の BUY ループ内に追加。

```python
def _has_upcoming_earnings(conn, code, target_date) -> bool:
    """翌営業日が earnings_calendar に登録されている銘柄なら True。"""
```

`earnings_calendar` テーブルに `(code, next_trading_day(target_date))` の組み合わせが存在する場合に BUY を抑制。

### 4.3 決算回避（SELL 強制）

`_generate_sell_signals()` 内に追加。

```
決算 SELL 判定:
  - 保有銘柄の翌営業日が announcement_date → reason="earnings_avoidance" で SELL
  - 最低保有日数チェックは earnings_avoidance ではスキップ（#174-B で実装）
```

### 4.4 主要イベント対応（BUY サイズ縮小）

`generate_signals()` 内に追加。

```python
def _get_event_size_multiplier(event_dates, target_date, conn) -> float:
    """翌営業日が event_dates に含まれる場合 0.5、それ以外は 1.0 を返す。"""
```

BUY シグナルを `signals` テーブルへ書き込む際に `size_multiplier` を付与。

### 4.5 J-Quants 決算カレンダー取得

`jquants_client.py` に追加：

```python
def fetch_earnings_calendar(id_token=None, date_from=None, date_to=None) -> list[dict]:
    """GET /equities/earnings-calendar を取得。"""

def save_earnings_calendar(conn, records) -> int:
    """earnings_calendar テーブルへ冪等保存（INSERT OR REPLACE）。"""
```

`pipeline.py` の夜間バッチに組み込み（カレンダー先読み: 30日程度）。

---

## 5. #174-B 実装ロジック（#171 完了後）

`_generate_sell_signals()` に例外条件を追加：

```
保有日数スキップ条件（SELL 許可）:
  - stop_loss（既存）
  - reason="earnings_avoidance"（#171 追加後）
  - Bear レジームへの移行（Bear フラグを引数で受け取る）
```

---

## 6. テスト方針

- `position_entries` の INSERT/UPDATE：`execution_engine` / `simulator` のユニットテスト
- 最低保有日数チェック：`signal_generator` のユニットテスト（`target_date` をずらして検証）
- 再エントリー制限：同上
- 決算回避：`signal_generator` のユニットテスト（`earnings_calendar` にデータを挿入して検証）
- イベントカレンダーパーサー：`event_calendar.py` のユニットテスト
- サイズ縮小：`signals` テーブルの `size_multiplier` 値を検証

---

## 7. 変更ファイル一覧

### PR-A (#174 Part 1)

- `src/kabusys/data/schema.py`
- `src/kabusys/strategy/signal_generator.py`
- `src/kabusys/execution/execution_engine.py`
- `src/kabusys/backtest/simulator.py`
- `tests/test_signal_generator.py`
- `tests/test_execution_engine.py`（または既存テストに追加）
- `tests/test_simulator.py`（または既存テストに追加）

### PR-B (#171)

- `src/kabusys/data/schema.py`
- `src/kabusys/data/jquants_client.py`
- `src/kabusys/data/event_calendar.py`（新規）
- `src/kabusys/data/pipeline.py`
- `src/kabusys/strategy/signal_generator.py`
- `config/event_calendar.md`（新規）
- `tests/test_signal_generator.py`
- `tests/test_event_calendar.py`（新規）
- `tests/test_jquants_client.py`（または既存テストに追加）

### PR-C (#174 Part 2)

- `src/kabusys/strategy/signal_generator.py`
- `tests/test_signal_generator.py`
