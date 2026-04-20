# KabuSys

日本株自動売買システムの一部コードベース。環境設定ウィザード、設定検証、監視プロセス、ExecutionEngine 起動スクリプト、ポートフォリオ構築、リサーチ・AI 周りのユーティリティなどを含みます。

以下はこのリポジトリに含まれる主要機能、セットアップ手順、使い方、およびディレクトリ構成の概要です。

---

## プロジェクト概要

KabuSys は日本株自動売買向けに設計されたモジュール群です。主な機能は次の通りです。

- ExecutionEngine（発注エンジン）起動・停止の管理（本番 / ペーパートレード切替）
- 監視（Monitoring）プロセス：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期チェックしアラート・Kill Switch を管理
- .env 対応の環境設定ウィザードと事前設定検証ツール
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析
- AI モジュール：ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- Paper Trading 検証レポート生成ツール

設計方針として、DB（DuckDB/SQLite）をデータストアに使い、外部 API キーは環境変数経由で注入します。ペーパートレード時は本番 DB と分離して専用 SQLite を使用します。

---

## 機能一覧（抜粋）

- 環境設定ウィザード: python -m kabusys.config_setup  
  - 対話形式で .env を生成 / 更新
- 設定検証: python -m kabusys.validate_config  
  - .env / config/*.yaml / 必須環境変数等をチェック
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution  
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring  
  - 定期的に SystemMonitor.check_once() を実行、MONITOR_POLL_INTERVAL で間隔調整可
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report  
  - 指定期間の稼働率・注文成功率・レイテンシ等を集計して判定を出力
- ポートフォリオ構築ユーティリティ:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（単元株丸め、リスク・上限管理）
  - セクターキャップ適用、レジーム乗数
- AI:
  - kabusys.ai.news_nlp.score_news — raw_news を LLM に投げセンチメント評価し ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime — ma200 とマクロニュースで市場レジーム判定
- ログ設定ユーティリティ: setup_logging（Stream + 日次ローテートファイル）

---

## 必須 / 推奨環境変数（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB / ログ:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパー用、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR（ログディレクトリ、デフォルト: logs）
- OpenAI を使う機能:
  - OPENAI_API_KEY（news_nlp / regime_detector が必要とする）
- その他:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Settings 経由）

注意: .env に関する自動読み込みはプロジェクトルートが特定できる場合に行われます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要なインストール例（最低限）:
     - pip install duckdb psutil openai
   - YAML 関連の検証を利用する場合:
     - pip install PyYAML

3. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザード後に .env が生成されます（Git にコミットしないでください）

4. 設定の検証
   - python -m kabusys.validate_config
   - 問題があれば指摘が出るので修正する
   - --strict を付けると警告もエラー扱いになります

5. データディレクトリの用意
   - デフォルトでは `data/` 配下に DB や PID/flag ファイルが作られます。必要に応じて書き込み権限を確認してください。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動する（ローカル・フォアグラウンド）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
    - _STOP_FLAG（data/stop_requested.flag）が存在すると起動しません。実行中もこのファイルを作成すると停止します。
    - 起動時に pid ファイル（デフォルト: data/execution.pid）を書きます。

- Monitoring を起動する（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（デフォルト: data/monitoring.db）を用いて常に本番用の監視 DB を参照します（run_monitoring の挙動）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH で指定しても可）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

---

## 実行時の挙動と運用上の注意

- Kill Switch / stop フラグ
  - monitoring 側や KillSwitch は data/kill.flag（Settings.kill_flag_path）や data/stop_requested.flag を使って ExecutionEngine の停止や起動制御を行います。
  - KillSwitch はリスク（ドローダウンやポジション上限）に基づき kill.flag を書き込み、ExecutionEngine 側でそれを検知して停止させる運用を想定しています。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します（安全のため）。

- ロギング
  - setup_logging により stdout（StreamHandler）とログディレクトリ（TimedRotatingFileHandler 日次ローテーション、デフォルト logs/）へ出力します。
  - 環境変数 LOG_DIR、LOG_LEVEL で調整できます。

- データベース
  - DuckDB: 分析用途（prices_daily / raw_financials 等）
  - SQLite: 監視ログ（monitoring.db）・Paper Trading（paper_trading.db）
  - monitoring_db.init_monitoring_db() はテーブル作成や簡易マイグレーション（カラム追加）を行います（冪等）

- AI モジュール（OpenAI）
  - OPENAI_API_KEY を環境変数に設定するか、関数呼び出し側で渡す必要があります。
  - API 呼び出しはリトライやフェイルセーフ（失敗時にはスコアを 0 やスキップ）を備えています。
  - モデルは gpt-4o-mini（コード中の定義）を想定しています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成（このリポジトリの抜粋に基づく）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
  - execution/                 — ExecutionEngine, BrokerFactory, OrderManager 等（参照あり）
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時に作成されることが期待されるディレクトリ（DB / flag / pid）

（上記は抜粋で、実際のリポジトリにはさらにモジュールやサブパッケージが存在する可能性があります）

---

## 開発者向けメモ / 実装上のポイント

- Settings クラスは .env ファイルと OS 環境変数を統合します。プロジェクトルート（.git または pyproject.toml）を基準に自動で .env を読み込みます。
- Monitoring と Execution は stop フラグ（stop_requested.flag）を使って優雅に停止できます。手動で停止したい場合はこのファイルを作成してください。
- run_execution は KABUSYS_ENV により本番/ペーパーの DB を切り分けますが、run_monitoring は常に本番の sqlite_path（monitoring.db）を参照します（設計上の注意）。
- AI 系処理は外部 API に依存するため、API キーとレート制限に注意してください。エラー時はフェイルセーフで進める実装になっています。

---

## 付録：よく使うコマンド例

- .env を作る（対話ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書いてほしい追加情報や、特定の運用手順（systemd ユニット、Docker 化、CI/CD やテストの設定など）があれば教えてください。必要に応じて起動例の systemd ユニットやコンテナ化手順も作成します。