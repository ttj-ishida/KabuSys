# KabuSys

KabuSys は日本株向けの自動売買システムのコードベースです。  
このリポジトリは注文実行（Execution）、監視（Monitoring）、研究（Research）、AI（ニュースセンチメント / レジーム判定）、ポートフォリオ構築、および運用ツール群を含みます。

---

## プロジェクト概要

主な目的は「安全性を重視した自動売買の実行基盤と運用監視」です。  
設計方針の要点：

- Execution（発注）と Monitoring（監視）を明確に分離
- DuckDB を用いた時系列ファクタ計算（研究用途）
- SQLite を用いた軽量な運用ログ・監視 DB
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとマクロ判定（AI モジュール）
- Paper Trading（模擬売買）を環境変数で切替可能（本番 DB と分離）
- フェイルセーフ（例：API 失敗時のフォールバック、冪等性、データ欠損時の安全動作）

---

## 機能一覧

- Execution
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - オーダー作成・送信・同期（OrderManager, Reconciler）
  - リスク管理（RiskManager）・注文リポジトリ（OrderRepository）
  - Paper Trading モード（MockBroker 使用、paper_trading DB に記録）
- Monitoring
  - システム状態監視（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - 注文滞留・約定異常検知（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（条件で Execution を停止する flag ファイル）
  - LINE へアラート送信（AlertManager）
  - 監視用ストリームリットダッシュボード（streamlit_dashboard.py）
  - 監視 DB 管理（monitoring_db.py）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- Research（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 前方リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュース NLP（news_nlp）: LLM で銘柄ごとにセンチメントを算出して ai_scores に格納
  - Regime Detector（regime_detector）: ETF の MA とマクロセンチメントを合成して市場レジームを判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順

※ 以下は典型的な手順です。CI や配布パッケージがある場合はそれに従ってください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境準備（推奨 Python >= 3.10）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が存在する場合:
     - pip install -r requirements.txt
   - 参考パッケージ（本プロジェクトで使用）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - sqlite3 は Python 標準ライブラリで提供されます。

4. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...（AI 機能を使う場合必須）
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL（秒、監視ループの間隔、デフォルト 60）

5. データディレクトリ作成
   - mkdir -p data

注意: process priority / CPU affinity 設定は OS により権限が必要です。psutil による優先度設定で AccessDenied 警告が出る場合がありますが安全に無視されます。

---

## 使い方

基本的な起動例（リポジトリルートから実行）:

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  - KABUSYS_ENV=live:
    - python -m kabusys.run_execution
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH にデータを保存します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 30秒ごとにポーリング

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで確認できます（ローカルファイルを read-only モードで開きます）。

- AI 機能（ニューススコア付与 / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY）。
  - モジュール関数を Python から呼ぶか、スクリプト経由で組み込んで実行してください。
  - 例（ライブラリとして呼び出す）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)

- kill.flag による Execution 停止
  - KillSwitch は条件検知時にデータ/kill.flag を書き込み、ExecutionEngine はそれを検出して安全停止する設計です。
  - Execution 起動時に kill flag をクリアする場合は Settings.kill_flag_clear_on_start を環境変数で制御できます（KABUSYS 設定参照）。

ログレベルは LOG_LEVEL 環境変数で指定可能（DEBUG/INFO/...）。Settings クラスでその他設定を取得します。

---

## 主要設定（Settings）

設定は environment variables もしくは `.env` / `.env.local` で行います。主なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（Paper Trading 時の SQLite）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH（監視・プロセス管理用ファイルパス）
- MONITOR_POLL_INTERVAL（監視ループ間隔、秒）

自動で .env ファイルをプロジェクトルートから読み込みます（.git または pyproject.toml を基準にルートを探索）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主なモジュール構成と簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env ロードと Settings クラス
  - run_execution.py
    - ExecutionEngine 起動スクリプト（高優先度で起動、Paper Trading 切替）
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - execution/
    - broker_factory.py, broker_api.py, ...（ブローカー抽象、OrderManager, Reconciler）
    - execution_engine.py（エンジン本体）
    - order_manager.py, order_repository.py, order_record.py など
  - monitoring/
    - monitoring_db.py（SQLite スキーマ・読み書き）
    - system_monitor.py（CPU/メモリ/ディスク/データ鮮度/プロセス監視）
    - trade_monitor.py（注文滞留・約定異常検知）
    - risk_monitor.py（ドローダウン / ポジション上限監視）
    - kill_switch.py（kill.flag 管理）
    - alert_manager.py（LINE 通知）
    - monitoring_engine.py（複数 Monitor の束ね）
    - streamlit_dashboard.py（DashBoard）
  - portfolio/
    - portfolio_builder.py（候補選定 / 重み計算）
    - position_sizing.py（株数決定・丸め・aggregate cap）
    - risk_adjustment.py（セクター上限 / レジーム乗数）
  - research/
    - factor_research.py（momentum/volatility/value ファクター）
    - feature_exploration.py（将来リターン・IC・統計）
  - ai/
    - news_nlp.py（ニュースを OpenAI に渡して銘柄ごとセンチメント算出）
    - regime_detector.py（MA + マクロセンチメントで市場レジーム判定）
  - tools/
    - paper_verification_report.py（Paper Trading の検証レポート）
  - utils/
    - process_priority.py（プロセス優先度 / CPU affinity 設定ユーティリティ）
  - data/
    - （実行時に使用する SQLite / DuckDB ファイル等を置く想定のディレクトリ）

上記以外にも細かなモジュール（order_record, order_repository, execution components 等）が実装されています（ソース内コメントに詳細あり）。

---

## 運用上の注意点 / トラブルシューティング

- process priority の設定は OS による制限や権限を要します。権限不足で警告が出ることがありますが動作自体は継続します。
- モジュールは外部 API（kabuステーション、OpenAI、J-Quants 等）に依存する箇所があります。API キーや接続情報は .env または環境変数で設定してください。
- DuckDB / SQLite ファイルはデフォルトで data/ 下に作成されます。別パスにする場合は DUCKDB_PATH / SQLITE_PATH を指定してください。
- Paper Trading は本番 DB と分離されます（settings.is_paper による切替）。paper_trading 用 DB は PAPER_TRADING_SQLITE_PATH で制御できます。
- AI 呼び出しは外部サービスに依存するため、レート制限や一時的なエラー発生時の挙動は各モジュール内でリトライ/フォールバック実装がありますが、実運用では API 利用制限に留意してください。
- streamlit を使う場合、データベースを read-only で開くために URI 形式で接続しています。MonitoringEngine が DB を作成していない場合はエラーになります（まず監視を起動してください）。

---

## 参考コマンドまとめ

- 仮想環境作成・依存インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

- 実行（本番 / ペーパー）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- 監視起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

本 README はソースコード内コメントを基に作成しています。実運用前に .env.example（存在する場合）や環境固有の設定を確認し、テスト環境で十分に検証することを推奨します。必要であればこの README をベースに導入ドキュメントや運用手順書（Runbook）を追記してください。