KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／研究フレームワークです。本リポジトリには以下の主な機能を持つモジュール群が含まれます。

- 発注エンジン（ExecutionEngine）およびブローカークライアント抽象化
- 監視機構（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- ニュース NLP を用いた AI スコアリング（OpenAI）
- Paper Trading 用検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール

特徴
----
- 環境変数 / .env を用いた柔軟な設定管理（Settings クラス）
- DuckDB（分析用） / SQLite（監視・履歴用） を併用
- Paper Trading モードで本番 DB と分離（data/paper_trading.db）
- OpenAI を利用したニュースセンチメント・レジーム判定機能（オプション）
- ログはコンソールと日次ローテートファイルに出力（logs/*.log）
- フラグファイル（data/kill.flag / data/stop_requested.flag）でプロセス制御

セットアップ手順
----------------

1. リポジトリをクローンして依存ライブラリをインストール
   - Python 3.9+ を推奨
   - 例（pip）:
     - pip install -r requirements.txt
     - 必要な主要パッケージ:
       - duckdb
       - psutil
       - openai (AI機能利用時)
       - PyYAML (validate_config で YAML 検証を行う場合)

2. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合の主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # development | paper_trading | live
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-xxxxx   # AI 機能を使う場合
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  # (任意)

   - 注意: .env は Git にコミットしないこと。

3. 設定の検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

4. データディレクトリ / ログディレクトリの作成
   - デフォルト:
     - data/ （SQLite、PID、フラグファイル）
     - logs/ （ログファイル）
   - 例:
     - mkdir -p data logs

使い方
-----

基本的な起動・ツールの実行はモジュールとして実行します。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 実行時の振る舞い:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（デフォルト data/paper_trading.db）に記録します。
    - 実行中は PID ファイル（data/execution.pid）を作成します。
    - data/stop_requested.flag が存在すると起動しない／停止します。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定（デフォルト 60秒）
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視は Settings に依存して sqlite_path を使用（monitoring は常に本番 sqlite_path を参照）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 主要な検証ポイント:
    - 必須環境変数の有無（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）
    - KABUSYS_ENV の有効値
    - DB パスの親ディレクトリ存在チェック
    - config/*.yaml の存在（PyYAML があればパース検証）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 / --db オプションで指定可能。デフォルト: data/paper_trading.db
  - 出力: 稼働率・注文成功率・レイテンシ等のサマリと PASS/FAIL 判定

- AI 機能
  - kabusys.ai.score_news を呼び出してニュースセンチメントを ai_scores テーブルへ書き込みます。
  - OpenAI API キーは OPENAI_API_KEY 環境変数で指定。
  - news_nlp / regime_detector は API 呼び出しの失敗に対してフェイルセーフ動作（デフォルトのスコアで継続）します。

運用 / 制御に関するメモ
- Kill Switch:
  - KillSwitch は settings.kill_flag_path（デフォルト data/kill.flag）を使って ExecutionEngine に停止シグナルを送ります。
  - kill.flag が存在すると ExecutionEngine は起動時に Kill を検出できます。
  - 手動で解除する場合: rm data/kill.flag
- 停止フラグ:
  - run_monitoring/run_execution は data/stop_requested.flag を監視してループ停止／エンジン停止を行います。
- ログ:
  - デフォルトログディレクトリ: logs/
  - 各アプリケーションは logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
  - LOG_DIR 環境変数で変更可能。

設定（Settings）に関する補足
- Settings クラスは .env ファイル（.env.local を上書き）および OS 環境変数から値を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要プロパティ例:
  - env (KABUSYS_ENV): development | paper_trading | live
  - sqlite_path (SQLITE_PATH): 監視 DB のパス（デフォルト data/monitoring.db）
  - duckdb_path (DUCKDB_PATH): 分析用 DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - paper_sqlite_path (PAPER_TRADING_SQLITE_PATH): Paper Trading 用 DB パス
  - paper_fill_mode (PAPER_FILL_MODE): instant | partial | never | reject

ディレクトリ構成（主なファイル / モジュール）
------------------------------------

- src/kabusys/
  - __init__.py                     — パッケージ定義（バージョン等）
  - config.py                       — 環境変数 / .env 読み込み・Settings 定義
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI

  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

  - execution/                      — 発注・エンジン関連（抽象, Engine, OrderManager 等）
    - (実ファイル群はリポジトリにより追加)

  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py             — システムモニタ（CPU/メモリ/ディスク/プロセス/データ鮮度）
    - trade_monitor.py              — 注文関連監視（滞留注文や異常約定検出）
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — Kill Switch 実装（フラグファイル書込）
    - monitoring_engine.py          — 各 Monitor を束ねる実行ループ
    - alert_manager.py              — LINE 等への通知ラッパ（実装がある場合）

  - portfolio/
    - portfolio_builder.py          — 候補選定・重み付け（equal / score）
    - position_sizing.py            — 株数決定・集約キャップ処理
    - risk_adjustment.py            — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py            — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py        — 将来リターン・IC・統計サマリ等
    - __init__.py                   — 研究用 API エクスポート

  - ai/
    - news_nlp.py                   — ニュースを OpenAI でスコアリングして ai_scores に書込
    - regime_detector.py            — MA + マクロセンチメントからレジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成 CLI

  - utils/
    - logging_setup.py              — 統一的ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ
    - (その他ユーティリティ)

運用上の注意 / ベストプラクティス
--------------------------------
- 本番運用時（KABUSYS_ENV=live）は .env の設定を慎重に確認してください（validate_config の警告参照）。
- .env は機密情報を含むため絶対に Git へコミットしないこと。
- OpenAI API キーや API コールの課金に注意。AI 部分はオプションです。
- Paper Trading を用いてロジックを十分に検証してから本番発注を行ってください。
- run_execution/run_monitoring は systemd や Supervisor / Docker などでプロセスマネージャから管理することを推奨します。ログや PID ファイルの管理を行ってください。

ライセンス / 貢献
-----------------
- この README はコードベースに基づく導入ドキュメントです。実際のライセンス・貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

お問い合わせ
------------
- 実装詳細や使い方で不明点があれば、該当モジュール（例: monitoring, execution, ai）を参照し、必要に応じて issue を作成してください。

以上。必要があれば導入手順の具体的なコマンド例（systemd unit や Dockerfile、.env.example のテンプレート）を追記します。どの情報を補足しますか？