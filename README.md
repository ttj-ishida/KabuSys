# KabuSys

日本株向け自動売買システムのコアライブラリ（モニタリング、Execution、リサーチ、ポートフォリオ構築、AI支援などを含む）。  
このリポジトリには運用に必要な起動スクリプト・監視ツール・解析ユーティリティが含まれます。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されています。

- Execution（発注エンジン、OrderManager、Reconciler 等）
- Monitoring（システム状態、注文状態、リスク監視、アラート送信）
- Portfolio（候補選定、重み計算、ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- CLI/ツール（モニタリングループ、エンジン起動、Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の一部:
- 環境変数 / .env による設定管理（自動ロード機能あり、無効化も可能）
- Paper Trading は本番 DB から完全分離（別 SQLite を使用）
- DuckDB をリサーチ／時系列データ解析に利用
- OpenAI API を用いたニュースセンチメント・レジーム判定（オプション）

---

## 主な機能一覧

- SystemMonitor: CPU / メモリ / ディスク / プロセス生存確認、データ鮮度チェック
- TradeMonitor: 注文滞留（stale orders）、約定価格異常検知
- RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
- KillSwitch: リスクトリガーで ExecutionEngine に停止信号を送る（flag ファイル）
- AlertManager: LINE Push による通知（クールダウン管理）
- ExecutionEngine（実行エンジン）: ブローカー連携、リスク管理、オーダー管理、リコンシリエーション
- Portfolio モジュール: 候補選定、等配分／スコア重み、リスク調整、ポジションサイズ計算
- Research モジュール: Momentum/Volatility/Value 等ファクター、IC・forward returns・統計サマリ
- AI モジュール:
  - news_nlp.score_news: raw_news を LLM（OpenAI）で評価し ai_scores に書き込む
  - regime_detector.score_regime: ma200 と LLM を合成して日次の市場レジーム判定
- ツール:
  - run_monitoring.py: 監視ポーリングループ起動
  - run_execution.py: ExecutionEngine 起動
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
  - tools.paper_verification_report: Paper Trading 検証レポート出力

---

## セットアップ手順

前提:
- Python 3.9+（実装上 typing の表記などを利用）
- SQLite（OS に標準搭載）
- 必要な Python パッケージ: duckdb, psutil, requests, openai, streamlit（用途により）

例: 仮想環境を作成して依存関係をインストールする
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

環境変数／.env:
- プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（既存 OS 環境変数は保護されます）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須変数（少なくとも実環境では設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用
（OpenAI を使う場合は以下も必須）
- OPENAI_API_KEY — OpenAI API キー

主要なオプション環境変数（デフォルト値も併記）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- LOG_LEVEL: INFO 等
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

ファイル/ディレクトリ:
- data/: PID・flag・SQLite DB 等を保存（自動作成されます）

初回起動時:
- 監視 DB の初期化はスクリプト実行時に自動で行われます（init_monitoring_db）。

---

## 使い方

基本的な起動コマンド（ソースツリー直下で実行する前提）:

- 監視ループを起動（モニタリングのみ）
```bash
python -m kabusys.run_monitoring
# またはバックグラウンドで実行
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Execution Engine を起動（本番 or paper_trading に応じて DB が分離されます）
```bash
# 本番(デフォルト KABUSYS_ENV=development) または
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Streamlit ダッシュボード（監視 DB を参照、読み取り専用で開く）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポート
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または明示的に DB 指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

AI モジュールの利用例（Python から呼ぶ）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# ニューススコアを生成（OPENAI_API_KEY は環境変数か api_key 引数で指定）
score_news(conn, target_date=date(2026, 4, 10))
# レジーム判定を実行
score_regime(conn, target_date=date(2026, 4, 10))
```

停止・制御:
- ExecutionEngine の停止は data/kill.flag を書き込むことで外部から停止シグナルを発行できます（KillSwitch を経由）。
- run_monitoring / run_execution は起動時に data/stop_requested.flag を検査し、存在すると起動/ループ継続を停止します。

ログレベル:
- 環境変数 LOG_LEVEL を設定すると Settings.log_level が使用され、ログ出力に反映されます（スクリプト内で basicConfig を利用）。

注意点:
- Paper Trading 環境（KABUSYS_ENV=paper_trading）ではブローカークライアントは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と完全分離）。
- run_monitoring は KABUSYS_ENV にかかわらず monitoring 用 SQLite はデフォルトで本番 sqlite_path を使用します（設計上の注意）。

---

## 環境変数一覧（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使用する場合に必須）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH — Execution の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env ローダー / Settings
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py — プロセス優先度 / affinity 設定
- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite 保存層（init + MonitoringDB）
  - system_monitor.py — システム状態監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 操作
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, ...（発注・同期ロジック）
- portfolio/
  - portfolio_builder.py, risk_adjustment.py, position_sizing.py
- research/
  - factor_research.py, feature_exploration.py, ...
- ai/
  - news_nlp.py — LLM によるニューススコアリング
  - regime_detector.py — レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

data/
- （実行時に作成される）monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag など

---

## 運用上の注意・ベストプラクティス

- 本番は KABUSYS_ENV=live で運用してください。paper_trading は本番 DB と切り離して検証を行うための環境です。
- OpenAI の呼び出しはレート制限や一時的なエラーに対してリトライ・フォールバックを組み込んでいますが、APIキー・課金設定を運用前に確認してください。
- data/kill.flag / stop_requested.flag / execution.pid は外部制御用ファイルです。誤操作でエンジンが停止しないよう取り扱いに注意してください。
- DuckDB に保存する時系列データ（prices_daily / raw_financials 等）はリサーチと AI モジュールで参照されます。データ鮮度を監視する SystemMonitor が動作していることを確認してください。
- 単体テスト・モック化対象:
  - news_nlp._call_openai_api 等はテスト時にモック可能な設計になっています。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt やデプロイ手順（systemd ユニット例や Dockerfile）を追加で作成します。どの情報を優先して追加しますか？