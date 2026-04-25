# KabuSys

日本株自動売買システムのライブラリ兼起動スクリプト群。

このリポジトリは、戦略研究・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視（Monitoring）・ペーパートレード検証・AI（ニュースNLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的のために設計されています。

- DuckDB / SQLite 上でのデータ処理・研究（ファクター計算、将来リターン、特徴量解析）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine による発注管理（本番 / ペーパートレード分離）
- 監視コンポーネント（システム状態、注文・リスク監視、Kill Switch）
- AI を用いたニュースのセンチメントスコアリング（OpenAI）
- ペーパートレード検証レポート生成

設計上の特徴：

- 本番 DB とペーパートレード DB の分離（KABUSYS_ENV=paper_trading 時）
- .env による設定管理 + 対話式ウィザード / 検証ツール付き
- ログは stdout と日次ローテートファイル（logs/）に出力
- フェイルセーフ設計（API 失敗時は安全値で継続する等）

---

## 機能一覧

主な機能（モジュール別）

- 実行 / 監視
  - run_execution.py: ExecutionEngine の起動スクリプト（本番 / ペーパートレード切替対応）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整）

- 設定管理
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: 環境変数と config/*.yaml の検証 CLI
  - config.py: Settings クラス（環境変数のパース・デフォルト値）

- 監視
  - monitoring/*: system_monitor, trade_monitor, risk_monitor, monitoring_engine, monitoring_db, kill_switch, alert_manager など
  - データ永続化: monitoring_db.py（SQLite スキーマと MonitoringDB クラス）

- 発注 / 実行関連（execution/*）
  - BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等（エンジン起動・注文管理・リスク管理）

- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重・スコア重み計算、セクター制限、レジーム乗数、ポジションサイズ決定

- 研究（research/*）
  - factor_research.py: momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリー等

- AI（ai/*）
  - news_nlp.py: raw_news を OpenAI に渡して銘柄ごとのセンチメント（ai_scores）を作成
  - regime_detector.py: ETF ma200 とマクロニュースを組み合わせた市場レジーム判定

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート出力（稼働率・注文成功率・レイテンシ等）

- ユーティリティ
  - utils/logging_setup.py: ログ設定ユーティリティ
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

---

## 前提 / 必要要件

- Python 3.9+（typing の一部機能を使用）
- 必要パッケージ（最低限）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config の YAML 検証を使う場合）

インストール例:

pip install duckdb psutil openai pyyaml

（requirements.txt がある場合はそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo-root>

2. 必要パッケージをインストール

   pip install duckdb psutil openai pyyaml

3. .env を用意（対話式ウィザード推奨）

   python -m kabusys.config_setup

   ウィザードは .env を生成します。重要な必須項目:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な環境変数（主なもの）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能利用時必須）
   - LOG_LEVEL（デフォルト: INFO）
   - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0 推奨）

4. 設定検証（起動前に推奨）

   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要なら）

   mkdir -p data logs

6. (オプション) 起動前に既存の kill.flag を確認／クリア

   # kill.flag を自動クリアしない設定が推奨（本番で誤操作を防ぐ）
   rm -f data/kill.flag
   rm -f data/stop_requested.flag

---

## 使い方

起動スクリプト・ツールの主な使い方を示します。

- ExecutionEngine を起動

  # 本番 / 開発 / ペーパートレードは KABUSYS_ENV に従う
  python -m kabusys.run_execution

  実行時の挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - エンジンは daemon スレッドで run_session を実行。外部からデータ/kill.flag を書いて停止させる仕組みがあります。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で指定可能）

- Monitoring を起動

  python -m kabusys.run_monitoring

  - SystemMonitor を周期的に実行します（既定 60 秒）。
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。0 以下や不正値は無視されデフォルト 60 秒を使用します。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視は環境にかかわらず本番 sqlite_path を参照する設計）。
  - 停止: data/stop_requested.flag が存在するとループを終了します。

- ペーパートレード検証レポート生成

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

  出力内容:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等。PASS/FAIL 判定。

- AI 関連（プログラム内 API）

  - ニュースセンチメントを付与して ai_scores に書き込む:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定を行い market_regime テーブルへ書き込む:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  注意:
  - OpenAI API を使う機能は OPENAI_API_KEY が必須（関数呼び出し時に api_key 引数で指定可能）。
  - API エラーはリトライやフェイルセーフ（0.0）で処理される設計です。

- ログ
  - デフォルトは logs/<app_name>.log（app_name は起動時に "execution" / "monitoring" 等）。
  - 標準出力とファイルの両方に出力。ログディレクトリは環境変数 LOG_DIR で変更可能。

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine を停止させます（監視が発動）。KillSwitch.clear() または手動で該当ファイルを削除してクリアしてください。
  - data/stop_requested.flag を置くと起動中の run_monitoring / run_execution が検知して停止します（外部停止シグナル）。

---

## 主要設定項目（要点のみ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用上重要:
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: mock ブローカー / data/paper_trading.db を使用
  - live: 実際に発注が行われる想定（注意して使用）
- OPENAI_API_KEY: AI 機能で必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（ペーパー時に使用）
- LOG_LEVEL, LOG_DIR

---

## ディレクトリ構成（主なファイル・モジュール）

リポジトリの主要な（src/kabusys 以下）構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI でセンチメント）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロニュース）

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + MonitoringDB
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文関連監視（滞留注文・価格異常等）※実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch（flag ファイル）
    - monitoring_engine.py   — 各 monitor を束ねて運用
    - alert_manager.py       — 通知管理（LINE 等。実装に依存）
  
  - execution/
    - broker_factory.py
    - execution_engine.py
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

  - data/                     # 実行時に使うデータフォルダ（logs とは別）
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード時)
    - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

---

## 開発・運用上の注意

- 本番（KABUSYS_ENV=live）での起動は十分に注意して行ってください。validate_config.py の警告を必ず確認します。
- kill.flag / stop_requested.flag の扱いに注意（特に本番）。KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。
- AI 機能は外部 API（OpenAI）に依存します。API キー管理・利用料・レート制限に注意してください。
- DB マイグレーションは monitoring_db.init_monitoring_db にて最低限を実行しますが、スキーマ変更時は注意が必要です。
- logging_setup は起動スクリプトから必ず呼び出して一貫したログ運用をしてください（例: setup_logging(app_name="execution")）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動
  python -m kabusys.run_execution

- Monitoring 起動
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

もし README に追記してほしい項目（例: API 使用例、設定ファイルテンプレート、詳しい監視/アラート条件やテーブル定義のドキュメント等）があれば教えてください。必要に応じて具体例やサンプル .env / SQL スキーマの抜粋を追加します。