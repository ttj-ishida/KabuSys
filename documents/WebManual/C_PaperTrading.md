# C. テスト運用（ペーパートレード） — WebManual

- **対象**: KabuSys のペーパートレード（仮想売買）環境での運用
- **想定読者**: 本番運用前に動作確認を行いたい運用者・管理者
- **目的**: 実際の資金を使わずにシステムの挙動・成績・連携を安全に検証できるようにする

---

## C-1. ペーパートレードの仕組みと制約

### ペーパートレードとは

KabuSys の「ペーパートレード（仮想売買）」とは、**実際の証券口座を使わずに自動売買ロジックをテストする機能**です。
本番と同じ Execution Engine・Risk Manager・Signal Queue の仕組みを使いながら、発注・約定をシミュレーション（模擬）するため、実際の資金リスクなくシステムの挙動を確認できます。

### 2 種類のペーパートレードモード

KabuSys では、目的に応じて 2 種類のペーパートレードモードをサポートします。

| モード | 概要 | kabu ステーション起動 | 用途 |
|---|---|---|---|
| **① Pure Mock モード** | システム内部の MockBrokerClient で発注・約定を完全シミュレート | 不要 | 発注ロジック・Risk Manager の動作確認 |
| **② 検証環境モード** | kabuステーション検証環境（ポート 18081）に実際に接続してテスト | 必要（検証用ログイン） | API 接続・認証・約定フローの E2E テスト |

> 両モードとも実装済みです（Issue #255）。②の有効化は `KABU_USE_SANDBOX=true` を設定してください。

### Pure Mock モードの仕組み

```
夜間バッチ → Signal Queue (DuckDB)
                     ↓
              ExecutionEngine
                     ↓
            MockBrokerClient（kabu API には繋がない）
            ・send_order()  → FILL_MODE に従い即時 or 部分約定
            ・get_positions() → メモリ上のポジションを返す
            ・get_available_cash() → メモリ上の現金残高を返す
                     ↓
            paper_trading.db (SQLite) に注文・約定を記録
```

### ペーパートレードの主な制約

| 制約 | 詳細 |
|---|---|
| 価格は模擬 | Pure Mock モードでは実際の市場価格に連動しない（約定価格は発注時の指定値 or 0円） |
| 現金は仮想 | MockBrokerClient の初期資金は `PAPER_TRADING_INITIAL_CASH` 環境変数で設定可能（デフォルト: 1,000 万円） |
| 再起動後も状態を引き継ぎ | Execution 再起動時に `paper_trading.db` の約定履歴からポジション・現金残高を自動復元します |
| 夜間バッチは本番と共用 | Signal Queue の生成は本番 DuckDB を使用。データ更新・特徴量生成は本番と同じ |

---

## C-2. ペーパートレード環境のセットアップ

### 事前準備

ペーパートレードを開始する前に、以下が完了していることを確認してください。

- [ ] `python scripts/setup_db.py --paper` を実行し、`data/paper_trading.db` が作成済み
- [ ] 夜間バッチが少なくとも 1 回以上正常に完了し、DuckDB に市場データが存在する
- [ ] `python -m kabusys.validate_config` でエラーが出ないこと

### 環境変数（`.env`）の設定

`.env` ファイルに以下を設定します。

```env
# ペーパートレードモードで起動
KABUSYS_ENV=paper_trading

# 約定シミュレーション方式（下記いずれか）
# instant : 発注した瞬間に全数量が即時約定（デフォルト・速い検証向け）
# partial : 数量の半分だけ約定するシミュレーション
# never   : 発注されるが約定しない（未約定注文のテスト向け）
# reject  : 発注を拒否する（エラーハンドリングのテスト向け）
PAPER_FILL_MODE=instant

# ペーパートレード用 SQLite DB のパス（本番 DB と分離）
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# MockBrokerClient の初期仮想資金（デフォルト: 10,000,000）
# 実際の運用予定資金に合わせてドローダウン・資金上限をテストできます
PAPER_TRADING_INITIAL_CASH=10000000

# ② 検証環境モード（kabuステーションポート 18081）を使う場合のみ設定
# KABU_USE_SANDBOX=true
# KABU_SANDBOX_API_PASSWORD=（検証環境用 API パスワード）
```

> ⚠️ `KABUSYS_ENV=paper_trading` では Execution の注文・約定は `paper_trading.db` に記録されますが、Monitoring は引き続き本番の `data/monitoring.db` を使用します。

---

## C-3. テスト用シグナルの注入（任意の銘柄を指定して検証）

通常、ペーパートレードでは夜間バッチが生成したシグナルを使います。
しかし特定の銘柄について「買い・売りが正しく処理されるか」をピンポイントでテストしたい場合は、ダミーシグナルを注入する CLI ツールを使います（Issue #229 で実装済み）。

### 日付の仕組み（必ず確認）

`inject_dummy_signal` と `run_signal_queue_report` はそれぞれ異なるデフォルト日付を使います。

| コマンド | `--date` 省略時のデフォルト |
|---|---|
| `inject_dummy_signal` | **翌営業日**（夜間バッチ後の注入を想定） |
| `run_signal_queue_report` | **今日**（`date.today()`） |

このため、`inject_dummy_signal` を `--date` 省略で実行した直後に `run_signal_queue_report` を実行すると、日付がずれて **EMPTY** になります。

### 使用パターン

**パターン A: 翌朝の動作確認（本来の用途）**

夜間（または夕方）に注入し、翌朝レポートで確認します。

```powershell
# 夜間：翌営業日向けシグナルを注入（--date 省略でよい）
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100

# 翌朝：date.today() が翌営業日に変わったタイミングでレポート実行
python -m kabusys.run_signal_queue_report
```

**パターン B: 当日すぐに確認したい場合**

注入とレポートで同じ日付を明示します。

```powershell
# 今日の日付でシグナルを注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100 --date 2026-05-12

# 同じ日付でレポート（省略時 date.today() と一致するのでそのままでも可）
python -m kabusys.run_signal_queue_report

# または注入した日付を明示して確認
python -m kabusys.run_signal_queue_report --date 2026-05-12
```

**パターン C: 注入後すぐに翌営業日のシグナルを確認したい場合**

```powershell
# 翌営業日で注入（--date 省略）
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100

# レポートに翌営業日を明示して確認
python -m kabusys.run_signal_queue_report --date 2026-05-13
```

### コマンド一覧

```powershell
# BUY シグナルを注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100

# SELL シグナルを注入（保有銘柄の売りテスト）
python -m kabusys.tools.inject_dummy_signal --code 7203 --side SELL --qty 100

# 日付を指定して注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100 --date 2026-05-12

# 既存シグナルを上書き
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --force

# 注入した日付を指定してレポート確認
python -m kabusys.run_signal_queue_report --date 2026-05-13
```

`pending` 状態でシグナルが表示されれば注入成功です。

---

## C-4. ペーパートレードの日次運用手順

ペーパートレードは本番と同じ `TradingRunbook.md` の運用フローに従います。
以下は、ペーパートレード固有の差分のみを説明します。

### 朝の確認（08:00〜08:05）

本番と同様に、3 本のレポートが Task Scheduler により自動実行されます。

| 時刻 | ジョブ | ペーパートレードでの主な確認内容 |
|------|--------|----------------------------------|
| 08:00 | `pre_market_report` | READY/BLOCKED 判定・停止フラグ確認 |
| 08:02 | `signal_queue_report` | `pending` シグナルの銘柄・売買方向・数量の確認 |
| 08:05 | `position_reconciliation_report` | DB ポジションとブローカー（Mock）の整合確認 |

> ℹ️ `signal_queue_report` は発注予定内容（銘柄・売買方向・数量）を一覧化します。ペーパートレードでも発注内容を事前確認するために活用してください。Pure Mock モードではブローカー接続が不要なため、`position_reconciliation_report` は常に `CLEAN` と判定されます。

手動で再実行したい場合（再確認・デバッグ時）:

```powershell
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
python scripts/run_position_reconciliation_report.py
```

| 確認項目 | ペーパートレードでの確認内容 |
|---|---|
| Signal Queue | `pending` のシグナルが存在するか（または手動注入するか） |
| DB 状態 | `data/paper_trading.db` が存在するか |
| 停止フラグ | `data/stop_requested.flag` が存在しないか |
| kabuステーション | Pure Mock モードでは**不要**（②検証環境モードでは必要） |

### Execution の起動（08:30）

**Pure Mock モードで起動する場合：**

```powershell
$env:KABUSYS_ENV="paper_trading"
python -m kabusys.run_execution
```

または `.env` に `KABUSYS_ENV=paper_trading` を設定済みであれば：

```powershell
python -m kabusys.run_execution
```

**② 検証環境モードで起動する場合：**

```powershell
# .env に以下を設定した上で起動
# KABUSYS_ENV=paper_trading
# KABU_USE_SANDBOX=true
# KABU_SANDBOX_API_PASSWORD=（検証用パスワード）
python -m kabusys.run_execution
```

> kabuステーションを検証用（ポート 18081）でログインしてから起動してください。  
> 発注リクエストはポート 18081 のsandbox APIへ実際に送信されます（`KABU_API_BASE_URL` の設定に関係なく 18081 を使用）。kabuステーション検証環境の仕様により実市場約定は発生しません。
>
> **現物取引余力（`/wallet/cash`）の注意**: 検証環境では `StockAccountWallet: null` が返るため、`get_available_cash()` は常に `0.0` を返します（Issue #317）。第1関門の資金チェックが常に失敗し発注がスキップされますが、これは検証環境の仕様です。発注フロー・認証・API接続の E2E テストは正常に行えます。

### 停止

本番と同じく停止フラグで安全に停止できます。

```powershell
python scripts/stop_system.py
```

または手動でフラグファイルを作成：

```powershell
New-Item data/stop_requested.flag -ItemType File
```

---

## C-5. 仮想売買の結果確認（検証レポートの見方）

### Paper Trading 専用の検証レポート

ペーパートレードの稼働・注文成功率・レイテンシを確認するための専用レポートがあります。

```powershell
# 直近の集計
python -m kabusys.tools.paper_verification_report

# 期間を指定して集計
python -m kabusys.tools.paper_verification_report --from 2026-05-01 --to 2026-05-07
```

このレポートでは以下を確認できます。

| 確認項目 | 見るべきポイント |
|---|---|
| 注文成功率 | `filled` 比率が FILL_MODE の設定通りか |
| レイテンシ | 発注から約定記録までの時間に異常がないか |
| エラー件数 | `rejected` / `error` ステータスの注文がないか |
| ポジション一覧 | 意図した銘柄が保有されているか |

### 成績レポート（ペーパートレード環境指定）

日次・週次・月次の運用成績を paper_trading 環境として集計できます。

```powershell
# 日次成績
python -m kabusys.run_performance_report --type daily --env paper_trading

# 週次成績
python -m kabusys.run_performance_report --type weekly --env paper_trading
```

---

## C-6. テスト環境のリセット

テスト運用を繰り返すと `paper_trading.db` にデータが蓄積します。
ワンコマンドでクリーンな初期状態にリセットできます（Issue #255 で実装済み）。

```powershell
# paper_trading.db を削除して再初期化（取引時間外に実行すること）
python scripts/setup_db.py --paper-reset
```

> ⚠️ `--paper-reset` を実行すると、ペーパートレードの注文・ポジション・約定履歴はすべて失われます。Execution Engine や Streamlit が DB を開いている場合は先に停止してください。

> ℹ️ 通常の `--paper`（テーブル初期化のみ）との違い: `--paper-reset` は既存の `paper_trading.db` ファイル自体を削除してから再作成します。

---

## C-7. 実装済み機能一覧

以下の機能はすべて実装済みです（`TODO_PaperTradingE2E.md` 参照）。

| 機能 | Issue | 状態 | 概要 |
|---|---|---|---|
| ダミーシグナル注入 CLI | #229 | ✅ 実装済み | 任意の銘柄・数量の BUY/SELL シグナルを signal_queue に直接注入 |
| 仮想資金の設定化 | #255 | ✅ 実装済み | `PAPER_TRADING_INITIAL_CASH` 環境変数で MockBrokerClient の初期資金を設定可能に |
| モック口座の状態復元 | #255 | ✅ 実装済み | 毎日の再起動後にも前日のポジション・現金残高が `paper_trading.db` から自動復元される |
| テスト DB リセット機能 | #255 | ✅ 実装済み | `python scripts/setup_db.py --paper-reset` でワンコマンド初期化 |
| kabuステーション検証環境対応 | #255 | ✅ 実装済み | `KABU_USE_SANDBOX=true` でポート 18081 の検証環境に接続し、本番と同じ API コードパスをテスト |
| 検証環境の null 余力に対応 | #317 | ✅ 実装済み | 検証環境（ポート 18081）の `/wallet/cash` が `null` を返す場合、`get_available_cash()` が `0.0` を返すよう修正（`TypeError` クラッシュを防止） |

---

## 参考リンク

- [kabuステーション API ドキュメント](https://kabucom.github.io/kabusapi/ptal/add-in.html) — 検証用ポート（18081）の説明あり
- `documents/08_Operations/TradingRunbook.md` — 日次運用の詳細な手順（本番・ペーパー共通）
- `documents/08_Operations/TODO_PaperTradingE2E.md` — ペーパートレード機能の実装要件一覧
- `documents/08_Operations/FailureRecovery.md` — 異常時の対応手順
