# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリには、戦略・ポートフォリオ構築、注文管理、監視（モニタリング）および運用支援ツールが含まれます。モジュール設計は本番運用を念頭に置き、SQLite / DuckDB をデータ層に使い、OpenAI を用いたニュース評価やレジーム判定機能も備えています。

以下は本コードベースの README（日本語）です。

## プロジェクト概要
- 戦略評価（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み・株数計算、セクター制限、レジーム乗数）
- 注文ライフサイクル管理（OrderManager、ExecutionEngine、Reconciler）
- モニタリング（システム状態、注文滞留、リスク）とアラート（LINE Push）
- Paper Trading（本番 DB と分離した模擬取引）用の仕組み
- AI 連携（ニュース NLP による銘柄センチメント、マクロレジーム判定）
- 運用向けツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

## 主な機能一覧
- portfolio/
  - 候補選定、等金額・スコア重み付け、ポジションサイズ計算（単元丸め、リスク制限）
  - セクターキャップ、レジーム乗数
- research/
  - Momentum / Volatility / Value のファクター計算（DuckDB を経由して prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- execution/
  - OrderManager（注文作成、重複チェック、状態遷移）
  - Reconciler（再起動時のブローカー突合）
  - ExecutionEngine 起動スクリプト（run_execution.py）
- monitoring/
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格の検出）
  - RiskMonitor（ドローダウン、ポジション上限検知）
  - KillSwitch（リスクトリガで ExecutionEngine に停止シグナル）
  - AlertManager（LINE Push で通知）
  - MonitoringEngine（複数モニタの束ね・ポーリング）
  - Streamlit ダッシュボード（監視データ可視化）
  - monitoring_db: SQLite スキーマ初期化・読み書き API
- ai/
  - news_nlp: OpenAI を使ったニュースセンチメント集約 → ai_scores への書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して日次レジーム判定
- tools/
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

## セットアップ手順（開発 / 実行環境）
※以下は本コードから読み取れる依存を基にした手順例です。実際の requirements.txt がある場合はそちらを優先してください。

1. 前提
   - Python 3.10+ を推奨
   - SQLite は OS に同梱されていることが多い
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - その他、プロジェクトで利用するパッケージがあれば追加してください
4. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env を置くか、OS 環境変数で設定します。
   - 自動で .env / .env.local を読み込む仕組みがあります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
6. DB 初期化
   - monitoring の SQLite ファイルは起動スクリプトが必要に応じてテーブル作成（冪等）を行います。
   - DuckDB ファイル（prices_daily 等テーブル格納）はデータ準備が必要です（外部 ETL）。

## 環境変数一覧（主要）
以下は Settings クラスで参照される主要な環境変数です。必須のものは明記します。

必須（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

オプション / デフォルトあり
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — Monitoring 用（監視は環境に関わらず本番 sqlite_path を使用）
- PAPER_FILL_MODE (default: instant) — instant|partial|never|reject
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — Paper Trading 用 DB（paper_trading 環境用）
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|...)
- OPENAI_API_KEY — AI 機能を使う際に必要
- MONITOR_POLL_INTERVAL — run_monitoring.py のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が存在すれば無効化）

注意:
- run_monitoring（監視モジュール）は KABUSYS_ENV に関係なく Settings.sqlite_path（本番用 monitoring.db）を使います。
- run_execution（発注エンジン）は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い paper 用 DB を使用します（本番 DB と完全分離）。

## 使い方（起動コマンド例）
- 監視プロセスを起動（ポーリング）
  - python src/kabusys/run_monitoring.py
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py

- 実行エンジン（ExecutionEngine）を起動
  - python src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading に設定すると paper_trading 専用 DB と Mock ブローカーを使用:
    - KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py

- 停止・フラグ
  - 実行中のプロセス停止は data/stop_requested.flag が作成されると安全に終了します（スクリプトはこのファイルを監視）。
  - KillSwitch（重大リスク発生時）は data/kill.flag を書き込み、ExecutionEngine を停止させる仕組みです。kill.flag は KillSwitch.clear() で削除できます（起動時に KILL_FLAG_CLEAR_ON_START を使う構成も可能）。

- Streamlit ダッシュボード（ローカルで監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - SQLite DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニュース評価 / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す API が用意されています。実行には OPENAI_API_KEY が必要です。コード内 API 呼び出しは OpenAI Python SDK を使用します。

## 運用時の注意事項
- process 優先度を最初に "high" に設定する処理が run_monitoring.py / run_execution.py に含まれます（psutil による）。権限不足で設定に失敗すると警告が出ます。
- monitoring_db.init_monitoring_db は冪等でテーブル作成と軽微なマイグレーション（カラム追加）を行います。初回起動時に自動的に実行されます。
- AI 呼び出しではレート制限・ネットワークエラーに対して指数バックオフでリトライする実装がありますが、API キー未設定時は例外になります。
- Paper Trading を利用する場合は PAPER_TRADING_SQLITE_PATH により本番 DB と分離されます。安全のため本番データと混ざらない運用設計を推奨します。
- Streamlit は monitoring DB を読み取り専用で開くため、同時実行中でもダッシュボード表示が可能です（URI に ?mode=ro を付与）。

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - data/                            — 実行時に利用するデータ/フラグ（リポジトリ直下に作成）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 ExecutionEngine / broker 実装ファイル)
  - tools/
    - paper_verification_report.py

（実際のファイル構成はリポジトリ内の src/kabusys を参照してください）

## 開発者向けメモ
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 多くの関数は副作用を最小化する純粋関数（portfolio / research 等）として設計されています。単体テストが書きやすく保守性を考慮した構成です。
- DuckDB は分析・リサーチ用に使用されます（prices_daily, raw_financials, raw_news 等の大規模データ参照に適するため）。

## よく使うファイル / スクリプト
- run_monitoring.py — 監視ポーリングのメインスクリプト
- run_execution.py — ExecutionEngine を起動するスクリプト
- src/kabusys/tools/paper_verification_report.py — Paper Trading 検証レポート生成
- src/kabusys/monitoring/streamlit_dashboard.py — Streamlit ダッシュボード

---

不明点や README に追加したい具体的な手順（例: requirements.txt の内容、DB の初期データロード手順、broker の設定方法など）があれば教えてください。必要に応じて README を追記・整形します。