# KabuSys

KabuSys は日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）です。本リポジトリには実行エンジン、監視コンポーネント、研究用のファクター計算や AI ベースのニュース評価などが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は、自動売買の実行と運用監視、研究用データ処理を統合的に提供することです。設計方針として

- 本番・ペーパートレードを明確に分離（DB も分離）
- DuckDB を使った分析（prices_daily / raw_financials 等）
- SQLite を使った監視ログ・トレードログの永続化
- LLM（OpenAI）を用いたニュース NLP / レジーム判定（オプション）
- プロセス優先度・ログ出力の統一化
- 各種 CLI（.env ウィザード、設定検証、レポート生成）

といった点を重視しています。

---

## 機能一覧

- ExecutionEngine（発注エンジン、BrokerClientFactory 経由で実際のブローカー or MockBroker を使用）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine）
- Kill Switch（条件を満たしたら data/kill.flag に書き込んで ExecutionEngine を停止）
- 設定管理（.env を自動ロードする仕組み、Settings クラス）
- .env 対話ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
- Portfolio 構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算、forward returns、IC、統計サマリ等）
- AI 機能（OpenAI を使ったニュースセンチメント評価 / 市場レジーム判定）
- ロギング設定ユーティリティ（日次ローテーション / コンソール出力）
- プロセス優先度設定ユーティリティ（Windows / POSIX を吸収）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、ソースルートへ移動

   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   必須ライブラリ（主要なもの）:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - pyyaml (設定ファイル検証時に YAML を検証するなら)

   例:
   pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt がない場合は、上記パッケージを必要に応じて追加してください。

4. 環境変数の準備

   - 推奨: .env を作成（kabusys.config_setup を使うと対話式で作れます）

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   AI 機能を使う場合:
   - OPENAI_API_KEY

   主要なオプション（デフォルト値あり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
   - LOG_LEVEL — デフォルト: INFO
   - LOG_DIR — デフォルト: logs/
   - PAPER_FILL_MODE — instant | partial | never | reject (paper_trading 用)

   .env を作るには:
   python -m kabusys.config_setup

5. DB 初期化

   実行スクリプト（monitoring / execution）が起動時に監視 DB のテーブルを作成します（init_monitoring_db）。DuckDB のスキーマ（prices_daily 等）は別途データ投入の手順に従って準備してください。

---

## 使い方

### .env 作成（ウィザード）

対話式に .env を作成/更新:
python -m kabusys.config_setup

作成後は設定を検証:
python -m kabusys.validate_config
# 追加で厳密モード（警告があっても FAIL にする）:
python -m kabusys.validate_config --strict

### 実行エンジン起動

ExecutionEngine を起動します。Paper Trading（KABUSYS_ENV=paper_trading）の場合は MockBroker を使用し、data/paper_trading.db に記録します。

python -m kabusys.run_execution

挙動メモ:
- 起動時に Settings に基づいた SQLite 接続（paper_trading の場合は paper_sqlite_path）と DuckDB 接続を作成します。
- data/execution.pid に PID を書く（pid_file の設定による）。
- data/stop_requested.flag（プロジェクト直下 data/stop_requested.flag）を検出するとエンジンを停止します。
- プロセス優先度を "high" に設定しようとします（権限によっては警告）。

### 監視（Monitoring）起動

監視ループをポーリングで起動します（SystemMonitor の定期チェック）:

python -m kabusys.run_monitoring

挙動メモ:
- 環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化します。
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト: 60 秒）。
  例: export MONITOR_POLL_INTERVAL=30
- 停止はプロジェクトルート/data/stop_requested.flag を作成して通知（run_monitoring はこのフラグを監視して終了）。

### Kill Switch（運用上の停止）

- KillSwitch は条件に応じて Settings.kill_flag_path（デフォルト: data/kill.flag）を書き込み、ExecutionEngine に停止信号を送ります。
- 実行エンジン起動時に kill.flag を削除したい場合は KILL_FLAG_CLEAR_ON_START 環境変数を use（0/1）。ただし本番ではクリアしないことを推奨します。

### Paper Trading 検証レポート

paper_trading 用 DB（デフォルト: data/paper_trading.db）から検証レポートを生成します:

python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

出力には稼働率、注文成功率、送信率、レイテンシ（P95）などが含まれ、閾値を超えると FAIL として報告します。

### AI 機能（ニュース NLP / レジーム判定）

- AI 機能を使うには OPENAI_API_KEY が必要です（引数で直接渡す API も一部関数で可能）。
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — raw_news を集約して ai_scores テーブルへ書き込み
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 1321 の MA200 とマクロニュースで市場レジームを推定、market_regime テーブルへ書き込み

API 呼び出しはリトライやフォールバック（失敗時は安全側の値）を備えています。

---

## 主要スクリプト（エントリポイント）

- python -m kabusys.config_setup     → .env ウィザード
- python -m kabusys.validate_config  → 設定検証 CLI
- python -m kabusys.run_execution    → ExecutionEngine 起動
- python -m kabusys.run_monitoring   → Monitoring 起動
- python -m kabusys.tools.paper_verification_report → Paper Trading レポート

---

## 環境変数一覧（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 主要:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- OPENAI_API_KEY — OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア）

PAPER_FILL_MODE（ペーパートレードの約定挙動）:
- instant | partial | never | reject（デフォルト: instant）

注意: Settings クラスは一部の値の妥当性チェックを行います。KABUSYS_ENV や LOG_LEVEL、PAPER_FILL_MODE の値が不正な場合は例外になります。

---

## ディレクトリ構成（src/kabusys 内の主要ファイル）

以下はソースツリーの主要ファイル / モジュールの概観です（抜粋）。

- kabusys/
  - __init__.py  (パッケージ定義、__version__=0.1.0)
  - config.py  (Settings クラス、.env 自動ロード機能)
  - config_setup.py  (.env 対話ウィザード)
  - validate_config.py  (設定検証 CLI)
  - run_execution.py  (ExecutionEngine 起動スクリプト)
  - run_monitoring.py  (SystemMonitor ポーリング起動スクリプト)
  - utils/
    - logging_setup.py  (ロギング設定ユーティリティ)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - execution/  (ExecutionEngine, OrderManager, BrokerFactory など)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - risk_manager.py
    - reconciler.py
  - monitoring/
    - monitoring_db.py  (SQLite のテーブル作成と永続化 API)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

（上記は実装済みの主要部を抜粋したもので、細かいファイルはリポジトリを参照してください）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の扱いに注意してください。validate_config は live 設定時に警告を出します。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）や kill.flag を使って外部から停止させる運用設計です。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリが作れない場合はコンソールのみで継続します。
- AI 機能は外部 API（OpenAI）を使用するため、料金やレートリミット、モデルのバージョン変更に注意してください。news_nlp および regime_detector はリトライやフォールバック実装を行っていますが、API キーの扱いは適切に行ってください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）は別途データパイプラインで準備する必要があります（kabusys.data.pipeline 等のモジュールを参照）。

---

## 開発・テスト

- 各モジュールはできるだけ副作用を少なく、関数単位でのユニットテストがしやすい設計になっています（多くの関数は DB 接続や引数を注入できる）。
- AI 呼び出し箇所は _call_openai_api を内部で使っており、テスト時はモック化して外部通信を遮断できます（例: unittest.mock.patch）。

---

何か追加してほしい情報（例: 実行時のログサンプル、テーブルスキーマ詳細、デプロイ手順、requirements.txt の生成など）があれば教えてください。README をさらに詳細化して提供します。