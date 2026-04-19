# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README。  
この README はソースツリー（src/kabusys/...）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・運用支援を目的としたモジュール群です。主な機能群は次の通りです。

- 注文実行エンジン（ExecutionEngine / ブローカークライアント抽象化）
- 監視（System / Trade / Risk を監視してアラート・Kill Switch を管理）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ決定）
- リサーチ（ファクター計算、特徴量探索、IC計算など）
- AI 補助機能（ニュース NLP によるセンチメント評価・市場レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針の一部:
- DuckDB を分析用 DB、SQLite を監視／履歴用 DB として利用
- Paper Trading（シミュレーション）は本番 DB と分離（別 SQLite）
- 環境設定は .env をベースにし、起動時に自動読み込み（任意で無効化可能）
- OpenAI 等外部 API を用いる箇所はフェイルセーフ設計（失敗時は安全側にフォールバック）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動（KABUSYS_ENV により MockBroker への切替あり）
  - Paper Trading は専用 DB (`data/paper_trading.db` など) に分離
  - PID ファイル管理（デフォルト `data/execution.pid`）
  - `data/stop_requested.flag` により外部から停止可能

- run_monitoring.py
  - SystemMonitor のポーリングループを起動（デフォルト間隔 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能
  - 監視ログは SQLite（monitoring DB）へ永続化（`monitoring_db.init_monitoring_db`）

- monitoring パッケージ
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch（条件到達時に `data/kill.flag` を書き込み、Execution を止める）
  - MonitoringDB（SQLite に対する CRUD を集中管理）

- portfolio パッケージ
  - 候補選定、重み計算、セクター制限、ポジションサイズ計算（純粋関数）

- research パッケージ
  - ファクター計算（momentum/value/volatility 等）
  - 将来リターン計算、IC、統計サマリー

- ai パッケージ
  - news_nlp: raw_news を集約し OpenAI でセンチメントを取得して ai_scores に書き込む
  - regime_detector: ETF の MA とマクロニュースを統合して市場レジーム判定

- utils
  - logging_setup: 一貫したログ設定（stdout + 日次ローテートファイル）
  - process_priority: クロスプラットフォームでプロセス優先度 / CPU affinity を設定

- tools
  - paper_verification_report: ペーパートレード DB から検証レポート（稼働率・成功率・レイテンシ等）を出力

---

## 前提・要件

- Python 3.8+
- 推奨ライブラリ（プロジェクトの requirements.txt を確認してください）
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（設定ファイル検証で使用）
- ファイルシステムへの書き込み権限（`data/`、`logs/` 等）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は上記「前提ライブラリ」を個別に pip install してください

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, PAPER_FILL_MODE（instant/partial/never/reject）など

   自動読み込みはデフォルトで有効。テスト等で無効にする場合は:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

5. 必要ディレクトリの作成（通常はスクリプト実行時に自動作成されますが、手動で用意する場合）
   - mkdir -p data logs

---

## 使い方（起動・運用）

- 実行エンジン起動（本番/ペーパートレードを環境で切替）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、paper_trading 用 SQLite に記録します（本番 DB と分離）。
    - 実行中に外部から停止したい場合はプロジェクトルートの data/stop_requested.flag を作成してください（`touch data/stop_requested.flag`）。エンジンは検出後に停止します。
    - PID ファイルはデフォルト `data/execution.pid` に書かれます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視は Settings に従って sqlite_path / duckdb_path を利用します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計です（監視ログを本番 DB に書くため）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パス指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先使用。

- AI 関連（OpenAI API キー必要）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を渡して呼び出します
  - 簡易 CLI は提供していませんが、スクリプトやスケジューラから呼び出すことを想定

- Kill Switch と停止フロー
  - RiskMonitor 等が条件に達すると KillSwitch が `data/kill.flag` を書き込みます
  - ExecutionEngine は起動時に kill flag をクリアするオプション（KILL_FLAG_CLEAR_ON_START）がありますが、本番ではクリアしないことを推奨します
  - kill.flag が書かれると運用者は内容を確認し、必要に応じて手動でファイルを削除・対処します

---

## 環境変数（主な一覧）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- LOG_DIR: ログ出力先（default: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: instant|partial|never|reject（paper trading の約定モード）
- KILL_FLAG_CLEAR_ON_START: 1 にすると Execution 起動時に `data/kill.flag` を自動クリア（注意：本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動読込を無効化

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主要ファイル／モジュールのツリー（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数／.env 読み込みと Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - __init__.py
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py             — SQLite テーブル初期化・CRUD
    - system_monitor.py
    - trade_monitor.py             — （コード省略部分に実装想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py             — （アラート送信のラッパー実装想定）
  - execution/                      — Execution 系エンジン、オーダー管理（実装一部参照）
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                           — （データファイル: sqlite/duckdb 等を配置する想定）
  - logs/                           — ログファイル出力先（デフォルト）

（実際のリポジトリではさらにファイル・サブパッケージがあります。上は主要なモジュールの抜粋です。）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config の WARN を無視しないでください。
- .env は機密情報を含むため決して Git にコミットしないでください。
- Kill Switch（data/kill.flag）や stop フラグ（data/stop_requested.flag）は運用上重要です。自動クリア設定（KILL_FLAG_CLEAR_ON_START）は本番では 0 を推奨します。
- OpenAI 等外部 API を利用する機能は API 制限・課金に注意し、適切なエラーハンドリング・レート制限を設定してください（実装はリトライやバックオフを含みますが、運用監視は必須です）。
- 監視は monitoring DB（SQLite）に記録されます。バックアップ／ローテーションやディスク容量管理をしてください。

---

## 追加情報

- ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一されます。`LOG_DIR` 環境変数または引数でログ出力先を変更できます。
- process_priority は psutil を使います。権限不足で設定できない場合は WARNING を出して続行します。
- DuckDB を用いた分析/リサーチ系の SQL は DuckDB 接続を受け取る設計です。データ投入後に分析ジョブとして呼び出してください。

---

この README はコードベースの主要点をまとめたものです。追加で「導入手順（OS別）」「実行例（systemd/cron の設定例）」「テストの実行方法」などの具体的な運用ドキュメントが必要であれば教えてください。