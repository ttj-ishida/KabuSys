# KabuSys

日本株向け自動売買システムのコアライブラリ群。戦略・ポートフォリオ構築、監視、実行エンジンの起動スクリプト、AI を使ったニュース評価などのユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成された、自動売買システムの基盤ライブラリです。

- 環境変数 / .env の読み書き・検証ツール
- 実行エンジン起動スクリプト（実売買 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクターキャップ等）
- 研究用ファクター計算・特徴量探索（DuckDB 経由）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- 各種ユーティリティ（ログ設定、プロセス優先度、レポート生成 等）

設計方針の例:
- DB（DuckDB / SQLite）や OpenAI など外部依存は注入/環境変数で切替可能
- ペーパートレード時は本番 DB と分離（別 SQLite ファイル）
- ルックアヘッドバイアス回避のため日付や時刻の扱いに注意

---

## 主な機能一覧

- 設定/環境管理
  - .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行関連
  - 実行エンジン起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading DB に記録
  - 監視ループ起動スクリプト（run_monitoring.py）
    - システム状態・データ鮮度監視、リスク監視、Kill Switch 評価
- 監視 / リスク管理
  - SystemMonitor / TradeMonitor / RiskMonitor と MonitoringEngine
  - SQLite ベースの監視ログ（monitoring_db）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止シグナル
- ポートフォリオ構築
  - 候補選定、等配分／スコア加重、リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数
- 研究 (research)
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュースを銘柄ごとにスコアリングして ai_scores に保存（news_nlp）
  - 市場レジーム判定（regime_detector）
  - リトライ、レスポンス検証、部分書き込みによる堅牢な設計
- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順

最低限の Python 環境（例: Python 3.10+）を用意してください。

1. リポジトリをクローン / 展開
   - 仮にプロジェクトルートが存在すると .env 自動ロード等が有効になります。

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（代表例）
   - duckdb
   - psutil
   - openai
   - PyYAML（オプション: validate_config の YAML 検証に使用）
   例:
     pip install duckdb psutil openai PyYAML

   注意: sqlite3 は標準ライブラリです。

4. .env の作成
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - もしくは `.env.example` を参考に手動で作成（リポジトリに example がある想定）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. ディレクトリ作成（実行前）
   - デフォルトで使用されるディレクトリ:
     - data/ （SQLite DB・PID・kill.flag 等）
     - logs/ （ログファイル保存）
   - ログディレクトリは環境変数 LOG_DIR で変更可能（default: logs/）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API を使うモジュールで必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1。0 推奨）

自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）を見つけると `.env` と `.env.local` を自動で読み込みます。テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要コマンド例）

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 本番 / 開発（KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動を行いません。
    - 実行中は data/execution.pid に PID を書きます。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（秒、デフォルト 60）
    - 監視は本番 sqlite_path を使ってログ保存（環境に依らず本番パスを使用）
    - data/stop_requested.flag を検知するとループ終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - db パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ライブラリとして利用）
  - 例: ニューススコアリング（Python REPL またはスクリプト）
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

  - 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")

  注意: OpenAI API キーは OPENAI_API_KEY 環境変数でも指定できます。

---

## 監視・停止の仕組み（簡潔）

- kill.flag（data/kill.flag）
  - KillSwitch が条件を満たすとこのファイルを書きます。ExecutionEngine は起動時にこのフラグをチェックし、ファイルがあれば起動しません。
  - 実行中は Monitoring の評価で必要に応じて kill.flag が作成され、実行エンジンを安全に停止できます。
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py が外部からの停止要求を検知するために参照します。存在するとループを抜けて終了します。
- PID ファイル
  - run_execution は data/execution.pid を利用してプロセス管理・検出を行います。

---

## ログ

- ログ構成は kabusys.utils.logging_setup.setup_logging によって統一されています。
  - コンソール（stdout）出力と日次ローテーションファイル（logs/<app_name>.log）を併用。
  - LOG_DIR 環境変数または引数でログ保存先を変更可能。
  - デフォルトは logs/（30 日分保持）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下のおおまかな構成（本リポジトリに含まれるファイルに基づく）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py 等が想定される)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - その他: execution/*（実行ロジック）、data/（DB・フラグ・PID）等

---

## 開発上の注意点 / ベストプラクティス

- 本番動作時（KABUSYS_ENV=live）は特に kill.flag / KILL_FLAG_CLEAR_ON_START 設定に注意してください。デフォルトで自動クリアは無効（0 推奨）。
- Paper trading 時は本番 DB とデータが分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI API を利用する機能は API レート制限やエラーへ対するリトライ処理を実装していますが、API キーの管理・コストには注意してください。
- DuckDB の接続はライブラリ呼び出し側で作成して注入する設計になっています（テストでの差し替えが容易）。
- モジュール単位でのユニットテストを整備することを推奨します（外部 I/O をモック可能な設計）。

---

この README はコードベースの主要点を抜粋した概要です。詳細や運用ルールは各モジュールのドキュメントノート（ソースの docstring）を参照してください。必要であれば実行例や追加の運用手順（systemd ユニット、監視ジョブ、Dockerfile など）を追記します。