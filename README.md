# KabuSys

日本株向けの自動売買・リサーチ基盤のコアライブラリ群と起動スクリプト群です。  
本リポジトリは、注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI によるニュースセンチメント評価などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムの主要コンポーネントを集めたモジュール群です。主な設計思想は以下の通りです。

- 発注ロジックと監視ロジックを分離して運用可能（Execution / Monitoring）。
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による切替）。
- DuckDB を使ったオフラインリサーチ（ファクター計算、特徴量探索）。
- OpenAI（gpt-4o-mini）を利用したニュース NLP によるセンチメント生成（オプション）。
- 簡易的な Kill Switch / リスク監視・アラートの仕組みを内包。

この README では、主要な機能、セットアップ手順、使い方、プロジェクトのディレクトリ構成を説明します。

---

## 機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて本番または paper_trading を分離）
  - run_monitoring: SystemMonitor のポーリングループを起動（監視ログを永続化）
- 設定管理
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - Settings クラスによる集中設定取得
- 監視
  - MonitoringDB: SQLite ベースの監視用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
- 発注関連（execution パッケージ）
  - Broker クライアントのファクトリ、OrderManager、RiskManager、ExecutionEngine 等（起動スクリプト経由で利用）
- ポートフォリオ構築
  - 銘柄選定、重み付け（等金額・スコア加重）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・統計サマリー
  - DuckDB との連携でオフライン集計
- AI（任意）
  - news_nlp: raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector: ETF とマクロセンチメントを合成して日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

---

## セットアップ手順

前提: Python 3.9+ を想定しています。仮想環境の利用を推奨します。

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール  
   本プロジェクトが使っている主な外部依存:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（validate_config で YAML 検証を行う場合）
   - (その他、プロジェクトで requirements.txt を用意している場合はそれに従ってください)

   例:
   - pip install duckdb psutil openai PyYAML

4. データ / ログ ディレクトリの準備
   - data/ と logs/ を作成します（多くのモジュールが自動で作成しますが事前に用意しておくと安全です）
   - mkdir -p data logs

5. .env の作成
   - python -m kabusys.config_setup を実行して対話式に .env を生成します。
   - あるいは手動で .env を作成してください（.env は絶対に Git にコミットしないでください）。

   必須の環境変数例（.env で設定）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   推奨/よく使う変数:
   - KABUSYS_ENV=development|paper_trading|live
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - LOG_LEVEL=INFO
   - OPENAI_API_KEY=...  （AI 機能を使う場合）

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告やエラーが出たら .env / config/*.yaml を見直してください。
   - --strict オプションで警告も FAIL 扱いにできます。

注意:
- .env の自動ロードはデフォルトで有効です。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用 (KABUSYS_ENV=live) の際は必須環境変数や LINE 通知設定等を特に注意してください。

---

## 使い方

主要な起動・ユーティリティコマンドを示します。いずれもプロジェクトルート（pyproject.toml/.git を含むルート）で実行してください。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注実行）
  - python -m kabusys.run_execution
  - 動作概要:
    - 起動時にプロセス優先度を high に設定（可能なら）
    - KABUSYS_ENV が paper_trading の場合は専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して発注を模擬
    - 停止は data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を書き込むことでトリガーされます
    - 実行時の PID は data/execution.pid に書き込まれます

- Monitoring を起動（常時監視ループ）
  - python -m kabusys.run_monitoring
  - 動作概要:
    - Settings.sqlite_path を使用して監視ログを永続化（監視は環境に関係なく本番 sqlite_path を使用）
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数をオーバーライド可能（正の整数）
      - 例: export MONITOR_POLL_INTERVAL=30
    - 監視ループの停止はプロジェクトルートの data/stop_requested.flag ファイルの存在で検知して終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ系（プログラムから利用）
  - ニュース NLP（関数）: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定（関数）: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続を開いてこれらの関数を呼ぶことで ai_scores / market_regime テーブルへ書き込みます。
  - 注意: OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

ログ:
- logs/<app_name>.log に日次ローテートでログが書き出されます（例: logs/execution.log, logs/monitoring.log）。
- 標準出力にも同様のログが出ます。ログ出力設定は kabusys.utils.logging_setup.setup_logging 経由で行われます。

停止・Kill Switch:
- 手動停止: data/stop_requested.flag を作成すると run_* スクリプトのループが終了します。
- 自動停止（Kill Switch）: RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側が検出して停止します。KillSwitch.clear() で削除可能です。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされます（本番では 0 推奨）。

権限:
- set_process_priority はプラットフォームにより権限が必要な場合があります（Linux で負の nice 値を設定する等）。アクセス拒否時は警告を出してスキップします。

---

## ディレクトリ構成

主要ファイル・ディレクトリの簡単な説明を示します（ソースは src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - config.py                  — Settings クラス、.env 自動ロードロジック
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py              — ニュースを LLM でスコアリングして ai_scores に書き込むロジック
    - regime_detector.py       — 市場レジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite ベースの監視永続化層
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （trade の監視ロジック）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag の生成/検査ユーティリティ
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - alert_manager.py         — （アラート送信ロジック）
  - execution/
    - execution_engine.py      — ExecutionEngine 実行ロジック
    - broker_factory.py        — BrokerClient の生成
    - order_manager.py         — 発注管理
    - order_repository.py      — 永続化
    - reconciler.py            — ブローカと DB の整合処理
    - risk_manager.py          — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数計算・キャップ処理
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum, volatility, value）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー等
  - data/                      — 実行時に生成される DB / フラグファイル等（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）
  - logs/                      — ログ出力ディレクトリ（デフォルト logs/）
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

注: 一部ファイル（trade_monitor.py, alert_manager.py など）はここでは割愛しましたが、実装によりさらに機能が提供されます。

---

## 追加情報 / 注意事項

- .env は必ず機密情報を含むため Git にコミットしないでください。
- KABUSYS_ENV=live の場合、本番発注が行われるため十分に設定・検証してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB と分離されます。
- OpenAI を使用する機能は API 利用料がかかる点に注意してください。OPENAI_API_KEY を環境変数にセットするか関数呼び出し時に引数で渡してください。
- DuckDB / SQLite のスキーマ変更は init_monitoring_db がマイグレーション処理を簡易的に行いますが、本番ではバックアップを必ず取得してください。

---

問題・改善提案・機能追加などがあれば教えてください。README を運用方針や社内手順に合わせて調整します。