# 手動ポジションの自動売買ロジック組み込み（助言モード）設計

- Issue: #410 手動注文メイン運用と助言モードの整備
- 関連: `docs/superpowers/specs/2026-09-17-manual-order-main-operation-design.md`
- ブランチ: `feature/manual-trade-advisory-410`

## 1. 目的

手動で約定した保有（`manual_trades`）を、自動売買と同じロジックの判断対象に含める。

- 手動保有にも自動売買と同じ SELL 判定（損切り・トレーリング等）を適用し、売却候補として提示する。
- 手動保有中の銘柄は、目標株数に対する不足分を「買い増し」BUY 候補として提示する。
- 手動保有を反映した総資産・利用可能現金で BUY 株数を計算する。
- システムは発注しない。候補の提示と記録のみを行う。

## 2. 前提（現状の確認結果）

- SELL 判定は `strategy/signal_generator.py::_generate_sell_signals` が `positions` テーブルと `position_entries`（保有開始日・ピーク価格算出用）を読んで行う。手動約定はこれらに入らないため、現状は手動保有に SELL 判定がかからない。
- SELL シグナルは `signals` テーブルと夜 LINE 通知に出るのみで、`signal_queue` に投入する経路は存在しない（`signal_queue` への INSERT は `scripts/run_portfolio_construction.py` の BUY のみ）。
- BUY 株数は `portfolio/position_sizing.py::calc_position_sizes` が `current_positions` を考慮して算出する（保有分を差し引いた株数）。

## 3. 有効化

`config.py` の `Settings` に以下を追加する。

| 環境変数 | 型 | 既定 | 用途 |
| -------- | -- | ---- | ---- |
| `MANUAL_TRADING_ENABLED` | bool | `false` | 手動保有を判定に含めるか |
| `MANUAL_TRADING_INITIAL_CASH` | float | `PORTFOLIO_VALUE` と同値 | 手動運用の元手 |

手動保有の取り込みは **呼び出し側が明示的に渡した場合のみ** 行う。`generate_signals` 等のデフォルトは「手動保有なし」とし、バックテスト（`backtest/engine.py`）からは一切渡さない。これにより、本番 DB をコピーしてバックテストした場合でも実取引データが混入せず、Look-ahead Bias 制約を守る。

## 4. 保有ポジションの統一表現

`src/kabusys/strategy/holdings.py`（新規）に定義する。

```python
@dataclass(frozen=True)
class HeldPosition:
    code: str
    qty: int
    avg_price: float
    first_entry_date: date | None   # 現保有の最古エントリー日（ピーク価格の起点）
    latest_entry_date: date | None  # 現保有の最新エントリー日（保有日数の起点）
    source: str                     # "auto" | "manual" | "mixed"
```

### 4.1 自動売買分

`load_auto_positions(conn, target_date, sqlite_conn)`：既存 `_generate_sell_signals` 冒頭のクエリ（`positions` の最新行 × `position_size > 0`）と、既存 `_peak_close` / `_held_days` と同じ `position_entries` 参照で entry 日を埋める。entry が無い場合は `None`（既存と同じく該当チェックをスキップ）。

### 4.2 手動分

`load_manual_positions(conn, target_date)`：`manual_trades` の `trade_date <= target_date` を約定日順に畳み込み、`calculate_manual_positions` と同じ平均単価・数量規則で保有を算出する。

- `first_entry_date`: 現保有が始まった BUY の約定日。数量が 0 になった後に再度 BUY した場合はその日から数え直す。
- `latest_entry_date`: 現保有中の最後の BUY 約定日。
- `calculate_manual_positions` と保有開始日の計算を共有するため、`operations/manual_trades.py` 側の畳み込み処理に entry 日の追跡を追加し、両者で再利用する。

### 4.3 合算

`merge_positions(auto, manual)`：同一銘柄は数量合算・平均単価は数量加重平均・`first_entry_date` は min・`latest_entry_date` は max・`source="mixed"`。

## 5. SELL 判定の共通化

- `_generate_sell_signals` に `positions: list[HeldPosition] | None = None` を追加する。`None` の場合は `load_auto_positions` で従来どおり読み込む（既存呼び出し・バックテストの挙動は不変）。
- 価格（終値）は従来どおり `prices_daily` の `target_date` 以前の最新値を使う。
- `_peak_close` / `_held_days` に `entry_date: date | None` を直接受け取る内部関数を切り出し、既存関数はそれを呼ぶラッパーにする。`HeldPosition` の entry 日を渡すことで手動分も同じ計算になる。
- 戻り値の各要素に `source` と `qty` を追加する（既存キー `code` / `score` / `reason` は維持）。
- `generate_signals` に `manual_positions: list[HeldPosition] | None = None` を追加する。指定時は自動分と合算した保有で SELL 判定する。`signals` テーブルへの書き込みは従来どおり（SELL は発注経路に乗らない）。

## 6. 売却候補の記録：`manual_action_queue`

DuckDB に新規テーブルを追加する（`data/schema.py`）。

```sql
CREATE TABLE IF NOT EXISTS manual_action_queue (
    action_id   VARCHAR   NOT NULL PRIMARY KEY,  -- {date}_{code}_{action}
    date        DATE      NOT NULL,
    code        VARCHAR   NOT NULL,
    action      VARCHAR   NOT NULL CHECK (action IN ('sell_candidate')),
    qty         BIGINT    NOT NULL CHECK (qty > 0),
    reason      VARCHAR   NOT NULL,
    status      VARCHAR   NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done', 'skipped')),
    created_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at  TIMESTAMP
)
```

- `scripts/run_strategy_signal.py` で `MANUAL_TRADING_ENABLED=true` のとき、手動保有（`source` が `manual` / `mixed`）の SELL を `manual_action_queue` に UPSERT する。
- 冪等性: 同じ `action_id` が既にある場合は `reason` / `qty` のみ更新し、ユーザーが変更した `status` は保持する。
- 対象日に候補でなくなった `open` 行は削除せず残す（日付が異なるため影響なし）。
- Execution Engine・`signal_queue` 処理はこのテーブルを参照しない。テストで保証する。
- 操作関数は `operations/manual_trades.py` に `record_sell_candidates` / `list_actions` / `update_action_status` として追加する。

## 7. BUY 側（`scripts/run_portfolio_construction.py`）

`MANUAL_TRADING_ENABLED=true` のとき：

- **資金**: `_calc_manual_portfolio_value(settings, conn)` を追加。
  - 現金 = `MANUAL_TRADING_INITIAL_CASH` − Σ(BUY 約定額 + 手数料) + Σ(SELL 約定額 − 手数料)
  - 総資産 = 現金 + Σ(手動保有数量 × 最新終値)
  - 利用可能現金 = max(現金, 0)
  - 既存の live / paper / dev 分岐より優先する。
- **保有株数**: `current_positions` に手動保有数量を加算する。保有中銘柄は目標株数に対する不足分だけが BUY 株数になる（既存の `calc_position_sizes` の仕組みをそのまま使う）。
- BUY 候補は従来どおり `signal_queue` に入れる（手動運用では候補の中間成果物として扱う）。

## 8. 通知・ダッシュボード

- **夜 LINE**（`operations/line_reports.py::format_evening_message`、`_collect_evening_signals`）
  - SELL 行: `{code} {name} {qty}株 ({reason})`、手動保有分は末尾に `[手動保有]`。
  - BUY 行: 手動保有中銘柄は末尾に `[買い増し]`。
  - SELL の理由・株数は `manual_action_queue` から取得し、自動分は従来表示。
- **Streamlit `12_Manual_Trades.py`**: 「売却候補」タブを追加。日付指定で `manual_action_queue` を一覧し、行ごとに「対応済み」「見送り」に更新できる。

## 9. エラー処理

- `manual_trades` テーブルが存在しない／空: 手動保有なしとして続行。
- 手動保有銘柄の価格が無い: 既存と同じく SELL 判定をスキップし warning ログ。総資産計算では時価 0 扱いで warning。
- `manual_action_queue` への記録失敗: `signals` 書き込みは成功させたまま、ジョブを失敗扱いにしてログ出力（候補の記録漏れに気づけるようにする）。
- LINE 通知失敗は既存どおり握りつぶす。

## 10. テスト

- 手動保有に対して stop_loss / trailing_stop / time_exit / score_drop が判定されること。
- 再購入時に保有日数が数え直されること。
- 自動分のみのとき、改修前と同一の SELL 結果になること（既存テストが無修正で通ること）。
- `manual_positions` 未指定時（バックテスト・フラグ OFF）は手動約定を無視すること。
- 自動・手動の同一銘柄合算が正しいこと。
- 買い増し株数が保有分を差し引いて算出されること。
- 手動運用の現金・総資産計算が正しいこと。
- 同じ候補を二度記録しても 1 行で、`status` が保持されること。
- Execution Engine が `manual_action_queue` を参照しないこと。
- LINE 夜通知の SELL / BUY 行フォーマット。

## 11. 対象外

- ロット別管理（合算・平均単価で扱う）
- ユーザー承認後に発注する確認キュー
- 週次・月次の手動運用成績レポート
