# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、ペーパートレード／本番発注、監視・アラート、AI を用いたニュース解析などの機能を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の用途を想定したモジュール群です。

- DuckDB / SQLite を用いた時系列データ解析・ファクター計算（research）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- ExecutionEngine を通した発注・リスク管理（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）の運用
- OpenAI を用いたニュースセンチメント評価・レジーム判定（AI モジュール）
- ペーパートレード結果の検証レポート生成ツール

設計方針の一部：
- DB 接続を注入する方針（DuckDB / SQLite）
- 本番／ペーパーを環境変数 `KABUSYS_ENV` で切替
- 自動化運用を考慮したログ・プロセス優先度設定・フラグファイル制御

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- 実行/監視スクリプト
  - run_execution: ExecutionEngine 起動（`python -m kabusys.run_execution`）
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し `data/paper_trading.db` に分離保存
  - run_monitoring: SystemMonitor ポーリングループ起動（`python -m kabusys.run_monitoring`）
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き可（デフォルト 60 秒）

- 監視 / Kill Switch
  - SystemMonitor、TradeMonitor、RiskMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine の停止
  - risk_monitor によるドローダウン / ポジション上限監視、log を SQLite に永続化

- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等配分 / スコア加重配分
  - リスクベースの株数計算（lot サイズ丸め、aggregate cap のスケーリング）
  - セクター上限の適用、レジーム乗数

- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）、統計サマリ

- AI（OpenAI）
  - ニュース NLP（news_nlp）：raw_news をまとめて LLM に投げ、銘柄別センチメントを ai_scores に書き込み
  - レジーム判定（regime_detector）：ETF MA とマクロセンチメントを合成して daily regime を生成

- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 前提（推奨）パッケージ

最低限の依存（実行に必要なもの）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証で YAML ファイルを検証するなら任意）

インストール例:
pip install duckdb psutil openai pyyaml

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動

2. Python 環境を作成・有効化（推奨: venv / virtualenv / pyenv）

3. 依存パッケージをインストール
   - 例: pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを利用する:
     - python -m kabusys.config_setup
   - ウィザードで作成した .env はプロジェクトルートに配置されます。
   - 必須設定例:
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須
     - OPENAI_API_KEY は AI 機能を使う場合に必須

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

6. データ／ログディレクトリ
   - デフォルト DB/ログパス（.env で変更可）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/<app>.log
   - 必要に応じてディレクトリを作成（多くの処理は自動作成を試みます）

注意:
- 本番環境では KABUSYS_ENV を `live` に設定すると本番 API を使用します。十分に注意して設定してください。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も FAIL）: python -m kabusys.validate_config --strict

- ExecutionEngine（注文実行エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数:
    - development: 発注を行わない開発用
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録
    - live: 本番発注
  - 停止: 監視側やオペレーターが data/kill.flag を書くと停止シグナル（Kill Switch）として機能します。
  - 起動時、`data/execution.pid` が作成されます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止フラグファイル `data/stop_requested.flag` を置くとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数で DB を指定する場合: PAPER_TRADING_SQLITE_PATH

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要（引数経由で渡す API も関数には用意されています）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を受けて実行します（コードから呼び出す用途）
  - CLI 実装は用意されていないため、スケジューラやスクリプトから呼び出して運用してください。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除する（0/1。 production では 0 推奨）

---

## 停止／Kill Switch の運用

- kill.flag（デフォルトパス: data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送ります（KillSwitch）。
- monitoring は KillSwitch を評価し、条件により kill.flag を書くことがあります（例: DRAWDOWN_ALERT, POSITION_LIMIT）。
- stop_requested.flag（data/stop_requested.flag）を配置すると run_monitoring / run_execution のループを終了します（運用者が使う停止フラグ）。

---

## ディレクトリ構成（主なファイル／モジュール）

概略（src/kabusys 以下）:

- __init__.py
- config.py
- config_setup.py
- validate_config.py

- run_monitoring.py
- run_execution.py

- ai/
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

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- data/（実行時に生成される想定）
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - kill.flag, stop_requested.flag, execution.pid などの運用フラグ

（実際のリポジトリでは上記に加えて execution パッケージの各モジュール（broker_factory、execution_engine、order_manager など）や data / strategy 周りのモジュールが存在します。）

---

## 開発・運用時の注意点

- 本番運用時（KABUSYS_ENV=live）は設定ミスが致命的になり得ます。`python -m kabusys.validate_config --strict` による確認を推奨します。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup は注意書きを出します）。
- AI（OpenAI）呼び出しではレート制限や一時的失敗に備えたリトライ実装がありますが、API キーの管理とコストに注意してください。
- DuckDB / SQLite のファイルはバックアップ・運用方針に従って管理してください（特に本番データ）。

---

もし README に追記してほしいサンプルコマンド、環境変数の雛形（.env.example の内容）、あるいは個別モジュールの API ドキュメントが必要であればお知らせください。