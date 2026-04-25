KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージです。  
主要機能は以下のとおりです：

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・約定管理（paper_trading モードあり）
- 監視（Monitoring）: システム稼働監視、注文監視、リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ: 候補選定、重み算出、ポジションサイジング等
- リサーチ: ファクター計算・特徴量探索（DuckDB を用いた分析）
- AI モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI API）
- ユーティリティ: 設定ウィザード、設定検証、ログ設定等
- ツール: ペーパートレードの検証レポート生成スクリプト等

重要な設計方針:
- リサーチ / AI モジュールは本番発注 API に直接触れない設計（DuckDB / ローカル DB ベース）
- paper_trading は本番 DB と分離（専用 SQLite を使用）
- 設定は .env または環境変数で管理。自動ロード挙動あり（後述）

主な機能一覧
-------------
- 実行（run_execution.py）
  - KABUSYS_ENV に応じて本番／ペーパートレードを切り替え
  - BrokerClientFactory を通じてブローカークライアント生成
  - リスク管理（RiskManager）、OrderManager、Reconciler を統合した ExecutionEngine を起動
  - data/execution.pid で PID 管理、data/stop_requested.flag による停止指定対応

- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視
  - TradeMonitor: 発注ログの監視（滞留注文・価格異常など）
  - RiskMonitor: ドローダウン / ポジション上限の監視とアラート記録
  - KillSwitch: 危険検知時に data/kill.flag を書き、ExecutionEngine に停止シグナルを送出
  - MonitoringEngine: 上記を束ねるポーリングループ（MONITOR_POLL_INTERVAL で間隔制御）

- ポートフォリオ（portfolio パッケージ）
  - 候補選定（select_candidates）
  - 等金額 / スコア加重の重み計算
  - セクターキャップ適用、レジーム乗数算出
  - ポジションサイズ計算（単元株丸め・コストバッファ・aggregate cap）

- リサーチ（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB 接続を受け取り SQL で高速処理

- AI（ai パッケージ）
  - news_nlp.score_news: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出・書き込み
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
  - OpenAI API の呼び出しは堅牢化（リトライ、バリデーション、部分失敗の保護）

- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の整合性チェック CLI
  - tools.paper_verification_report: ペーパートレード検証レポートの生成

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を用意
   - 推奨: Python 3.10+（コード中で | 型等を使用）
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - main dependencies（最低限）:
     pip install duckdb psutil openai PyYAML
   - 実行環境に応じてさらに必要なパッケージを追加してください。

   （注）本リポジトリに requirements.txt がない場合はプロジェクト独自の依存管理に従ってください。

3. 初期設定（.env）
   - 対話式で .env を生成:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成してください。
   - 自動ロード挙動:
     - 起動時、プロジェクトルートに .env/.env.local があれば自動ロードします（OS 環境変数が優先）。
     - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1) になります。

5. データディレクトリ
   - デフォルト DB / PID / フラグは data/ 配下に配置されます。必要に応じて .env でパスを変更してください。

主要な環境変数（抜粋）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- 実行/監視関連:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL — (DEBUG/INFO/...)、デフォルト INFO
  - LOG_DIR — ログディレクトリ（デフォルト logs/）
  - PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch が書き込むフラグパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)

- DB / ファイル:
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE — paper_trading のマッチング挙動（instant|partial|never|reject）

- AI:
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必須）

- 監視間隔:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）。0 や負数は無効。

使い方（起動例）
----------------

- 環境設定ウィザードを実行:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能:
    export MONITOR_POLL_INTERVAL=30

- 実行エンジン起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用して paper_trading 用 DB に記録します:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution

- ペーパートレード検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプションや環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

プロセス停止・フラグ
-------------------
- 一時停止（監視/実行スクリプト両方で利用）:
  - data/stop_requested.flag が存在すると run_monitoring/run_execution は安全終了します。
  - 手動で作成: touch data/stop_requested.flag
- Kill Switch:
  - Monitoring が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では注意）。

ログ
----
- ロギングは共通のユーティリティ kabusys.utils.logging_setup.setup_logging により設定されます。
- デフォルト: stdout + 日次ローテートされたファイル logs/<app_name>.log（30 日保持）
- ログ出力先やレベルは環境変数 LOG_DIR / LOG_LEVEL で上書き可能。

ディレクトリ構成
----------------
（src/kabusys 以下の主なファイル / ディレクトリの概要）

- kabusys/
  - __init__.py — パッケージのメタ情報（__version__ など）
  - config.py — 設定読み込みロジック（.env 自動ロード・Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI

  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py  — ExecutionEngine 起動スクリプト

  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py  — 発注ログ監視（ファイルは省略）
    - risk_monitor.py   — ドローダウン / ポジション上限監視
    - kill_switch.py    — Kill Switch ロジック（flag ファイル書き込み）
    - monitoring_engine.py — 各種 Monitor を束ねるエンジン
    - alert_manager.py  — （アラート送信。コード参照）

  - execution/
    - execution_engine.py — ExecutionEngine 実装（EngineConfig 等）
    - broker_factory.py   — BrokerClientFactory（環境により Mock/Real を生成）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄スコア算出
    - regime_detector.py — マーケットレジーム判定（MA + マクロニュース LLM）
  - tools/
    - paper_verification_report.py — paper_trading 検証レポート

  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

注意点・運用上のヒント
--------------------
- monitoring は run_monitoring の docstring にある通り「環境にかかわらず本番 sqlite_path を使用」します（監視 DB は本番の監視対象として共有される想定）。一方、run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 SQLite を使用し、本番 DB と分離します。
- .env の自動ロード優先順は OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local で上書きされます。
- OpenAI を利用する機能を動かすには OPENAI_API_KEY を設定してください。API 呼び出しはリトライやレスポンスバリデーションを行いますが、コストとレート制限に注意してください。
- デバッグ時は LOG_LEVEL=DEBUG を設定して詳細ログを取得してください。
- データベースのマイグレーションは monitoring_db.init_monitoring_db の中で基本的なカラム追加（冪等）を行います。既存 DB を運用する場合は事前にバックアップを取ってください。

開発／貢献
---------
- 新しい機能を追加する際は、ユニットテスト・モジュール境界（DB 依存 / 依存注入）を意識してください。AI 呼び出し等の外部 I/O は可能な限りモック可能に実装されています（テスト用に _call_openai_api の差し替え等を利用）。

参考コマンド早見表
-----------------
- .env 対話作成: python -m kabusys.config_setup
- 設定検証:       python -m kabusys.validate_config
- 監視起動:       python -m kabusys.run_monitoring
- 実行起動:       python -m kabusys.run_execution
- レポート出力:   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / その他
-------------------
- 本 README はコードベースの要点をまとめたものであり、実運用に移す際はテスト、設定、アクセス権管理、API 利用制限、監査ログ等を十分に検討してください。

質問や追加してほしいドキュメント（例: 詳細な設定例、デプロイ手順、FAQ）があれば教えてください。README を拡張して整備します。