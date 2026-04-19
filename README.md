# KabuSys

日本株向け自動売買システムのコアライブラリ（モジュール群）。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース/NLP）連携などの主要機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主目的としたモジュール群です。

- 日次 / リアルタイムの取引実行（ExecutionEngine、OrderManager、RiskManager 等）
- システム稼働・データ鮮度・注文フローの監視（Monitoring）
- ポートフォリオ構築（銘柄選定・重み付け・株数計算・セクター制約など）
- リサーチ向けファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュースを用いた NLP スコアリング & マクロレジーム判定（OpenAI 経由）
- Paper Trading 用の分離 DB と検証レポート生成ツール

設計方針の要点:
- 環境変数 / .env による設定管理
- Paper Trading と Live を明確に分離（DB も分離）
- LLM 呼び出しは失敗を許容してフェイルセーフ化
- ログや監視データの永続化は SQLite / DuckDB を利用

---

## 主な機能一覧

- Execution
  - 実行エンジンの起動スクリプト（run_execution.py）
  - Paper Trading 時は MockBrokerClient を使用し DB を分離
  - プロセス優先度設定、PID ファイル管理、停止フラグ検出
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch（条件を満たせば data/kill.flag を書き込む）
  - run_monitoring.py によるポーリングループ
- Portfolio
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB 上でファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（情報係数）、ファクター統計
- AI（OpenAI）
  - ニュース記事のセンチメント評価（ai.news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- 開発支援
  - 対話型 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## セットアップ手順（ローカル開発用）

前提: Python 3.10+（typing の | を使用しているため）を想定。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそちらを使用してください。）

4. 初期設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example があれば参考に）

5. 設定検証
   - python -m kabusys.validate_config
   - 本番想定の厳密チェックは:
     - python -m kabusys.validate_config --strict

6. 初回 DB 作成
   - run_execution / run_monitoring 起動時に必要なテーブルは自動作成されます。
   - DuckDB / SQLite のデフォルトパスは data/ 配下（下記参照）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（デフォルト値を併記）:
- KABUSYS_ENV — 実行環境。値: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）に必要
- PAPER_FILL_MODE — paper_trading 時の執行モード（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

停止・管理フラグ等:
- data/stop_requested.flag — run_monitoring / run_execution が存在を検出すると順次停止
- data/kill.flag — KillSwitch が検出対象。ExecutionEngine に停止シグナルを送る（書き込みは KillSwitch）

注:
- .env は自動で読み込まれます（プロジェクトルートの .env / .env.local）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（よく使うコマンド）

- 環境ファイル作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - Paper Trading の場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行時は data/execution.pid に PID を書き、data/stop_requested.flag を置くと停止します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を秒で上書き:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視処理は常に本番 sqlite_path を使用（監視は環境に依存しない）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定してから、対応関数をスクリプトや別プロセスから呼び出します。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ際に api_key 引数も渡せます。

ログ:
- デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション・30日保持）および stdout 出力。
- ログディレクトリは環境変数 LOG_DIR で変更可能。

停止方法:
- 外部から停止したいときは data/stop_requested.flag を作成してください（両起動スクリプトが検出して終了します）。
- KillSwitch による自動停止は data/kill.flag によるシグナルです（KillSwitch が発動するとファイルを書きます）。

---

## 主要モジュール / API（簡単な説明）

- kabusys.config.Settings
  - 環境変数の取得・検証を行うクラス。アプリ内で settings = Settings() を使って参照。

- run_execution.py
  - ExecutionEngine を組み立ててバックグラウンドスレッドで run_session を実行する起動スクリプト。
  - Paper Trading は専用 sqlite を使用。

- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト。MONITOR_POLL_INTERVAL で制御。

- kabusys.monitoring.monitoring_db.MonitoringDB
  - SQLite に対する永続化レイヤ。テーブル初期化やログ書き込み用のユーティリティを提供。

- kabusys.portfolio.*
  - ポートフォリオ構築用の純粋関数群（選定、重み付け、株数算出、セクター制限、レジーム乗数）。

- kabusys.research.*
  - DuckDB を入力にファクター計算・将来リターン計算・IC・統計サマリーを提供。

- kabusys.ai.news_nlp / kabusys.ai.regime_detector
  - OpenAI を利用した NLP モジュール。API レスポンスの検証・リトライ等の処理を含む。

- kabusys.utils.logging_setup.setup_logging
  - 全プロセスで共通のログ設定を行う関数。

- kabusys.utils.process_priority.set_process_priority
  - Windows / POSIX に跨るプロセス優先度設定ユーティリティ（psutil 使用）。

---

## ディレクトリ構成

省略可能ファイルを除いた主要な構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
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
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (存在想定 / 参照される)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在想定 / 参照される)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

プロジェクトルート:
- data/                     — DB・PID・flag 等（実行時に作成）
- logs/                     — ログファイル（デフォルト）

---

## 注意事項 / 運用メモ

- Paper Trading と Live の DB は分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視コンポーネントは監視用 SQLite（settings.sqlite_path）を使用。監視はどの KABUSYS_ENV でも同じ監視 DB を参照します（run_monitoring の設計による）。
- OpenAI 系機能は API キーが必須です。失敗時はフェイルセーフで継続するよう実装されていますが、キー未設定では明示的なエラーが出ます。
- .env は機微な情報を含むため絶対に Git にコミットしないでください（config_setup の出力にも警告を含む）。
- ログディレクトリや DB ファイルの親ディレクトリが存在しない場合、起動スクリプト側で必要に応じて作成されますが、アクセス権やパスの確認を事前に行ってください。

---

README はここまでです。必要であれば以下の追加情報を含めることができます:
- 実行フロー図（Engine / Broker / Monitor の相互作用）
- サンプル .env.example
- 代表的なログ抜粋とトラブルシューティング手順
どれを追加したいか指示してください。