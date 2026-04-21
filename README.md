KabuSys — 日本株自動売買システム
=============================

このドキュメントは本リポジトリ内の主要スクリプト・モジュールの概要、セットアップ、使い方、およびディレクトリ構成をまとめた README です。  
コードは Python パッケージとして設計されており、Execution Engine（発注系）・Monitoring（監視系）・Portfolio / Research / AI 等のコンポーネントで構成されています。

プロジェクト概要
----------------
KabuSys は日本株の自動売買システムです。主な機能は次のとおりです。

- 発注実行（ExecutionEngine）
  - 本番・ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントの抽象化（MockBrokerClient を含む）
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）
- 監視（Monitoring）
  - システム状態・データ鮮度・トレードログ・リスク監視
  - Kill Switch（条件に応じて実行系停止フラグを発行）
  - ロギングとアラート連携
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限適用、レジーム補正
- リサーチ（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索、将来リターン・IC 計算、統計サマリー
- AI（OpenAI）連携
  - ニュースを LLM でスコアリング（news_nlp）
  - マーケットレジーム判定（regime_detector）
- 工具（tools）
  - Paper Trading の検証レポート生成スクリプト等
- ユーティリティ
  - 設定（.env）ウィザード、設定検証、ログ設定、プロセス優先度設定等

特徴一覧
--------
- 環境切替（development / paper_trading / live）により挙動を分離
  - paper_trading では MockBrokerClient を用い、Paper 用 SQLite（デフォルト data/paper_trading.db）へ記録
- DuckDB を分析用 DB、SQLite を監視・注文履歴用 DB として併用
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価とレジーム判定（API キー必須）
- ログは stdout と日次ローテートファイル（logs/<app>.log）へ出力
- Kill Switch / stop flag による安全停止機構
- 設定用ウィザード（.env 作成）および検証 CLI を提供

セットアップ手順
----------------
以下は一般的なセットアップ手順の例です。

1. Python 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存関係のインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な依存例（最低限）:
     - pip install duckdb psutil openai
   - optional:
     - pip install PyYAML  （config/*.yaml の検証に必要）

   ※ 実際の依存パッケージはプロジェクト配布物（pyproject.toml / requirements.txt）を参照してください。

3. 環境変数の設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数の例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY （AI を使う場合）
   - 主要な環境変数（デフォルト値や説明）:
     - KABUSYS_ENV: development | paper_trading | live （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR
     - LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 動作の挙動）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

5. DB の初期化
   - 監視用 SQLite（monitoring）は起動スクリプト内で init されます（init_monitoring_db が冪等でテーブル作成）
   - DuckDB 用のテーブル（prices_daily 等）は別途データ投入スクリプトを用意して初期化してください（本リポジトリ内の pipeline 等を参照）

使い方（主要コマンド）
--------------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用してペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行中の停止:
    - data/stop_requested.flag を作成すると run_execution は起動済みスレッドに停止を要求します。
    - Monitoring 側の KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（設定次第で起動時に自動クリアできる）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - run_monitoring は settings.sqlite_path を使用して監視データを永続化します（環境にかかわらず本番 sqlite_path を使用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - ai モジュールは Python API を提供:
    - from kabusys.ai import score_news
      - score_news(conn, target_date, api_key=None)
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY 環境変数または引数で渡す api_key）が必要です。

ログ・停止制御
--------------
- ログ
  - デフォルトは logs/<app_name>.log（例: logs/execution.log / logs/monitoring.log）。stdout（コンソール）にも出力されます。
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。

- 停止フラグ
  - data/stop_requested.flag: run_* スクリプトが外部からの即時停止（ポーリングループを抜ける）を検知するために参照します。
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナル（安全停止）を送ります。
  - PID ファイル: data/execution.pid（ExecutionEngine が PID を書き込むパス。Settings.pid_file_path で変更可能）

設定の自動ロードについて
-----------------------
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
- 自動ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要モジュールと役割の概観（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定の読み込み・検証（Settings クラス）
  - config_setup.py           — .env 対話式ウィザード（CLI）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py         — Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成 CLI
  - execution/                 — 発注関連（Engine, OrderManager, RiskManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（テーブル初期化・CRUD）
    - system_monitor.py       — システム状態・データ鮮度チェック
    - trade_monitor.py        — 注文ログ監視（stale / anomaly 検出）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch（kill.flag 書込み）
    - monitoring_engine.py    — 各モニタのオーケストレーション
    - alert_manager.py        — （アラート送信ラッパー: LINE など）
  - portfolio/
    - portfolio_builder.py    — 候補選定・スコアソート
    - position_sizing.py      — 発注株数算出、aggregate cap 処理
    - risk_adjustment.py      — セクター上限 / レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等ファクター計算（DuckDB 使用）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores へ書き込み
    - regime_detector.py      — マーケットレジーム判定（ma200 + LLM）
  - utils/
    - logging_setup.py        — ロギングの初期化（stdout + 日次ファイルローテート）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/                     — デフォルト DB・フラグ・PID 等を置く想定ディレクトリ（data/monitoring.db 等）

注意事項・運用上のヒント
-------------------------
- 本番運用時は KABUSYS_ENV=live に設定し、.env 内の値を厳重に管理してください。
- KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険（kill flag が自動クリアされる）。本番では 0 を推奨します。
- OpenAI API 呼び出しはネットワーク/料金の観点から注意してください。API キーは安全に管理してください。
- DuckDB のテーブル（prices_daily / raw_financials など）は事前にロードしておく必要があります（research, ai モジュールが依存）。
- ログディレクトリや data/ ディレクトリは起動時に自動作成されますが、パーミッション等は事前に確認してください。

サポート / 拡張
----------------
- 新しいブローカ実装は execution/broker_factory 経由で追加可能です。
- AI モジュールのモデルやプロンプトは ai/news_nlp.py / ai/regime_detector.py を調整してください。
- 追加の監視ルールやアラート送信先（Slack / PagerDuty 等）は monitoring/alert_manager を拡張して実装できます。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

この README はソースコードの主要部分を元に記述しています。実運用にあたっては pyproject.toml / requirements.txt（ある場合）や運用手順書を参照し、テスト環境で十分に検証してください。必要であれば README に追記したい項目（デプロイ手順、CI、詳細な DB 初期化方法など）を教えてください。