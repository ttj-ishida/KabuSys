# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）。

このリポジトリは、注文実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、リサーチ・AI ツールなどを含んだモジュール群です。コードは「実行」「監視」「検証（Paper Trading）」「研究（Factor／Feature）」などの用途に分かれています。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 使い方（起動 / 実行例）
- 環境変数（主要）
- 停止 / フラグファイルの扱い
- ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は日本株自動売買のための内部ライブラリと、運用用の起動スクリプト群を提供します。主な要素は以下です。

- ExecutionEngine: ブローカークライアントを経由した発注／注文管理、リスク管理、リコンシリエーション
- Monitoring: システム状態、注文滞留・約定異常、ドローダウン等を監視しログ保管・アラート送信（LINE）
- Paper Trading: 本番環境と分離した紙運用（mock broker）と検証ツール（レポート生成）
- Research / AI: DuckDB を使ったファクター計算、将来リターン計算、ニュースの LLM スコアリング（OpenAI）
- Portfolio construction: 候補選定、重み付け、ポジションサイジング、セクターキャップ等の純粋関数群

---

## 機能一覧

- システムモニタ（CPU / メモリ / ディスク / PID / データ鮮度）
- 注文監視（滞留注文、約定価格の異常検出）
- リスク監視（ドローダウン・保有数上限）と kill switch（停止フラグ生成）
- LINE によるアラート通知（cooldown 管理）
- ExecutionEngine：ブローカー抽象（本番 or paper_trading 切替）、リスク管理、OrderManager、Reconciler
- Paper Trading 検証レポートを標準出力に生成するツール
- Streamlit ダッシュボード（監視 DB を可視化）
- DuckDB を使ったファクター計算（Momentum / Volatility / Value）
- OpenAI を使ったニュースセンチメント評価（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- process priority / CPU affinity のユーティリティ

---

## 前提条件

- Python 3.10 以上（パイプラインや typing の構文で使用）
- OS: Linux / macOS / Windows（process priority はプラットフォームによる制限あり）
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（組み込みライブラリ）
- ネットワークアクセス（ブローカー API / OpenAI / LINE API を使う場合）

インストールの例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# または requirements.txt がある場合:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンして移動
```bash
git clone <repo-url>
cd <repo-root>
```

2. 仮想環境作成 & パッケージインストール（上記参照）

3. 環境変数の準備
- プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動読み込みされます（デフォルトでは OS 環境 > .env.local > .env の優先順）。
- 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. データディレクトリ
- デフォルトでは `data/` 配下のファイル（SQLite、DuckDB、PID/flag）を使用します。必要なら環境変数でパスを上書きできます。

5. DB 初期化
- 各稼働スクリプトは起動時に必要な監視テーブルを作成（init_monitoring_db）します。手動で作成する必要は通常ありません。

---

## 使い方

### 環境モード
- KABUSYS_ENV（必須）
  - development
  - paper_trading
  - live

例: paper trading（本番 DB と分離）
```bash
export KABUSYS_ENV=paper_trading
```

### 主要スクリプト起動（モジュール実行）

- 監視ループ（SystemMonitor を使ったポーリング）
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を秒で上書き:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
備考: run_monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path を使います（監視は本番 DB を参照）。

- ExecutionEngine（取引実行）
```bash
python -m kabusys.run_execution
```
備考:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録して本番 DB と分離します。
- 起動時に `data/stop_requested.flag` が存在すると起動を行いません。
- 実行中に stop flag を作成するとエンジンに停止シグナルを送れます。

- Paper Trading 検証レポート（コマンドラインツール）
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report
# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- Streamlit ダッシュボード（監視用 UI）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI / リサーチ関数（ライブラリ的に利用）
  - ニューススコアリング: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - ファクター計算: `kabusys.research.calc_momentum(conn, target_date)` など

これらは DuckDB 接続（duckdb.connect(...)）を引数に受けます。OpenAI を使う場合は `OPENAI_API_KEY` または関数引数 `api_key` を設定してください。

---

## 環境変数（主要）

config.Settings で参照される主要な環境変数（抜粋）:

- KABUSYS_ENV : development | paper_trading | live
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (AlertManager 用)
- LINE_USER_ID (AlertManager 用)
- OPENAI_API_KEY (ai モジュールで使用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用: デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper trading 用 DB、デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定動作: instant | partial | never | reject)
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔上書き)
- LOG_LEVEL (DEBUG/INFO/...）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

.env.example を元に .env を作成してください。

---

## 停止 / フラグファイルの扱い

- data/stop_requested.flag
  - run_monitoring, run_execution がループ中に監視する停止フラグ。存在するとループを終了します。
- data/kill.flag
  - KillSwitch（RiskMonitor の結果によって）を書き込むと ExecutionEngine に停止を促すためのフラグになります。
- PID ファイル（data/execution.pid）
  - 実行プロセスが PID を書き込みます。SystemMonitor はこの PID の存在と生存確認でプロセスが生きているか監視します。

KillSwitch は drawdown や position limit などの条件で kill.flag を書き込みます（冪等性あり）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定読み込み
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py            — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py             — システム状態監視
    - trade_monitor.py              — 注文滞留 / 約定異常監視
    - risk_monitor.py               — ドローダウン / ポジション数監視
    - kill_switch.py                — kill.flag の生成/削除
    - alert_manager.py              — LINE 通知
    - monitoring_engine.py          — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py        — streamlit ダッシュボード
  - execution/
    - order_manager.py              — 注文の作成・同期 API
    - reconciler.py                 — 起動時リコンシリエーション
    - ...                           — （ブローカー/エンジン関連の他ファイル）
  - portfolio/
    - portfolio_builder.py          — 候補選定、重み計算
    - position_sizing.py            — 数量計算、スケーリング
    - risk_adjustment.py            — セクター制限、レジーム乗数
  - research/
    - factor_research.py            — Momentum / Value / Volatility 計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - utils/
    - process_priority.py           — プロセス優先度／CPU affinity ユーティリティ
  - data/                            — 既定の DB / pid / flag が置かれる想定ディレクトリ

---

## 注意事項 / 運用上のヒント

- 監視 DB（monitoring.db）は run_monitoring が使用するデフォルトの SQLite です。監視は本番 DB を参照するよう設計されています（監視の正確性のため）。
- Paper Trading モードでは paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- OpenAI / LINE / ブローカーの認証情報は環境変数で管理してください。.env / .env.local を用いるとローカルで簡単にセットできます。
- process priority や CPU affinity の設定は権限やプラットフォームに依存します。権限不足で失敗する可能性があるため、ログに警告が出ますが処理は継続します。
- DuckDB を大量データで使う場合はパスやファイルロックに注意してください（streamlit では read-only URI を使って接続する例あり）。

---

不明点や README の追加情報（例: サンプル .env.example、requirements.txt、運用手順書）を追加したい場合は指示してください。