# KabuSys

日本株自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、戦略研究（Research）、ポートフォリオ構築、発注実行（Execution）、監視（Monitoring）、および AI 補助モジュールを含む自動売買システムのコア部分を提供します。

---

## プロジェクト概要

主な目的は「安全に日本株の自動売買を行うための基盤機能」を提供することです。構成要素は以下の通りです。

- Execution: 発注エンジン、注文管理、リスク管理、ブローカークライアント抽象化
- Monitoring: システム稼働監視、注文ログ監視、リスク（ドローダウン・ポジション数）監視、Kill Switch
- Research: DuckDB を用いたファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- AI: ニュースセンチメント（OpenAI）による銘柄スコアリング、マクロセンチメントを用いた市場レジーム判定
- Utilities: 設定管理（`.env` 自動読み込み / ウィザード）、ロギング設定、プロセス優先度設定
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト

---

## 機能一覧

- 環境設定ウィザード（`.env` を対話式に生成・更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（`.env` と config/*.yaml の基本チェック）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動 / 停止制御
  - python -m kabusys.run_execution
  - KABUSYS_ENV により paper_trading では MockBroker を使用し DB を分離
- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）
- 監視用 SQLite（監視ログ、トレードログ、リスクログ、ダッシュボード）
  - モジュール: kabusys.monitoring.monitoring_db / MonitoringDB
- AI モジュール
  - ニュースを OpenAI で評価し ai_scores に保存（kabusys.ai.news_nlp）
  - レジーム判定（kabusys.ai.regime_detector）
- Research モジュール（DuckDB 接続を受けて計算）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン、IC、統計サマリ等
- Portfolio モジュール
  - 候補抽出、等重・スコア重み、ポジション株数計算、セクター制限、レジーム乗数
- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発・ローカル実行）

前提：
- Python 3.9+（ソース内 typing や一部モジュールを想定）
- Git リポジトリルートが存在すること（.env 自動読み込みでルート検出を使用）

1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須ライブラリ例（プロジェクトの requirements.txt がある場合はそちらを利用してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml
4. .env を作成
   - 対話式に作成する（推奨）:
     - python -m kabusys.config_setup
   - または、`.env.example` を参考に手動作成
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. 必要なディレクトリの作成
   - data/（DB・PID・flag 等）
   - logs/（ログファイル）
   - 例: mkdir -p data logs

注意:
- 自動 .env 読み込みは、プロジェクトルート（.git または pyproject.toml）を基準に行われます。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要環境変数（要・推奨）

必須（起動前にセットするか .env に記載）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション / デフォルト
- KABUSYS_ENV: execution モード（development / paper_trading / live） — デフォルト development
  - paper_trading: MockBroker を使い DB を data/paper_trading.db に分離
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG 等も指定可能）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）用
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） — run_monitoring に適用

ログ・PID・フラグ関連:
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- stop_flag: data/stop_requested.flag（手動で作成すると run_* のループを停止）

---

## 使い方（起動例）

1. ExecutionEngine を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading にすると MockBroker を使用して data/paper_trading.db に記録されます
   - 起動中に data/stop_requested.flag が作成されると安全に終了します
   - Kill スイッチは data/kill.flag（監視モジュールにより書き込まれる）で ExecutionEngine に停止シグナルを送ります

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - デフォルトは 60 秒間隔。MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能
   - 監視は Settings.sqlite_path（SQLITE_PATH）を使用して監視用テーブルを初期化します（init_monitoring_db）

3. 環境設定・検証
   - python -m kabusys.config_setup    （.env ウィザード）
   - python -m kabusys.validate_config [--strict]

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。--db で指定可能

5. AI 機能（プログラム的に）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - どちらも OPENAI_API_KEY を環境変数か引数で渡す必要があります

ログ：
- ログは logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリは自動作成）
- アプリケーション共通で kabusys.utils.logging_setup.setup_logging を使用しています

停止フロー：
- run_execution / run_monitoring は data/stop_requested.flag（プロジェクト root の data/stop_requested.flag）を監視し、存在するとループを終了します
- KillSwitch（監視コンポーネント）は重大なリスク発生時に data/kill.flag を書き込み、Execution 側がそれを検出して停止する設計です

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py         — 共通ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 / MonitoringDB
    - system_monitor.py
    - trade_monitor.py         — （トレード監視：ログ異常・滞留注文検出など、別ファイル）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （外部通知管理：LINE 等、別ファイル）
  - execution/
    - execution_engine.py      — ExecutionEngine 本体（別ファイル）
    - broker_factory.py        — Broker クライアント生成（Mock 対応）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py       — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py   — IC / 統計解析
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — マクロ + MA によるレジーム判定
  - data/                      — 実行時に生成されるファイル（DB / PID / flag）
  - logs/                      — ログファイル出力先（ログ設定で作成）

（注）上記は主要ファイルの抜粋です。実際のファイル階層はリポジトリ全体を参照してください。

---

## 実装上の注意点 / 運用メモ

- paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- monitoring の初期化（init_monitoring_db）は冪等であり、既存 DB に対してスキーマ追加（マイグレーション）を行う処理が含まれます。
- OpenAI を利用する機能は API 制限・エラーに対してリトライとフェイルセーフ（ゼロフォールバック）を実装していますが、API キーは必ず管理してください。
- ログディレクトリ作成やプロセス優先度設定はアクセス権に依存します。権限がない場合は警告が出て機能をスキップします。
- .env は機密情報を含みます。絶対に Git にコミットしないでください（config_setup で明記あり）。

---

## よく使うコマンドまとめ

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば README にサンプル .env テンプレート、Docker / systemd サービスファイル例、開発向けのテスト手順なども追加します。どの情報を優先して追加しますか？