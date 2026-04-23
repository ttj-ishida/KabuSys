# KabuSys

日本株向け自動売買システムのコアライブラリ群（kabusys）。  
このリポジトリは実運用向けのエンジン、監視、リサーチ、ポートフォリオ構築、AI 支援モジュールなどを含みます。

---

## 概要

KabuSys は以下の機能を備えたモジュール式の自動売買基盤です。

- 発注エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（DuckDB を用いたローカル分析）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- ペーパートレード用の分離された DB と Mock ブローカー
- 設定ウィザード、設定検証、紙上検証レポート生成などの CLI ツール

設計方針として、ルックアヘッドバイアスを避けるために日付参照は明示的に渡す（date.today() を直接参照しない）実装が多く、運用安全性（kill flag、ログ、優先度設定、監視）に配慮されています。

---

## 主な機能一覧

- Execution（発注）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - RiskManager によるポジション上限・ドローダウン制御
  - OrderRepository / OrderManager / Reconciler による注文管理
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス検出、データ鮮度確認
  - TradeMonitor: 注文滞留／約定異常検出（trade_logs ベース）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch / AlertManager による自動停止通知
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースセンチメント（OpenAI 使用）
  - レジーム判定（MA とマクロニュースの合成）
- ユーティリティ
  - 設定ウィザード（.env 生成）
  - 設定検証 CLI
  - Paper Trading 検証レポート生成
  - ロギングセットアップ、プロセス優先度設定ユーティリティ

---

## セットアップ手順（開発 / ローカル起動向け）

1. Python と仮想環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化してください。
     - python -m venv .venv
     - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必須ライブラリ（例）:
     - duckdb, psutil, openai
   - PyYAML は config ファイル検証で任意
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # optional（validate_config の YAML 検証）

   （requirements.txt がある場合はそれを利用してください: pip install -r requirements.txt）

3. .env の設定
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（主なもの）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（分析用）
     - SQLITE_PATH: data/monitoring.db（監視用）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR（デフォルト: INFO）
     - OPENAI_API_KEY: OpenAI を使う機能のために必要（ai.news_nlp, ai.regime_detector）
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパーブローカーの約定モード）
     - KILL_FLAG_CLEAR_ON_START: 0|1（本番で 1 は危険。起動時に kill.flag を削除）

   - 自動ロード:
     - パッケージ読み込み時にプロジェクトルートから `.env` と `.env.local` を自動読み込みします。
     - OS 環境変数が優先されます。
     - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ
   - デフォルトでは `data/`、`logs/` を作成します。
   - 例:
     - mkdir -p data logs

---

## 使い方（起動と CLI）

基本的にモジュールを Python -m で実行します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を high に設定（psutil を利用）
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_db（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動前に data/stop_requested.flag が存在する場合は起動しない
    - 強制停止は data/stop_requested.flag または KillSwitch による data/kill.flag

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を指定（デフォルト 60 秒）
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を用いてログする
    - data/stop_requested.flag を置くとループ終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（プログラム内 API）
  - ニュースのスコア化:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key を渡すか、環境変数 OPENAI_API_KEY を設定
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止・Kill フラグ:
- data/stop_requested.flag: 実行中の run_monitoring / run_execution のメインループを穏やかに終了させるために利用
- data/kill.flag: KillSwitch が立てるフラグ。ExecutionEngine は起動時や実行中にこのフラグを検出して停止する

ログ:
- logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、既定 30 日保持）
- コンソール出力は stdout に書かれます

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用関係:
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: MockBroker を使用し paper DB に記録（本番 DB と分離）
  - live: 本番動作（注意深く設定してください）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（data/paper_trading.db）
- DUCKDB_PATH: 分析用 DuckDB（data/kabusys.duckdb）
- OPENAI_API_KEY: AI モジュール利用時に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパーブローカー動作）

設定自動ロード:
- .env / .env.local がプロジェクトルートにある場合、自動で読み込みます（OS 環境変数が優先）
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python パッケージは `src/kabusys` 以下にあります。主な構成:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込みロジック、.env 自動ロード
  - config_setup.py
    - .env 作成の対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 発注に関連する主要コンポーネント（エンジン、ブローカー抽象、リスク管理）

  - monitoring/
    - monitoring_db.py
      - SQLite ベースの監視ログ永続化（テーブル初期化・CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
      - 監視関連の各種モニタと KillSwitch / アラート管理
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - 提案銘柄選定・重み付け・株数算出・セクター制約など
  - research/
    - factor_research.py
    - feature_exploration.py
    - DuckDB を使ったファクター計算・特徴量評価
  - ai/
    - news_nlp.py
    - regime_detector.py
    - OpenAI を使ったニュースセンチメントとレジーム判定
  - data/
    - pipeline.py, stats.py (DuckDB 連携・統計ユーティリティなど)
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
      - 統一的なログ構成（stdout + 日次ローテートファイル）
    - process_priority.py
      - psutil を使ったプロセス優先度 / CPU affinity 設定

- data/
  - デフォルトの DB / flag / pid ファイルを置く場所（実行時に自動作成されます）
  - 例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid

- logs/
  - ログファイル（logs/execution.log, logs/monitoring.log など）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を確実に行ってください（validate_config 参照）。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（自動で kill.flag をクリアしてしまうため）。
- Paper Trading は本番 DB と分離されていますが、設定ミスで本番 DB を使わないよう環境変数を確認してください。
- OpenAI API を利用する機能はネットワークの影響を受けます。API キーとリトライ挙動に注意してください。
- ログディレクトリの作成に失敗した場合、ファイル出力はスキップして stdout のみになります。権限を確認してください。

---

## 開発者向け補足

- テストやユニットテストでは、環境読み込みを抑止するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- AI 関連の外部呼び出しはテストでモック化しやすいように設計されています（内部の API 呼び出し関数を差し替える）。
- DuckDB / SQLite のスキーマやマイグレーションは monitoring_db.init_monitoring_db 等に組み込まれています。

---

必要に応じて README の内容をプロジェクトの実際の運用ポリシーや CI/CD、デプロイ手順（systemd 単位ファイル / コンテナ化手順など）に合わせて補足してください。質問や特定の起動方法のテンプレートが必要であれば教えてください。