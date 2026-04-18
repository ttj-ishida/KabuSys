KabuSys — 日本株自動売買システム README
==================================

概要
----
KabuSys は日本株向けの自動売買システム／研究基盤のコード群です。  
主に以下の責務を持ちます。

- 発注実行エンジン（ExecutionEngine）
- 監視（Monitoring） / Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量探索）
- AI 帰属のニュースセンチメント／レジーム判定（OpenAI）
- 運用補助ツール（設定ウィザード、構成検証、ペーパートレード検証レポート）

このリポジトリはライブラリとしての利用（import）と、モジュール単位での CLI 実行（python -m ...）の両方を想定しています。

主な機能
--------
- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory による実際のブローカー／モック切替
  - RiskManager・OrderManager・Reconciler を組み合わせた実行エンジン
  - 起動時 PID ファイル作成 / 停止フラグ（data/stop_requested.flag）で安全停止

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度監視
  - TradeMonitor：注文滞留、約定異常などの検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：重大事象で data/kill.flag を書き込み Execution を停止させる
  - MonitoringDB：SQLite ベースの監視ログ永続化（テーブル作成・マイグレーション含む）

- Portfolio
  - 候補選定（スコア順）、等重／スコア重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap でスケーリング）

- Research
  - DuckDB を使ったファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - ニュース NLP（OpenAI を使ったセンチメント集約 → ai_scores へ保存）
  - レジーム判定（ETF MA + マクロニュースセンチメントの合成）
  - API 呼び出しは堅牢なリトライ / バックオフ / バリデーションを実装

- ツール
  - .env 設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート出力（kabusys.tools.paper_verification_report）

前提条件（簡易）
----------------
- Python 3.10+（コードは | 型、match 等に依存していませんが union 表記を使用）
- 推奨ライブラリ（最低限必要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容チェックを行う場合）
- SQLite は標準ライブラリで提供
- システムにより追加の OS 権限（プロセス優先度設定や CPU affinity）が必要になる場合があります

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb psutil
   - AI 機能を使う場合:
     - pip install openai
   - config YAML の検証を使う場合:
     - pip install pyyaml

   （プロジェクトに requirements.txt があればそれを使用してください）

4. .env ファイル作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env の既存値を読み込み、対話的に更新します
   - あるいは .env を手動で作成（.env.example を参考に）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ・ログディレクトリの準備
   - デフォルト DB / ファイルパスは data/ および logs/
   - 必要に応じて環境変数で上書き（下記を参照）

主要な環境変数
---------------
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading の場合、Execution は MockBrokerClient を使用し data/paper_trading.db に書き込みます
- DB / パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（Execution pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch の旗ファイル、デフォルト: data/kill.flag）
  - LOG_DIR（ログ出力先、デフォルト: logs/）
- ログ / 動作
  - LOG_LEVEL（INFO 等）
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒） — run_monitoring.py で使用、デフォルト 60）
- Paper Trading / Mock 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject
- OpenAI
  - OPENAI_API_KEY（AI 機能を使う場合）

自動 .env 読み込み
- プロジェクトルートにある .env / .env.local は起動時に自動読み込みされます（OS 環境変数が優先）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（起動例）
----------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（CLI）
  - python -m kabusys.run_execution
  - 実行時、KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用します
  - 起動中に data/stop_requested.flag を作成すると安全に停止します（run_execution はこのフラグを監視します）
  - 実行開始時に data/execution.pid が作成されます

- Monitoring 起動（CLI）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）
  - 監視は system_status 等を monitoring DB（SQLITE_PATH）に書き込みます
  - data/stop_requested.flag を作成すると監視ループは停止します
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番パス）を利用します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ライブラリ呼び出し）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

ログ
----
- setup_logging() ユーティリティで標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）を統一して設定します。
- LOG_DIR 環境変数で出力先を変更できます。

停止・キルスイッチ
------------------
- 安全停止フラグ（stop）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して終了します（デバッグ / 運用停止用）
- Kill Switch（運用上の致命的トリガー）
  - monitoring の判定により KillSwitch が data/kill.flag を書き込みます
  - ExecutionEngine は kill.flag の存在を起点に停止する設計になっています
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアしますが、本番では 0（クリアしない）を推奨します

ディレクトリ構成（主なファイル）
-------------------------------
src/
  kabusys/
    __init__.py                — パッケージ初期化（バージョン等）
    config.py                  — 環境変数 / Settings 管理、自動 .env ロード
    config_setup.py            — .env 対話式ウィザード
    validate_config.py         — 起動前設定検証 CLI
    run_execution.py           — ExecutionEngine 起動スクリプト
    run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

    execution/                 — 発注実行関連（BrokerFactory, Engine, OrderManager 等）
    monitoring/
      monitoring_db.py         — SQLite スキーマ / 永続化層
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    data/                      — データパイプライン・スキーマ（DuckDB/SQLite 連携）
    tools/
      paper_verification_report.py

    utils/
      logging_setup.py
      process_priority.py

data/                          — デフォルトのデータ保存先（DB・フラグ・PID 等）
logs/                          — ログ保存先（デフォルト）

注意点 / 運用メモ
-----------------
- Monitoring は sqlite_path を固定で使用します。開発時に monitoring と execution で DB を分けたい場合は SQLITE_PATH を個別に設定してください。
- run_execution は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH を使用し、発注履歴を本番 DB と分離します。
- OpenAI を使う AI モジュールは API キーが必須です。API 呼び出しはリトライ・バックオフ・レスポンスバリデーションを実装していますが、API 利用料とレイテンシには注意してください。
- データ鮮度チェックや PID ファイル管理、Kill Switch の挙動は慎重に運用してください。本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。

トラブルシュート（よくある質問）
--------------------------------
- ログファイルが作成されない:
  - LOG_DIR の書き込み権限を確認。権限がないとファイル出力がスキップされ、コンソールのみになります（警告が stderr に出ます）。
- psutil による優先度設定が失敗する:
  - 権限（root）が必要な場合があります。失敗時は警告を出してスキップする実装です。
- .env 自動ロードを無効化したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献 / 開発
-----------
- 単体テストやモジュール分割が進行中です。ユニットテストは外部 API 呼び出しをモックする形で作成してください（例えば news_nlp._call_openai_api のパッチ等）。
- ドキュメント（PortfolioConstruction.md や StrategyModel.md）に基づく実装が含まれています。アルゴリズムや閾値を調整する場合は該当ドキュメントを参照してください。

付記
----
この README はコード構成と動作方針の要約です。各モジュールには詳細な docstring が含まれているため、個別の挙動や引数仕様は該当ファイルを参照してください。質問や補足があれば教えてください。