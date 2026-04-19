# KabuSys — 日本株自動売買システム

このリポジトリは、日本株の自動売買システム（バックテスト／ペーパートレード／本番運用を想定）のコアモジュール群を含みます。  
ドメイン別にモジュールを分離し、監視・実行・リサーチ・ポートフォリオ構築・AI補助（ニュースセンチメント）などのコンポーネントが実装されています。

注意: この README はソースコード（src/kabusys/*.py）を基に作成しています。実運用では設定（.env）や API キーの管理、十分なテストを行ってください。

---

## 概要

- 設計方針
  - 各モジュールはできるだけ副作用を抑え、テストしやすい関数/クラスとして実装されています。
  - 実行環境は環境変数（.env）で管理。`.env` の初期作成を支援する対話式ウィザードあり。
  - 監視（Monitoring）と実行（Execution）は別プロセス／DB（ペーパートレード時）で分離。
  - DuckDB を分析・リサーチ用に使用、SQLite を監視・トレードログに使用。
  - OpenAI（LLM）を使ったニュース・マクロセンチメント解析機能あり（APIキー必要）。

---

## 主な機能一覧

- 実行
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード用 DB（data/paper_trading.db）を使用
    - 実行中は PID ファイル（data/execution.pid）を生成
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせる MonitoringEngine: src/kabusys/run_monitoring.py, src/kabusys/monitoring/*
  - 監視ログの永続化（SQLite）: monitoring_db.MonitoringDB
  - Kill Switch（データ・ドローダウン等で Execution を停止するためのフラグ管理）
- 環境設定 & 検証
  - 対話式 .env ウィザード: src/kabusys/config_setup.py
  - 設定検証 CLI（.env と config/*.yaml の基本チェック）: src/kabusys/validate_config.py
- ツール
  - ペーパートレード検証レポート: src/kabusys/tools/paper_verification_report.py
- ポートフォリオ構築
  - 候補選定、重み計算、位置サイズ計算、セクターキャップ、レジーム乗数: kabusys.portfolio.*
- リサーチ
  - ファクター計算（モメンタム／ボラティリティ／バリュー）: kabusys.research.factor_research
  - 特徴量探索・IC 計算等: kabusys.research.feature_exploration
- AI（OpenAI）
  - ニュース NLP（銘柄ごとのセンチメント）: kabusys.ai.news_nlp
  - マーケットレジーム判定（マクロ + ETF MA200）: kabusys.ai.regime_detector
- ユーティリティ
  - ログ設定ユーティリティ: kabusys.utils.logging_setup
  - プロセス優先度 / CPU affinity 設定: kabusys.utils.process_priority
  - 設定読み込み・検査: kabusys.config

---

## 事前準備 / 動作要件

- Python 3.10 以上（ソースコードは 3.10 の型記法等を使用）
- SQLite（Python 標準ライブラリに同梱）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml のパース検証を行う場合）
- 例: 仮想環境作成およびインストール
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
  - pip install duckdb psutil openai PyYAML

（requirements.txt をプロジェクトに用意している場合は `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - 主要な必須環境変数:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
     - その他主要変数（デフォルト値あり）:
       - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
       - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
       - KILL_FLAG_CLEAR_ON_START（0/1、デフォルト: 0）
5. 設定検証（必須環境が揃っているか確認）
   - python -m kabusys.validate_config
   - 必要なら --strict をつけて警告もエラー扱いにする
6. （OpenAI 機能を使う場合）OPENAI_API_KEY を設定
   - .env に OPENAI_API_KEY=... を追加（または環境変数として設定）
   - news_nlp / regime_detector は APIキーが必須（例外を投げる）

---

## 使い方（実行コマンド）

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
    - 本番（live）では本番用設定と本番 sqlite_path を使用
    - 起動時に data/execution.pid を作成（pid_file のパスは Settings.pid_file_path で上書き可能）
    - 停止のために data/stop_requested.flag を作成するとデーモンループが検知して停止します

- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視DBを更新します
    - 停止は project_root/data/stop_requested.flag を作成することでループを終えます

- 設定・検証
  - python -m kabusys.config_setup （.env 対話式作成/更新）
  - python -m kabusys.validate_config （設定検証）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出してニュースセンチメントやレジーム判定を実行
  - 実行時に OPENAI_API_KEY の設定が必須

ログ:
- ログは標準出力（stdout）とログファイル（logs/<app_name>.log）に出力されます（kabusys.utils.logging_setup.setup_logging を使用）。
- ログレベルは環境変数 LOG_LEVEL で指定可能（デフォルト INFO）。

停止・Kill Switch:
- ExecutionEngine を強制停止させる運用ロジック:
  - KillSwitch は risk_monitor / system_monitor / trade_monitor の結果を評価して、必要なら data/kill.flag を書き込みます（Settings.kill_flag_path から参照）
  - 管理者が手動で停止したい場合は project_root/data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して正常終了します

監視 DB とペーパートレード DB の分離:
- monitoring（system/trade/risk logs）は sqlite_path（SQLITE_PATH）を使用
- ペーパートレードの Execution は PAPER_TRADING_SQLITE_PATH を使用（KABUSYS_ENV=paper_trading 時）

環境変数の主な一覧（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能で必須）
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）
- LOG_LEVEL（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（0/1）

PAPER_FILL_MODE（ペーパートレード挙動）:
- 有効値: instant | partial | never | reject（デフォルト instant）
- Settings.paper_fill_mode によって MockBrokerClient の約定挙動が変わります

---

## ディレクトリ構成（主要ファイル）

以下はソース内の主要ファイル／ディレクトリの抜粋です（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読み込みユーティリティ
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py               — ニュースを OpenAI でスコアリング
    - regime_detector.py        — マーケットレジーム判定（MA200 + マクロLLM）
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（監視用テーブル）
    - system_monitor.py
    - trade_monitor.py          — （トレード監視ロジック：ファイル参照）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py          — （アラート送信ロジック：ファイル参照）
  - execution/
    - execution_engine.py       — ExecutionEngine（取引ロジック本体：ファイル参照）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                       — 実行時に使用する（logs、DB、flag ファイル等）

（上記はコードベースの要点をまとめたものです。実際のリポジトリではさらに多くのファイル／サブモジュールがあります）

---

## 運用上の注意 / ベストプラクティス

- 本番運用時は KABUSYS_ENV=live を使用。validate_config.py を使って設定を慎重に確認してください。
- .env は決して Git 等で共有しないでください（README 内にも明記済みの通り .env をコミットしないこと）。
- OpenAI API を使う機能は外部API呼び出しのため、レート制限やコストに注意。API キーは適切に管理してください。
- 監視（monitoring）プロセスは本番 sqlite_path を使って常に書き込む設計のため、監視用 DB の権限・バックアップ戦略を検討してください。
- Kill Switch 機構は自動停止を引き起こすため、KILL_FLAG_CLEAR_ON_START の値や kill.flag の取り扱いに注意してください（本番では 0 推奨）。

---

もし README に追加してほしい具体的な内容（例: 実際の .env テンプレート、ユニットテストの実行方法、CI 設定例、Docker 化手順など）があればお知らせください。必要に応じて追記します。