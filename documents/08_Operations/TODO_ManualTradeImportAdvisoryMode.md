# TODO: 手動注文メイン運用と助言モードの整備

## 1. 背景

現行システムは、夜間バッチで生成したシグナルを `signal_queue` に積み、Execution Engine が Pull 型で発注処理する自動売買フローを前提としている。

kabuステーションを毎営業日起動・ログイン維持し、API 接続状態を確認し続ける運用は負荷が高いことが分かった。
そのため、当面の本番運用では自動発注を主ルートにせず、前日夜・当日朝の候補を見てユーザーが手動注文する運用を主ルートにする。

この TODO では、KabuSys を「発注するシステム」ではなく「候補提示・手動約定取り込み・保有評価・SELL 助言を行うシステム」として整備する。

関連設計:

- `docs/superpowers/specs/2026-09-17-manual-order-main-operation-design.md`
- `documents/WebManual/C_ManualOrderOperation.md`

## 2. 目的

- 前日夜・当日朝に、ユーザーが手動注文できる形式で BUY / SELL 候補を提示する。
- 手動で買付・売却した銘柄を KabuSys に登録し、既存のポジション管理・リスク評価対象に含める。
- 登録済みポジションに対して、自動売買と同じ SELL ロジックを適用して売却候補を出す。
- システムは直接発注せず、ユーザーが手動で売却判断・発注できる形式で提示する。
- 自動売買ポジションと手動投入ポジションを区別できる監査情報を残す。

## 3. 実装要件

### [ ] 1. 前日夜・当日朝の手動注文候補レポート

`signal_queue` を自動発注キューとしてだけでなく、手動注文候補として表示する。

必要項目:

| 項目 | 内容 |
| ---- | ---- |
| `date` | 注文候補日 |
| `code` | 銘柄コード |
| `side` | `buy` / `sell` |
| `suggested_qty` | 推奨数量 |
| `reference_price` | 前日終値または基準価格 |
| `estimated_amount` | 想定約定金額 |
| `reason` | シグナル理由 |
| `skip_note` | 見送り条件 |

出力候補:

```powershell
python -m kabusys.run_manual_order_plan --date 2026-09-17 --save
```

### [ ] 2. 手動売買データ投入 CLI

手動で約定した BUY/SELL を投入する CLI を追加する。

候補:

```powershell
python scripts/import_manual_trade.py --code 7203 --side buy --qty 100 --price 2500 --trade-date 2026-09-16
python scripts/import_manual_trade.py --csv data/manual_trades.csv
```

必須項目:

| 項目 | 内容 |
| ---- | ---- |
| `code` | 銘柄コード |
| `side` | `buy` / `sell` |
| `qty` | 株数 |
| `price` | 約定単価 |
| `trade_date` | 約定日 |
| `source` | `manual` 固定、または任意メモ |
| `note` | 任意の判断メモ |

### [ ] 3. DB スキーマへの出所情報追加

手動投入データと自動売買データを混同しないよう、ポジション・約定履歴に出所情報を持たせる。

検討案:

- `trade_source`: `auto` / `manual`
- `external_trade_id`: 手動投入 CSV 側の一意キー、または冪等キー
- `imported_at`: 投入日時
- `note`: 任意メモ

冪等性のため、同じ手動約定を二重投入しない仕組みを入れる。

### [ ] 4. 助言モードでの SELL 判断

手動投入ポジションにも、自動売買と同じ評価ロジックを適用する。

対象:

- stop loss
- trailing stop
- score drop
- time exit
- `score_drop_atr_gate`
- `entry_3d_max_abs_return` は新規 BUY 抑制なので、保有後の SELL 判断には原則使わない

出力は発注ではなく、売却候補レポートまたは `manual_action_queue` とする。

### [ ] 5. 自動発注しない安全設計

手動注文メイン運用では、BUY / SELL 候補をそのまま Execution Engine に流さない。

方針:

- `signal_queue` に入れる場合は `execution_mode=advisory` のような区分を持たせる。
- Execution Engine は `advisory` を発注対象外として扱う。
- レポート・通知には「手動売却候補」として表示する。
- 本番運用では `scripts/start_system.py --component execution` を標準手順から外す。

これは「AI は直接発注しない」「重複発注を防ぐ」という既存アーキテクチャ制約を維持するため必須。

### [ ] 6. レポート・通知

日次レポートに以下を追加する。

- 手動投入ポジション一覧
- 前日夜の注文候補
- 当日朝の最終注文候補
- 含み損益・保有日数・現在スコア
- 売却候補と理由
- 自動売買ポジションとの差分
- ユーザーが手動で対応すべきアクション

### [ ] 7. テスト

最低限、以下を確認する。

- 同じ手動約定を再投入しても二重登録されない。
- 手動 BUY がポジションとして評価対象になる。
- SELL 条件に該当した場合、発注ではなく助言レポートに出る。
- Execution Engine が `advisory` シグナルを発注しない。
- 自動売買ポジションと手動投入ポジションが監査ログ上で区別できる。
- Execution Engine を起動しなくても、前日夜・当日朝の手動注文候補レポートが生成できる。

## 4. 未決事項

- 手動 SELL を投入したとき、既存ポジションの数量・平均単価をどう更新するか。
- 自動売買ポジションと同一銘柄を手動でも保有した場合、合算管理するかロット別管理するか。
- 手動投入ポジションに対して `max_holding_days` を約定日基準で適用するか、投入日基準で適用するか。
- レポートだけに留めるか、将来的に「ユーザー承認後に発注」できる確認キューへ拡張するか。
- `signal_queue` を手動注文候補として使い続けるか、専用の `manual_action_queue` に分離するか。
- 約定CSVの標準フォーマットを証券会社のエクスポート形式に寄せるか、KabuSys 独自形式にするか。

## 5. 完了条件

- 前日夜・当日朝に手動注文候補を確認できる。
- 手動約定を CLI または CSV で投入できる。
- 投入されたポジションが日次評価・リスク監視・SELL 判断に含まれる。
- 売却候補が自動発注されず、助言として確認できる。
- 二重投入・二重発注を防ぐテストがある。
- kabuステーションを起動しなくても、1週間の手動注文運用を回せる。
