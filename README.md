KabuSys
=======

日本株自動売買システム（KabuSys）のコードベース向け README（日本語）

この README はリポジトリ内の主要コンポーネント、セットアップ手順、利用方法、ディレクトリ構成の概要をまとめたものです。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムです。主な機能は以下の通りです。
- 発注エンジン（ExecutionEngine）による注文作成・管理（本番 / ペーパートレード対応）
- 監視サブシステム（MonitoringEngine）によるシステム状態・注文状態・リスク監視
- ポートフォリオ構築ロジック（候補選定、重み計算、ポジションサイズ算出、セクター制約など）
- リサーチモジュール（ファクター計算、将来リターン、IC 計算、統計サマリ等）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定 / OpenAI 利用）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポートなど）
- ログ整備、プロセス優先度設定、SQLite / DuckDB を利用した永続化

主な設計指針
- 本番とペーパートレードの DB は原則分離（PAPER_TRADING_SQLITE_PATH を使用）
- ルックアヘッドバイアス回避（各モジュールは date 引数や接続を受け取り、今日を直接参照しない）
- フェイルセーフ設計（API 失敗時はスキップやフォールバックで継続）
- ロギングは共通ユーティリティで統一（logs/<app>.log、日次ローテーション）

機能一覧
--------
- 設定関連
  - .env 対話式ウィザード: kabusys.config_setup.run_wizard / python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config (--strict オプション)
  - 自動 .env ロード（プロジェクトルートの .env / .env.local。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

- 実行系
  - 発注エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
    - PID ファイル: data/execution.pid（デフォルト）
    - 停止フラグ: data/stop_requested.flag を監視

- 監視系
  - 監視ループ起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔変更（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path を参照（環境に関わらず）
    - kill.flag を生成する KillSwitch 機能で ExecutionEngine を停止可能

- ポートフォリオ構築（pure functions）
  - 候補選定: select_candidates
  - 等分配 / スコア加重配分: calc_equal_weights, calc_score_weights
  - ポジションサイジング: calc_position_sizes（lots 単位, risk_based / equal / score）
  - リスク調整: apply_sector_cap, calc_regime_multiplier

- リサーチ
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB を使用）
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank

- AI（OpenAI）
  - ニュース NLP: kabusys.ai.news_nlp.score_news — raw_news を集約して LLM でスコアリング
  - レジーム判定: kabusys.ai.regime_detector.score_regime — ma200 とマクロセンチメントを合成
  - OpenAI API 利用時は OPENAI_API_KEY が必要

- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
    - PAPER_TRADING_SQLITE_PATH を参照（デフォルト: data/paper_trading.db）

セットアップ手順
----------------
（以下は一般的な手順例です。プロジェクトに requirements.txt があればそちらを優先してください。）

1. リポジトリをクローン／チェックアウト
   - git clone ... && cd <repo>

2. Python 環境を作成（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install -r requirements.txt
   必須ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML (config 検証時のみ推奨)
   （requirements.txt がない場合は上の主要パッケージを個別にインストール）

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 自動ロード機構が働くため、プロジェクトルート（.git / pyproject.toml のある場所）に .env を置く

5. 設定検証（必須環境変数チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - data/ や logs/ は起動時に自動作成されますが、権限等で失敗する場合は手動で作成してください。

主要環境変数（デフォルト含む）
------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - is_paper 判定でペーパートレード DB を分離
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db (監視用 DB)
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/（ログファイル格納先）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
- KILL_FLAG_CLEAR_ON_START: 0/1
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag

使い方（コマンド例）
-------------------
- 設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も NG）: python -m kabusys.validate_config --strict

- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: data/stop_requested.flag が存在すると起動せず終了します
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード用 DB を使用

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db path/to/db

- AI モジュール（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 必要に応じて OPENAI_API_KEY を環境変数に設定

運用に関する注意
----------------
- kill.flag / stop_requested.flag / execution.pid
  - run_execution / run_monitoring は stop_requested.flag を監視して安全停止できます
  - KillSwitch は条件に応じて kill.flag を書き込み、ExecutionEngine に停止指示を出します
  - PID ファイルは data/execution.pid（設定で変更可）

- ログ
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30 日保持）
  - ログディレクトリの作成に失敗するとコンソール出力のみで継続します

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います

- テスト／開発
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない（テスト時に便利）

ディレクトリ構成（概要）
-----------------------
以下は src/kabusys 以下の主要ファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py                     — パッケージ定義（__version__ 等）
  - config.py                        — Settings / 自動 .env ロード / 環境変数取得ユーティリティ
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor 起動スクリプト

  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py               — SQLite テーブル定義と永続化 API
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — （注文ログ監視等 — 実装参照）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag の評価・書き込み
    - monitoring_engine.py           — 各 Monitor を束ねるループ
    - alert_manager.py               — （LINE 等へ通知する管理クラス — 実装参照）

  - execution/
    - execution_engine.py            — ExecutionEngine（発注セッション管理）
    - order_manager.py               — 注文管理ロジック
    - order_repository.py            — 注文永続化（SQLite）
    - reconciler.py                  — ブローカーとの差分解消
    - risk_manager.py                — 発注前リスクチェック
    - broker_factory.py              — BrokerClient の生成（Mock/実ブローカー切替）

  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 発注株数計算
    - risk_adjustment.py             — セクター上限・レジーム乗数

  - research/
    - factor_research.py             — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py         — 将来リターン・IC・統計ユーティリティ

  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py             — マクロ + ETF ma200 によるレジーム判定

  - monitoring/, tools/, portfolio/, research/ 等にさらに細かい実装ファイルあり

補足（開発者向け）
-----------------
- DuckDB を使って大規模な時系列データやファクター計算を行います。prices_daily / raw_financials 等のテーブルが前提です。
- OpenAI を使う機能は API エラー時にリトライやフォールバックを行う設計です。API キーの管理に注意してください。
- 本リポジトリ内のコメントと docstring（日本語）に設計意図や注意事項が多数含まれています。実運用前に validate_config で各種設定を確認してください。

ライセンス・貢献
----------------
- ライセンス情報は本リポジトリのトップレベルファイル（LICENSE 等）を参照してください。
- バグ報告・機能提案は Issue を立ててください。

以上がこのコードベースの概要と利用方法です。追加で各モジュールの詳細な API ドキュメントや実行例（サンプル .env、データベース初期データ生成スクリプト等）が必要であれば教えてください。