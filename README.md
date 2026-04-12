KabuSys — README
===============

概要
---
KabuSys は日本株向けの自動売買／リサーチ基盤のライブラリ兼アプリ群です。  
主な目的は「取引ロジック（Execution）」「監視（Monitoring）」「ファクター計算・研究（Research）」「ポートフォリオ構築」「ニュース NLP（AI）」を分離して実装し、SQLite / DuckDB を用いてデータ持続化・解析を行うことです。

特徴
---
- マルチ環境対応: KABUSYS_ENV による development / paper_trading / live 切替
- ExecutionEngine（発注）と MonitoringEngine（監視）を分離して起動可能
- Paper Trading モードは本番 DB と分離（data/paper_trading.db）
- DuckDB を使った高速なファクタ・統計処理（prices_daily / raw_financials 参照）
- OpenAI を用いたニュースセンチメント (news_nlp) と市場レジーム判定 (regime_detector)
- Streamlit ベースの監視ダッシュボード
- 監視ログ保存用 SQLite レイヤ（monitoring_db）と各種モニタ（システム / 注文 / リスク）
- レコンシリエーション（再起動後の状態同期）機能

セットアップ
---
前提
- Python 3.10 以上（| 型ヒントや match などを利用していなくとも、Union 表記に | を使っているため）
- SQLite（標準的に Python に同梱）
- pip が使えること

推奨手順
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）
4. .env ファイル設定（任意だが推奨）
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=<token>
     - KABU_API_PASSWORD=<password>
     - OPENAI_API_KEY=<openai-key>
     - LINE_CHANNEL_ACCESS_TOKEN=<token>  （通知用）
     - LINE_USER_ID=<user id>
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=<秒>（run_monitoring 用、デフォルト 60）

DB 初期化
- run_execution.py / run_monitoring.py は内部で init_monitoring_db() を呼び出し、必要な監視テーブルを作成します。明示的な初期化は不要ですが、手動で確認したい場合は以下を使ったスクリプトを作成して sqlite3 接続経由で init_monitoring_db() を呼んでください。

使い方
---
起動スクリプト
- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 概要: プロセス優先度を high に設定し、Settings を読み込み、ブローカークライアントを生成して ExecutionEngine を起動します。
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) に書き込みます。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 概要: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用します（監視ログは production DB を参照する想定）。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）
  - 期間内の稼働率 / 注文成功率 / レイテンシ等を集計して PASS/FAIL 判定を出力します。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルブラウザで監視メトリクス、ポジション、注文ログ、リスクログを確認できます（read-only 接続）。

プログラム API（ライブラリとして利用）
- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank

- AI
  - from kabusys.ai import score_news
  - kabusys.ai.regime_detector.score_regime を使って市場レジーム判定可能（OpenAI API キーが必要）

- 監視
  - from kabusys.monitoring import MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch

設定（Settings）
- 設定は kabusys.config.Settings 経由で取得します（.env または環境変数）。
- 重要項目:
  - KABUSYS_ENV: development / paper_trading / live（必須チェックあり）
  - PAPER_FILL_MODE: paper trading 時の約定挙動（instant/partial/never/reject）
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
  - PID_FILE_PATH / KILL_FLAG_PATH: Execution 停止 / 再開制御用

重要な挙動・注意点
- 監視側（run_monitoring）は常に sqlite_path（本番）を使用します。paper_trading とは分離されます。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用します（本番 DB と混ざらない）。
- .env 自動読み込み: プロジェクトルートを .git または pyproject.toml から探索して自動で .env/.env.local を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- kill.flag: KillSwitch により data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送れます。KillSwitch は再発防止（冪等）を考慮して実装されています。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼びます。psutil による権限不足等はログで警告してスキップします。
- OpenAI 呼び出し: news_nlp と regime_detector は OpenAI を利用します。API エラーはリトライ処理やフォールバック（ゼロスコア）等のフェイルセーフ設計です。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                    — 環境変数・設定読み込みロジック
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - __init__.py
  - news_nlp.py                — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py         — マクロ＋ETF MA で市場レジームを判定して market_regime に書込

- monitoring/
  - __init__.py
  - monitoring_db.py           — SQLite スキーマ / MonitoringDB クラス
  - system_monitor.py          — システム（CPU/MEM/DISK/プロセス/データ鮮度）監視
  - trade_monitor.py           — 注文滞留・約定異常監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag 管理
  - alert_manager.py           — LINE プッシュ通知（クールダウン管理）
  - monitoring_engine.py       — 各 Monitor を束ねてポーリング
  - streamlit_dashboard.py     — Streamlit ダッシュボード

- execution/
  - order_manager.py           — 発注フローと状態遷移 API
  - reconciler.py              — 起動時の再同期（ブローカーとローカルの突合）
  - （その他：broker_factory 等はプロジェクトに存在する想定）

- portfolio/
  - __init__.py
  - portfolio_builder.py       — 候補選定・重み付け
  - position_sizing.py         — 発注株数計算（lot 単位・リスク制限・スケーリング）
  - risk_adjustment.py         — セクターキャップ・レジーム乗数

- research/
  - __init__.py
  - factor_research.py         — momentum / volatility / value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py     — 将来リターン、IC、統計サマリー等

- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- utils/
  - __init__.py
  - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ

ログ・監視
---
- 監視データは SQLite（デフォルト data/monitoring.db）に格納されます。init_monitoring_db() により必要なテーブル・インデックスを作成します。
- LINE 通知は AlertManager 経由。環境変数 LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が未設定だと送信をスキップします。

サンプル .env（例）
---
以下は最低限の例。実運用では秘密情報を適切に管理してください。

KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LOG_LEVEL=INFO
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

補足・開発メモ
---
- DuckDB 接続を受けて SQL と Python を組み合わせる設計のため、prices_daily や raw_financials 等のテーブル整備が必要です（ETL は kabusys.data.pipeline 等に依存）。
- OpenAI 関連はリトライやレスポンス検証の考慮が入っていますが、API 仕様の変更には注意が必要です。
- Paper Trading モードは本番 DB を汚さない設計になっています。実際の取引を行う live 環境では外部 API キーや broker 設定に十分注意してください。

フィードバック / 貢献
---
バグ報告、改善提案やプルリクエストはリポジトリの issue / PR を利用してください。設計・実装の一貫性（DB スキーマ、時刻の UTC 扱い、ルックアヘッド防止等）を尊重して変更してください。

---
必要なら README の英語版や、requirements.txt / .env.example のテンプレート作成も支援します。どの形式でまとめたいか指示してください。