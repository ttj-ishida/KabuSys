# KabuSys

日本株自動売買システムのコアライブラリ群（ライブラリ / 起動スクリプト /ツール類）。  
このリポジトリは戦略構築、発注実行（本番 / ペーパートレード）、監視、リサーチ、AI 補助機能（ニュース解析・レジーム判定）などを含みます。

## 概要
KabuSys は以下の要素で構成されています。
- 戦略（ファクター計算、特徴量解析、ポートフォリオ構築、ポジションサイズ計算）
- Execution Engine（ブローカークライアント経由の発注、リスク管理、注文管理、リコンシリエーション）
- Monitoring（システム・取引・リスク監視、Kill Switch）
- Research（DuckDB を用いたファクター計算・解析）
- AI 補助（OpenAI を利用したニュースセンチメント、マクロセンチメント → レジーム判定）
- 運用用スクリプト（起動スクリプト、設定ウィザード、設定検証、検証レポート）

設計方針の重要な点：
- 本番 DB（monitoring 用 SQLite、分析用 DuckDB）は環境変数で指定可能（デフォルト: data/monitoring.db、data/kabusys.duckdb）。
- KABUSYS_ENV によって `paper_trading` モードでは発注先をモックに切り替え、paper_trading 用 SQLite に記録して本番 DB と分離します。
- .env 自動ロード機能があり、プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を読み込みます。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## 主な機能一覧
- 環境設定ツール（対話式ウィザード）
  - kabusys.config_setup: `.env` の作成・更新を支援
- 設定検証ツール
  - kabusys.validate_config: 環境変数や config/*.yaml の存在・簡易整合性チェック
- 起動スクリプト
  - run_execution: Execution Engine を起動（KABUSYS_ENV に応じて本番/ペーパートレード切替）
  - run_monitoring: SystemMonitor のポーリングループを起動
- 監視コンポーネント
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, MonitoringDB
- ポートフォリオ構築
  - 候補選定、等分/スコア重み、セクターキャップ、レジーム乗数、ポジションサイズ計算（単元丸め・利用可能資金考慮）
- リサーチ
  - ファクター計算 (momentum/value/volatility)、将来リターン、IC 計算、統計サマリ
- AI 支援
  - ニュースのセンチメントスコアリング（OpenAI 使用）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（MA + マクロセンチメント）: kabusys.ai.regime_detector.score_regime
- 運用ツール
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

---

## セットアップ手順（開発用）
以下は一般的な手順例です。実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください。

1. リポジトリをクローン、作業ディレクトリへ移動
   - git clone ...
   - cd <project_root>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 主要なライブラリ（例）: duckdb, psutil, openai, pyyaml

4. 環境変数設定 (.env)
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を参考に `.env` を作成
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 便利な変数（デフォルトが用意されているもの）
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）

5. ディレクトリ作成
   - data/ と logs/ は自動作成されますが明示的に作る場合:
     - mkdir -p data logs

注意:
- 自動 .env ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方

### 設定ウィザード
- 対話式で `.env` を作成/更新します。
  - python -m kabusys.config_setup

### 設定検証
- 起動前に設定を検証します。
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict

### Execution Engine 起動
- ExecutionEngine を起動します（発注処理/リスク管理を行う）。
  - python -m kabusys.run_execution
- 挙動:
  - 起動時にプロセス優先度を "high" に設定する試みを行います（psutil に依存）。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - 起動中に data/stop_requested.flag が作成されると安全に停止します。
  - Execution 用 PID ファイル: data/execution.pid（デフォルト）

### Monitoring 起動
- SystemMonitor をポーリング実行します。
  - python -m kabusys.run_monitoring
- 特記事項:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックします。
  - Monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path（SQLITE_PATH）を使用します（monitoring DB は本番 DB を参照する運用が想定）。
  - 停止は data/stop_requested.flag によりループを抜けます。

### Kill Switch / 停止フラグ
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件に応じて data/kill.flag を書き込みます。Execution 起動時にこのファイルが存在すると起動を行わない等のガードが実装されています。
- kill.flag を自動クリアしたくないのが本番運用推奨（環境変数 KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされますが本番では 0 を推奨）。

### ログ
- ロギング設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
  - コンソール (stdout) とファイル (logs/<app_name>.log) に日次ローテーションで出力（既定で 30 日保持）。
  - LOG_DIR や LOG_LEVEL は環境変数で上書き可能。

### Paper Trading 検証レポート
- ペーパートレード記録から検証レポートを生成します。
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

### AI 機能（プログラム的な呼び出し）
- ニュースセンチメントスコア:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)  — api_key が None の場合は OPENAI_API_KEY を参照
- 市場レジームスコア:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)
- OpenAI API キーが必要です。環境変数 `OPENAI_API_KEY` を設定するか、関数に `api_key` を渡します。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - __init__.py
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite の監視用永続化層（テーブル作成・CRUD）
    - system_monitor.py      — システム状態監視（CPU/メモリ/ディスク・データ鮮度・プロセス検出）
    - trade_monitor.py       — （注文滞留・約定異常などの監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 操作ロジック
    - alert_manager.py       — （通知送信ロジック: LINE 等）
    - monitoring_engine.py   — 各 Monitor の統括ポーリング
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — BrokerClient 作成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP + OpenAI 呼び出し・バリデーション・DB 書き込み
    - regime_detector.py     — MA + LLM によるレジーム判定
    - __init__.py

---

## デフォルトのファイルパス（環境変数）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- LOG_DIR: logs/
- (これらは Settings クラスで参照され、.env で上書き可能)

---

## 運用上の注意 / 推奨設定
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知などの運用監視を有効にしてください。validate_config は本番用の追加チェックを行います。
- kill.flag は本番環境で自動クリアしない（KILL_FLAG_CLEAR_ON_START=0 を推奨）。自動クリアを有効にすると、誤って本番を再起動してしまうリスクがあります。
- OpenAI の呼び出しはレートや課金に注意してください。API キーは環境変数で安全に管理してください。
- psutil による優先度設定や CPU affinity は権限が必要な場合があります。設定失敗時は警告ログを出して処理を続行します。

---

## 開発 / テスト
- モジュールは可能な限り純粋関数（DB 参照を限定）で設計されており、ユニットテストが書きやすくなっています。
- AI 呼び出し部分は `_call_openai_api` を patch / モックすることでテスト可能です。
- DB 初期化・マイグレーションは monitoring_db.init_monitoring_db() で冪等に実行されます。

---

もし README に含めたい具体的なセットアップの要件（requirements.txt の内容、運用手順書、systemd ユニットや Dockerfile のテンプレート等）があれば、それに合わせて追記します。