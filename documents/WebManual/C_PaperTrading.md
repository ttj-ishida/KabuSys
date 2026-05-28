# C. テスト運用（ペーパートレード） — WebManual

- **対象**: KabuSys のペーパートレード（仮想売買）環境での運用
- **想定読者**: 本番運用前に動作確認を行いたい運用者・管理者
- **目的**: 実際の資金を使わずにシステムの挙動・成績・連携を安全に検証できるようにする

---

## ▶ まず読む：ペーパートレードの全体像

ペーパートレードとは、**実際の証券口座を使わずに自動売買ロジックをテストする機能**です。本番と同じ仕組みで動きますが、発注・約定はシミュレーションになります。

### どちらのモードを使えばよいか？

```
初めてテストする  →  ① Pure Mock モード（kabu ステーション不要・手軽）
API 接続も確認したい  →  ② 検証環境モード（kabu ステーション検証版が必要）
```

| モード | kabu ステーション | 何をテストできるか | `PAPER_FILL_MODE` | `PAPER_TRADING_INITIAL_CASH` |
|---|---|---|---|---|
| **① Pure Mock** | 不要 | 発注ロジック・Risk Manager の動作 | 有効（即時・部分・未約定・拒否） | 有効（仮想資金） |
| **② 検証環境** | 必要（検証用ログイン） | API 接続・認証・約定フローの E2E | **無効**（実 API に委譲） | 有効（仮想資金として資金チェックに使用） |

> **迷ったら ① Pure Mock モードから始めてください。** このマニュアルの手順は① をベースに書いています。

---

## C-1. 初回セットアップ（最初の 1 回だけ）

### ステップ 1 ── `.env` の設定

プロジェクトルートの `.env` ファイルに以下を追加します。

```env
# ペーパートレードモードで起動
KABUSYS_ENV=paper_trading

# 約定シミュレーション方式（① Pure Mock モードのみ有効。② 検証環境モードでは無視される）
# instant : 即時全数量約定（まずはこれ）
# partial : 半分だけ約定
# never   : 約定しない（未約定テスト用）
# reject  : 発注を拒否（エラー処理テスト用）
PAPER_FILL_MODE=instant

# ペーパートレード専用 DB のパス（本番 DB とは別ファイル）
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# 仮想初期資金（デフォルト: 1,000 万円）
PAPER_TRADING_INITIAL_CASH=10000000
```

> ② 検証環境モードを使う場合は、さらに以下を追加します。
> ```env
> KABU_USE_SANDBOX=true
> KABU_SANDBOX_API_PASSWORD=（検証環境用 API パスワード）
> ```

### ステップ 2 ── ペーパートレード DB の作成

```powershell
python scripts/setup_db.py --paper
```

`data/paper_trading.db` が作成されれば成功です。

### ステップ 3 ── 設定の確認

```powershell
python -m kabusys.validate_config
```

エラーが出なければセットアップ完了です。

> **注意**: 夜間バッチが少なくとも 1 回以上完了していないと、シグナルが生成されません。バッチが未実施の場合は後述の「C-3. テスト用シグナルの注入」でダミーシグナルを使って動作確認できます。

---

## C-2. はじめての動作確認（起動テスト）

セットアップ後、次の手順でシステムが正常に動くか確認します。

### 1. テスト用シグナルを注入する

夜間バッチの代わりに、手動でダミーシグナルを入れます。

```powershell
# 例: トヨタ（7203）を 100 株 BUY するシグナルを「今日の日付」で注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100 --date 2026-05-28
```

> `--date` は今日の日付を入力してください（`YYYY-MM-DD` 形式）。

シグナルが入ったか確認します。

```powershell
python -m kabusys.run_signal_queue_report
```

`pending` 状態で表示されれば成功です。

### 2. Execution Engine を起動する

```powershell
# .env に KABUSYS_ENV=paper_trading が設定済みの場合
python -m kabusys.run_execution
```

起動すると、Signal Queue の `pending` シグナルを処理し始めます。ログに注文・約定の記録が流れれば正常動作しています。

### 3. 結果を確認する

```powershell
# 仮想売買の稼働状況・注文成功率を確認
python -m kabusys.tools.paper_verification_report
```

`filled` ステータスの注文が表示されれば、エンドツーエンドの動作確認完了です。

### 4. 停止する

```powershell
python scripts/stop_system.py
```

---

## C-3. テスト用シグナルの注入（詳細）

### 日付のルール（ハマりやすいポイント）

`inject_dummy_signal` と `run_signal_queue_report` でデフォルトの日付が異なります。

| コマンド | `--date` 省略時のデフォルト |
|---|---|
| `inject_dummy_signal` | **翌営業日** |
| `run_signal_queue_report` | **今日** |

`--date` を省略して注入した直後にレポートを実行すると日付がずれて **EMPTY** になります。**迷ったら両方に同じ日付を明示してください。**

### よく使うパターン

**今日すぐ確認したい（推奨：初回テスト時）**

```powershell
# 今日の日付でシグナルを注入（日付は今日に合わせること）
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100 --date 2026-05-28

# レポートで確認（date.today() = 今日なのでそのまま実行でよい）
python -m kabusys.run_signal_queue_report
```

**夜間に注入して翌朝確認する（本来の用途）**

```powershell
# 夜間：翌営業日向けシグナルを注入（--date 省略でよい）
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100

# 翌朝：日付が変わった後にそのまま実行
python -m kabusys.run_signal_queue_report
```

**夜間に注入してすぐ翌営業日のレポートも確認したい**

```powershell
# 翌営業日で注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100

# レポートにも翌営業日を明示（例: 明日が 2026-05-29 の場合）
python -m kabusys.run_signal_queue_report --date 2026-05-29
```

### コマンド一覧

```powershell
# BUY シグナルを注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100

# SELL シグナルを注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side SELL --qty 100

# 日付を明示して注入
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100 --date 2026-05-28

# 既存シグナルを上書き
python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --force

# 特定日付のシグナルをレポートで確認
python -m kabusys.run_signal_queue_report --date 2026-05-28
```

---

## C-4. 毎日の運用手順

ペーパートレードの 1 日の流れです。**太字** が自分でやること、それ以外は Task Scheduler が自動実行します。

### 夜間（前日 17:30 〜 当日 08:05）

| 時刻 | 内容 | 自動/手動 |
|------|------|----------|
| 17:30 | 市場データ更新 | 自動 |
| 18:30 | 特徴量計算 | 自動 |
| 20:00 | 売買シグナル生成 | 自動 |
| 21:00 | ポートフォリオ構築 | 自動 |
| 21:15 | 夜間バッチ結果レポート生成 | 自動 |
| **21:30 頃** | **夜間バッチ結果の確認** | **手動** → `artifacts/night_batch/` を開く |
| 08:00 | Pre-Market レポート | 自動 |
| 08:02 | Signal Queue レポート | 自動 |
| 08:05 | Position Reconciliation レポート | 自動 |

### 朝の起動前チェック（08:05〜08:30）

自動生成された 3 本のレポートを確認します。

| レポート | 確認するポイント |
|----------|----------------|
| Pre-Market | READY / BLOCKED の判定・停止フラグの有無 |
| Signal Queue | `pending` シグナルが存在するか、銘柄・方向・数量は正しいか |
| Position Reconciliation | `CLEAN` と表示されるか（Pure Mock では常に CLEAN） |

手動で再実行したい場合：

```powershell
python scripts/run_pre_market_report.py
python scripts/run_signal_queue_report.py
python scripts/run_position_reconciliation_report.py
```

チェックリスト：

- [ ] Signal Queue に `pending` シグナルがある（なければ C-3 で手動注入）
- [ ] `data/paper_trading.db` が存在する
- [ ] `data/stop_requested.flag` が存在しない（あれば削除）
- [ ] Pure Mock モードの場合、kabu ステーション起動は**不要**

### ザラ場（08:30〜15:00）

| 時刻 | 内容 | 自動/手動 |
|------|------|----------|
| **08:30** | **Execution Engine 起動** | **手動** |
| **09:00** | **Streamlit ダッシュボード起動・監視** | **手動** |
| 15:00 | （自動停止またはフラグで停止） | 自動/手動 |

**Execution Engine の起動（Pure Mock モード）：**

```powershell
python -m kabusys.run_execution
```

**Streamlit ダッシュボードの起動：**

```powershell
python scripts/run_streamlit_dashboard.py
```

**② 検証環境モードで起動する場合：**

```powershell
# .env に KABU_USE_SANDBOX=true を設定した上で、kabu ステーションを
# 検証用（ポート 18081）でログインしてから起動
python -m kabusys.run_execution
```

> **検証環境の注意**: `PAPER_FILL_MODE` は検証環境モードでは無効です（実際の kabu ステーション検証 API に発注が委譲されます）。資金残高は `PAPER_TRADING_INITIAL_CASH`（またはペーパー DB 復元値）を仮想値として使用するため、BUY 発注が資金チェックでスキップされることはありません（Issue #363 で修正済み）。

### 引け後（15:00〜）

```powershell
# 引け後確認レポート
python -m kabusys.run_market_close_report --save
```

### 停止

```powershell
python scripts/stop_system.py
```

---

## C-5. 結果の確認

### ペーパートレード専用の検証レポート

注文成功率・レイテンシ・エラー件数を確認します。

```powershell
# 直近の集計
python -m kabusys.tools.paper_verification_report

# 期間を指定
python -m kabusys.tools.paper_verification_report --from 2026-05-01 --to 2026-05-07
```

| 確認項目 | 見るべきポイント |
|---|---|
| 注文成功率 | `filled` 比率が `PAPER_FILL_MODE` の設定通りか |
| レイテンシ | 発注から約定記録までの時間に異常がないか |
| エラー件数 | `rejected` / `error` ステータスの注文がないか |
| ポジション一覧 | 意図した銘柄が保有されているか |

### 成績レポート

```powershell
# 日次成績
python -m kabusys.run_performance_report --type daily --env paper_trading

# 週次成績
python -m kabusys.run_performance_report --type weekly --env paper_trading
```

---

## C-6. テスト環境のリセット

テストを最初からやり直したい場合、ワンコマンドで初期化できます。

```powershell
# paper_trading.db を削除して再初期化（取引時間外に実行すること）
python scripts/setup_db.py --paper-reset
```

> ⚠️ **注文・ポジション・約定履歴はすべて削除されます。** 実行前に Execution Engine と Streamlit を停止してください。

---

## C-7. ペーパートレードの仕組み（参考）

### Pure Mock モードの内部フロー

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

### 検証環境（Sandbox E2E）モードの内部フロー

```
夜間バッチ → Signal Queue (DuckDB)
                     ↓
              ExecutionEngine
                     ↓
            PaperSandboxBroker（ラッパー）
            ・get_available_cash() → paper_trading.db 復元値
            │                        または PAPER_TRADING_INITIAL_CASH を返す
            │                        ※ /wallet/cash API には問い合わせない
            └→ KabuStationClient（検証環境 ポート 18081）
               ・send_order()  → kabu ステーション検証 API に実発注
               ・get_positions() → 検証環境のポジションを返す
                     ↓
            paper_trading.db (SQLite) に注文・約定を記録
```

> **PAPER_FILL_MODE の扱い**: 検証環境モードでは `PAPER_FILL_MODE` は参照されません。約定は kabu ステーション検証環境の応答に依存します。

### 主な制約

| 制約 | 詳細 |
|---|---|
| 価格は模擬 | Pure Mock モードでは実際の市場価格に連動しない |
| 現金は仮想 | `PAPER_TRADING_INITIAL_CASH` で設定した金額が初期残高 |
| 再起動後も状態を引き継ぎ | `paper_trading.db` から前回のポジション・残高を自動復元 |
| 夜間バッチは本番と共用 | データ更新・シグナル生成は本番 DuckDB を使用 |

### 実装済み機能

| 機能 | Issue | 概要 |
|---|---|---|
| ダミーシグナル注入 CLI | #229 | 任意銘柄の BUY/SELL シグナルを直接注入 |
| 仮想資金の設定化 | #255 | `PAPER_TRADING_INITIAL_CASH` 環境変数で初期資金を設定 |
| モック口座の状態復元 | #255 | 再起動後もポジション・現金残高を自動復元 |
| テスト DB リセット機能 | #255 | `--paper-reset` でワンコマンド初期化 |
| kabuステーション検証環境対応 | #255 | `KABU_USE_SANDBOX=true` でポート 18081 に接続 |
| 検証環境の null 余力に対応 | #317 | `/wallet/cash` が `null` の場合のクラッシュ防止 |
| PaperSandboxBroker | #363 | 検証環境でも `PAPER_TRADING_INITIAL_CASH` を仮想資金として使用（BUY がスキップされない） |

---

## 参考リンク

- [kabuステーション API ドキュメント](https://kabucom.github.io/kabusapi/ptal/add-in.html) — 検証用ポート（18081）の説明あり
- `documents/08_Operations/TradingRunbook.md` — 日次運用の詳細手順（本番・ペーパー共通）
- `documents/08_Operations/TODO_PaperTradingE2E.md` — ペーパートレード機能の実装要件一覧
- `documents/08_Operations/FailureRecovery.md` — 異常時の対応手順
