# KabuSys

日本株向け自動売買システム（ライブラリ / デーモン群）のリポジトリです。  
この README はコードベース（src/kabusys/...）に基づき、導入・操作方法と主要コンポーネントを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下のような機能を備えた自動売買プラットフォームのコア実装です。

- シグナル → ポートフォリオ構築 → 発注までの ExecutionEngine
- 実行系・監視系の分離（Execution と Monitoring）
- Paper Trading（模擬発注）モードのサポート（本番 DB と分離）
- モニタリング（システム稼働・注文・リスク）と Kill Switch（停止フラグ）
- DuckDB を用いた研究・ファクター計算モジュール
- OpenAI を使ったニュース NLP / レジーム判定機能（任意）
- 各種ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード・検証ツール等

---

## 主な機能一覧

- Execution
  - ExecutionEngine：発注・注文管理・リスク管理・リコンシリエーション
  - BrokerClientFactory：本番 / モック（paper_trading）クライアント生成
  - ペーパートレード用 DB（data/paper_trading.db）と実 DB の分離

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk/プロセス稼働やデータ鮮度チェック
  - TradeMonitor：注文の滞留・約定異常などの監視（コード中に実装）
  - RiskMonitor：ドローダウン・ポジション数監視とアラートログ
  - KillSwitch：リスクトリガで Execution を停止するフラグ管理
  - MonitoringDB：SQLite に監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を永続化

- Portfolio / Research
  - ポートフォリオ構築（候補選定・重み計算・単元丸め・ポジションサイズ計算）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns, IC, summary）

- AI（任意）
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector: ETF + LLM による市場レジーム判定（market_regime へ書込）

- ツール
  - 設定ウィザード（.env 作成支援）
  - 設定検証 CLI（.env + config/*.yaml のチェック）
  - Paper Trading 検証レポート生成ツール

- ユーティリティ
  - 統一的ログ設定（logs/<app>.log 日次ローテート）
  - プロセス優先度 / CPU affinity 設定

---

## システム要件（目安）

- Python 3.10+
- 以下は各機能で必要な外部パッケージ（用途別）
  - duckdb (DuckDB 接続)
  - psutil (プロセス / CPU / メモリ / disk)
  - openai (ニュース NLP / レジーム判定)
  - PyYAML（config/*.yaml の検証時に利用）
- SQLite は標準ライブラリで利用可能

requirements.txt がない場合は必要に応じて個別にインストールしてください。

例：
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（初期）

1. リポジトリをクローンしてワークツリーへ移動
   - （既存のプロジェクトルート想定: .git または pyproject.toml が存在する）

2. Python 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install duckdb psutil openai pyyaml

3. 対話式で .env を作成（推奨）
   - python -m kabusys.config_setup
   - ウィザードに従い J-Quants / kabuAPI の秘密情報などを入力します。
   - 生成された .env は Git にコミットしないでください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります。

5. ログディレクトリの作成（通常は自動）
   - デフォルト: logs/
   - 権限等で作成できない場合は環境変数 LOG_DIR を設定してください。

6. データディレクトリ（data/）を作成
   - 必要に応じて data/ を作成し、各種 PID / flag / DB ファイルを置く

---

## 主な環境変数（抜粋）

重要な環境変数とデフォルト値・説明：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 有効値: development / paper_trading / live
  - paper_trading: MockBroker を使用し data/paper_trading.db を利用
  - live: 本番（発注が実行されます）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 時の専用 DB
- PAPER_FILL_MODE (default: instant) — paper_trading の模擬約定モード
  - instant | partial | never | reject
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY — AI 機能を使う場合に必要
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (default: 0) — 起動時に kill.flag を自動クリアするか

自動で .env ファイルを読み込む仕組み:
- プロジェクトルートにある `.env` と `.env.local` を読み込みます（OS環境変数より優先度低）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（テスト用）。

例 .env の抜粋（ウィザードで生成されます）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（起動 / 実行）

基本的にはモジュールを直接実行します（プロジェクトルートで実行）。

1. ExecutionEngine を起動（発注実行）
   - python -m kabusys.run_execution
   - 動作中は data/execution.pid に PID を書き、停止は data/stop_requested.flag の作成で受け付けます。
   - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されます。

2. Monitoring の起動（監視ループ）
   - python -m kabusys.run_monitoring
   - デフォルトでポーリング間隔は 60 秒。環境変数で上書き可能:
     - MONITOR_POLL_INTERVAL=30 など（秒）
   - Monitoring は常に `settings.sqlite_path`（デフォルト data/monitoring.db）を使用してログを残します。
   - 停止はプロジェクトルートの data/stop_requested.flag を作ることで監視ループが終了します。

3. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH を指定するか、PAPER_TRADING_SQLITE_PATH 環境変数で指定

6. AI / 研究系の呼び出し（ライブラリ API）
   - ニューススコアリング（ai/news_nlp.py）
     - kabusys.ai.score_news(conn, target_date, api_key=None)
   - レジーム判定（ai/regime_detector.py）
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらをスケジュール（ジョブ）として呼び出すことが想定されています。
   - OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、呼び出し時に引数で渡します。

停止・強制停止の仕組み:
- data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します（優雅に終了）。
- Kill Switch（リスクトリガ）により data/kill.flag が書かれると Execution 停止リクエストのトリガになります（設定により自動クリアは危険です）。

ログ出力:
- logs/<app>.log に日次ローテートで出力されます（デフォルト保管: 30 日）。
- コンソール出力は stdout に出ます。

---

## よく使う CLI 例

- .env を生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（ポーリング 30 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

kabusys/
- execution/ — 発注・エンジン関連（Broker, Engine, OrderManager, Reconciler, RiskManager 等）
- monitoring/
  - monitoring_db.py — SQLite スキーマ & 永続化層
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文監視（滞留・約定異常など）
  - risk_monitor.py — ドローダウン・ポジション数監視
  - monitoring_engine.py — 各 Monitor の統合ポーリングロジック
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — アラート送信管理（LINE 等、実装箇所に応じて）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・集約上限処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — forward returns, IC, summary
- ai/
  - news_nlp.py — OpenAI を使ったニューススコアリング
  - regime_detector.py — レジーム判定（ETF MA + マクロ NLP）
- data/ — 実行時に作成することが多い。例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity

---

## 注意事項 / 運用上のヒント

- .env は絶対に Git にコミットしないでください（シークレット・API キーを含みます）。
- KABUSYS_ENV=live（本番）では特に kill_flag や通知設定（LINE）を入念に確認してください。
- Monitoring は本番 sqlite_path（data/monitoring.db）を常に使用します。Paper Trading データは paper_trading 用 DB に分離されます。
- OpenAI を使用する機能は API コスト・レート制限に注意して運用してください（リトライ・バックオフ実装あり）。
- ログディレクトリや DB の親ディレクトリが存在しない場合、validate_config は警告を出しますが起動時に自動作成されることもあります。権限・ディスク容量に注意してください。
- DB マイグレーションは monitoring_db.init_monitoring_db で簡易的に実施（カラム追加など）。

---

この README はコードの主要な使い方・初期セットアップをまとめたものです。  
詳細な API や内部設計（StrategyModel.md / PortfolioConstruction.md 等のドキュメント参照）があれば合わせて参照してください。必要なら README の補足（動作フロー図・設定テンプレート・運用手順）を追加します。