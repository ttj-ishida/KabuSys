KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／研究／監視コンポーネント群を集めたモノリポジトリです。  
ここに含まれるコードは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP / レジーム判定などを提供します。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution） — 本番 / ペーパートレードで分離された DB を使用して発注処理を実行
- Monitoring（run_monitoring） — システム状態・データ鮮度・取引イベント・リスク監視を周期的に実行し、kill flag による停止をサポート
- MonitoringDB — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- リスク監視（ドローダウン・ポジション上限）と Kill Switch による自動停止
- Portfolio Construction（候補選定、配分重み、サイズ決定、セクターキャップ、レジーム乗数）
- Research（ファクター・ボラティリティ・バリュー計算、特徴量探索、IC計算）
- AI モジュール（news_nlp: OpenAI を使ったニュースセンチメント、regime_detector: MA + マクロセンチメントでレジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証、紙トレード検証レポート）
- DuckDB を分析用に利用、SQLite を監視 / 発注履歴用に利用

必要な依存パッケージ（主なもの）
--------------------------------
以下は代表的な依存です。環境に合わせて requirements.txt を作成してください。

- python >= 3.9
- duckdb
- psutil
- openai
- PyYAML (config YAML の検証を行う場合に必要)

インストール例（仮）
pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリをクローン / 展開する

2. .env ファイルの作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - ウィザードは .env（デフォルト）に各種環境変数を書き込みます。重要な項目:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（デフォルト INFO）
     - その他：LINE 関連、KILL_FLAG_CLEAR_ON_START 等

   - 手動例（.env の一部）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     OPENAI_API_KEY=sk-...

3. 設定検証（起動前推奨）
   - 基本検証:
     python -m kabusys.validate_config
   - 警告もFAIL扱い（--strict）:
     python -m kabusys.validate_config --strict

4. ログ / データディレクトリの準備
   - デフォルトでは logs/（ログ）、data/（DB・PID・flag）を使用します。setup_logging は自動的に作成を試みますが、権限等で失敗する可能性があるため事前作成を推奨。

使い方（起動例）
----------------

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV に応じて本番/ペーパートレード切替）
  python -m kabusys.run_execution

  重要ポイント:
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - ExecutionEngine は実行中に data/stop_requested.flag を検知すると安全に停止します。
  - PID ファイル: data/execution.pid（設定で変更可）

- Monitoring を起動（周期的に SystemMonitor.check_once を呼び出す）
  python -m kabusys.run_monitoring

  重要ポイント:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は「環境にかかわらず」settings.sqlite_path（本番監視 DB）を使用して監視ログを永続化します。
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート（ツール）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

- AI スコアリング / レジーム判定（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  これらは DuckDB 接続と OpenAI API キーが必要です。CLI エントリは用意されていないため、スクリプトやスケジューラから呼び出してください。

主要機能一覧（要点）
-------------------
- run_execution.py
  - ExecutionEngine の起動ラッパー
  - 環境により paper_trading 用 DB を使い分け
  - BrokerClientFactory により実ブローカ / モックを切替
  - プロセス優先度を High に設定（psutil 経由、権限や OS に依存）

- run_monitoring.py
  - SystemMonitor のポーリングループを実行
  - MONITOR_POLL_INTERVAL で間隔指定
  - monitoring DB を初期化（init_monitoring_db）

- config.py, config_setup.py, validate_config.py
  - .env 自動読込（プロジェクトルートを基準に .env/.env.local をロード）
  - 対話式ウィザードで .env を生成
  - 起動前に設定妥当性チェック（validate_config）

- monitoring/*
  - monitoring_db: SQLite スキーマ初期化と永続化 API
  - system_monitor: CPU/メモリ/disk・プロセス死活・データ鮮度チェック
  - trade_monitor: trade_logs に基づく滞留注文・異常約定判定（詳細は実装ファイルを参照）
  - risk_monitor: ドローダウン／ポジション上限監視と dashboard 更新
  - kill_switch: 条件を満たすと data/kill.flag を出力して ExecutionEngine 停止を誘導
  - monitoring_engine: 各モニターを束ねてポーリング・アラート連携

- portfolio/*
  - portfolio_builder: 候補選定、等金額・スコア加重の重み計算
  - risk_adjustment: セクター制限適用、レジーム乗数
  - position_sizing: 株数算出（lot 単位丸め、risk_based/equal/score の割当方法、aggregate cap のスケーリング）

- research/*
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー

- ai/*
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント集計 → ai_scores テーブルに書き込み
  - regime_detector: ETF (1321) の MA200 乖離 + マクロニュースの LLM センチメント混合で市場レジーム判定を行い market_regime テーブルへ書き込み

ユーティリティ
--------------
- utils/logging_setup.py
  - StreamHandler (stdout) + TimedRotatingFileHandler（日次ローテーション）をルートロガーに設定
  - デフォルト log_dir は logs/

- utils/process_priority.py
  - Windows / POSIX に対応したプロセス優先度設定（psutil 使用）
  - CPU Affinity 設定補助関数あり

運用上の注意
-----------
- DB 分離: paper_trading では paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番監視 DB（SQLITE_PATH）とデータ分離します。一方、monitoring は環境にかかわらず settings.sqlite_path（監視 DB）を使用します。
- Kill Flag / Stop Flag:
  - kill.flag: リスク等で ExecutionEngine を停止させる意図で監視側から書き込むフラグ（Settings.kill_flag_path）
  - stop_requested.flag: ランチャー（外部）による停止要求（run_execution/run_monitoring は data/stop_requested.flag を監視）
- OpenAI API 呼び出しは失敗時にフォールバック（スコア=0.0 等）する設計だが、API キー未設定時は例外が発生することがあるため注意してください。
- .env の自動ロード:
  - プロジェクトルート（.git or pyproject.toml を探索）を基準に .env/.env.local を自動ロードします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - OS 環境変数は優先され、.env.local は .env を上書きします。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                  # 環境変数 / 設定読み込み
    config_setup.py            # .env 対話ウィザード
    validate_config.py         # 設定検証 CLI
    run_execution.py           # ExecutionEngine 起動スクリプト
    run_monitoring.py          # Monitoring 起動スクリプト

    execution/                 # 発注関連（Broker, Engine, OrderManager 等）
      ... (実装ファイル群)

    monitoring/                # 監視関連コンポーネント
      monitoring_db.py
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
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py
      regime_detector.py
      __init__.py

    tools/
      paper_verification_report.py
      __init__.py

    data/                      # 実行時に生成される（デフォルト）
      monitoring.db
      paper_trading.db
      kabusys.duckdb
      execution.pid
      kill.flag
      stop_requested.flag

最小動作確認フロー（例）
----------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の DB ファイルがなければ作成（アプリ起動時に自動で作られます）
4. 監視を起動: python -m kabusys.run_monitoring
5. 別ターミナルでエンジンを起動: python -m kabusys.run_execution
6. ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- 詳細実装（ExecutionEngine、BrokerClient 等）は実際の取引を伴うため取り扱いに注意してください。本番（KABUSYS_ENV=live）では設定・通知先（LINE など）やキルスイッチを慎重に設定してください。
- PyYAML が無い場合、validate_config は YAML 内容検証をスキップします（存在確認は行います）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで動作継続します。

ライセンス / バージョン
-----------------------
バージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

（必要に応じてここに LICENSE 情報や貢献ルールを追記してください）

以上。開発 / 運用に関する詳細な設計意図やアルゴリズムの説明は各ソースファイルの docstring を参照してください。