# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / 研究 / 監視用ライブラリ群です。  
README はプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存
- セットアップ手順
- 環境変数（主なキー）
- 実行方法（使い方）
- よく使うユーティリティ / スクリプト
- ディレクトリ構成（主要ファイル説明）
- 備考

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムを構成するためのモジュール群です。  
主に以下の用途を想定しています。

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ポートフォリオ構築（銘柄選定・重み付け・株数算出）
- 研究（ファクター計算、将来リターン、IC など）
- ニュースの NLP スコアリング（OpenAI を利用）
- ペーパートレード用検証レポート出力

設計方針として、DB を通じた永続化（SQLite / DuckDB）と、外部 API を疎結合に扱うことを重視しています。

---

## 機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の際は MockBroker を使い、paper_trading 用 DB（data/paper_trading.db）に記録。
- 監視プロセス
  - run_monitoring.py: SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60 秒）。
  - MonitoringEngine: System / Trade / Risk の各 Monitor を束ね、アラートや Kill Switch 評価を実行。
- 監視 DB 層
  - monitoring_db.py: SQLite を用いた監視ログ・ダッシュボード永続化。
- Risk / Trade / System の監視ロジック
  - risk_monitor.py, system_monitor.py, trade_monitor.py（trade_monitor はコード一覧に一部のみ含む）
  - KillSwitch による停止フラグ (data/kill.flag) の書込み
- ポートフォリオ構築
  - portfolio/ 以下: 候補選択、重み化、ポジションサイズ算出、セクター制約、レジーム乗数
- 研究（Research）
  - research/*: ファクター計算（momentum, value, volatility）、forward returns、IC 計算、統計サマリ
  - DuckDB 接続を通じて prices_daily / raw_financials 等のテーブルを参照
- AI（ニュース NLP / レジーム判定）
  - ai/news_nlp.py: raw_news をまとめて LLM に投げ、銘柄別センチメントを ai_scores テーブルへ保存
  - ai/regime_detector.py: ETF(1321) MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成（稼働率・約定率・レイテンシ等）
- 設定管理・ユーティリティ
  - config.py: 環境変数 / .env の自動読み込みと Settings クラス
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プラットフォーム差分吸収のプロセス優先度設定
  - monitoring/monitoring_engine.py: 監視ループ束ね

---

## 前提・依存

推奨 Python バージョン: 3.10 以上（型ヒントの | 記法を使用しているため）。

主要依存（最小限）:
- duckdb
- psutil
- openai (AI機能を使う場合)
- PyYAML（validate_config の YAML 検証を使いたい場合）
- sqlite3（標準ライブラリのため追加不要）

インストール例:
- pip install duckdb psutil openai PyYAML

（requirements.txt は付属していません。プロジェクトで必要な依存をプロジェクト側で管理してください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - 例: PYTHONPATH を通す場合は開発環境から `PYTHONPATH=src` を使います。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザード:
     - PYTHONPATH=src python -m kabusys.config_setup
     - これによりプロジェクトルートの .env を作成・更新できます。
   - または手動で .env を作成（以下を参照）。

5. 設定検証
   - PYTHONPATH=src python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. DB ファイル用ディレクトリ確保
   - デフォルトで data/ 以下を使います。自動で作成されない場合は手動で作成してください。

---

## 環境変数（主なキー）

Settings クラス / config_setup が扱う主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（推奨） / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO（例: DEBUG, INFO, WARNING）
- OPENAI_API_KEY: OpenAI を使う機能で必要

監視関連:
- KILL_FLAG_CLEAR_ON_START: 0（本番で 1 にするな — Kill Switch 自動クリア）
- PID_FILE_PATH / KILL_FLAG_PATH は Settings で参照可能（デフォルト data/execution.pid / data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring でポーリング間隔を秒で上書き（デフォルト 60）

Paper trading 特有:
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）

注意: .env を絶対に Git にコミットしないでください（config_setup でも警告があります）。

---

## 実行方法（使い方）

開発環境から直接実行する例（プロジェクトルートが一つ上の階層にある場合）:

- PYTHONPATH を使ってモジュール実行:
  - PYTHONPATH=src python -m kabusys.run_execution
    - ExecutionEngine を起動します。KABUSYS_ENV により paper_trading を分離します。
  - PYTHONPATH=src python -m kabusys.run_monitoring
    - SystemMonitor のポーリングループを開始します。MONITOR_POLL_INTERVAL を秒で上書き可能。
  - PYTHONPATH=src python -m kabusys.validate_config
    - 設定検証 CLI。--strict が利用可能。
  - PYTHONPATH=src python -m kabusys.config_setup
    - 対話式 .env 作成ウィザード。
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - ペーパートレード検証レポートの出力（DB パスは --db または PAPER_TRADING_SQLITE_PATH）。

ログ:
- ログはデフォルトで logs/ ディレクトリに日次ローテートで保存されます（例: logs/execution.log, logs/monitoring.log）。
- setup_logging() により stdout とファイル（TimedRotatingFileHandler）が設定されます。

停止 / Kill Switch:
- run_execution/run_monitoring は data/stop_requested.flag の存在を監視して安全に終了します。
- KillSwitch（監視）により data/kill.flag が書き込まれると ExecutionEngine 側で停止シグナルを受け取る仕組みです。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動クリアする挙動になります（本番では推奨されません）。

MONITOR_POLL_INTERVAL:
- run_monitoring のループ間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に設定可能（デフォルト 60）。不正値や 0 以下はデフォルトにフォールバックします。

Paper trading:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。

AI 機能:
- ai/news_nlp.py, ai/regime_detector.py は OPENAI_API_KEY が必要です。API 呼び出しはリトライなどフォールトトレラントに実装されていますが、API キー未設定ではエラーとなります。

---

## よく使うユーティリティ / スクリプト

- python -m kabusys.config_setup
  - .env を対話的に作成・更新
- python -m kabusys.validate_config [--strict]
  - 環境設定・config/*.yaml の事前検証
- python -m kabusys.run_execution
  - ExecutionEngine を起動（本番または paper_trading）
- python -m kabusys.run_monitoring
  - 監視ループを開始（SystemMonitor を周期実行）
- python -m kabusys.tools.paper_verification_report --from <YYYY-MM-DD> --to <YYYY-MM-DD> [--db PATH]
  - ペーパートレード検証レポートを標準出力

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ定義、__version__。
- config.py
  - Settings クラス。環境変数の読み取り、.env 自動ロード機能を含む。
- config_setup.py
  - 対話式 .env 作成ウィザード。
- validate_config.py
  - 起動前に環境・設定ファイルの妥当性をチェックする CLI。

スクリプト:
- run_execution.py
  - ExecutionEngine の起動スクリプト。process priority を上げ、DB 接続、Broker 作成、ExecutionEngine を開始。
  - data/stop_requested.flag による停止検出、data/execution.pid 書込みなどを扱う。
- run_monitoring.py
  - SystemMonitor ポーリングループ起動。MONITOR_POLL_INTERVAL で間隔変更可能。

サブパッケージ:
- ai/
  - news_nlp.py: raw_news を LLM でスコアリングして ai_scores に書込む。
  - regime_detector.py: ETF MA とマクロニュースで日次レジーム判定。
- monitoring/
  - monitoring_db.py: SQLite によるテーブル作成・ラッパー（MonitoringDB）。
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・プロセス存在チェック。
  - risk_monitor.py: ドローダウン・ポジション上限監視。risk_logs / dashboard 対応。
  - kill_switch.py: data/kill.flag 書き込み・クリア。
  - monitoring_engine.py: 各 Monitor を束ね、アラート送信や Kill Switch 評価を行う。
  - trade_monitor.py: 注文滞留・約定異常などの監視（コードベースの一部）。
- portfolio/
  - portfolio_builder.py: 候補選定、等金額/スコア加重の重み計算。
  - position_sizing.py: 株数計算、aggregate cap、lot 単位丸め。
  - risk_adjustment.py: セクターキャップ、レジーム乗数。
- research/
  - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB 使用）。
  - feature_exploration.py: forward returns, IC, factor summary 等。
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト。
- utils/
  - logging_setup.py: ルートロガーの統一設定（stdout + TimedRotatingFileHandler）。
  - process_priority.py: Windows/Linux の差分を吸収したプロセス優先度設定ユーティリティ。

その他:
- data/ (期待されるディレクトリ)
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - kabusys.duckdb（DUCKDB_PATH）
  - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

---

## 備考 / 運用上の注意

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 に設定することを推奨します。
- .env は機密情報（API トークン等）を含むため必ず .gitignore に追加し、リポジトリにコミットしないでください。
- AI 機能（news_nlp, regime_detector）は外部 API を利用するため費用とレートリミットに注意してください。失敗時はフェイルセーフで進める設計になっていますが、運用方針を決めてください。
- DuckDB / SQLite のスキーマやテーブル名（prices_daily, raw_financials, raw_news 等）は研究・AI モジュールと整合させる必要があります。
- validate_config.py は起動前チェックに有用です。CI に組み込むことを推奨します。

---

もし README に加えて、サンプル .env.example や requirements.txt、起動用 systemd / docker-compose のテンプレートが必要であれば作成できます。どの形式を優先して欲しいか教えてください。