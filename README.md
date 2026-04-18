README
======

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を目的とした Python パッケージです。本リポジトリには以下の主要機能を備えています。

- 実行エンジン（ExecutionEngine）: 発注・オーダー管理・リスク管理を行うランタイム（run_execution.py）
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク指標のポーリングとアラート（run_monitoring.py）
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出（kabusys.portfolio）
- リサーチ / ファクター計算: Momentum / Value / Volatility 等のファクター計算（kabusys.research）
- AI ユーティリティ: ニュースのセンチメント評価や市場レジーム判定（kabusys.ai）
- 開発用ツール: .env ウィザード、設定検証、Paper Trading 検証レポート等

特徴
----
- 環境変数 / .env による柔軟な設定
- 本番／ペーパートレードの DB 分離（paper_trading モード）
- DuckDB を用いた分析向けテーブルアクセス
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（任意）
- ログは stdout と日次ローテーションファイルに出力（logs/ ディレクトリ）
- 監視データは SQLite に永続化（data/monitoring.db 等）
- Kill Switch（data/kill.flag）による ExecutionEngine 停止機構

セットアップ
------------
1. リポジトリのクローン・作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - 必須（基本実行）:
     pip install duckdb psutil
   - AI 機能を使う場合:
     pip install openai
   - config/*.yaml の構文チェックをするなら（任意）:
     pip install PyYAML

   （プロジェクトに requirements.txt があればそちらを利用してください）

4. 環境変数の準備
   - 対話式ウィザードで .env を生成できます（推奨）:
     python -m kabusys.config_setup
   - 必須項目（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数例:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（分析用）
     - SQLITE_PATH: data/monitoring.db（監視ログ）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の専用 DB）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

使い方
------

実行エンジン（ExecutionEngine）
- 本番／ペーパーの ExecutionEngine を起動します。
- 実行（プロジェクトルートで）:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag（data/stop_requested.flag）を書き込むか Kill Switch を使用します。

監視（Monitoring）
- 監視ポーリングループを起動します:
  - python -m kabusys.run_monitoring
- 挙動:
  - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します
  - 停止はプロジェクトルート/data/stop_requested.flag を置くことで行います

環境設定ウィザード
- .env を対話的に作成・更新:
  - python -m kabusys.config_setup

設定検証
- .env と config/*.yaml の簡易チェック:
  - python -m kabusys.validate_config
  - --strict で警告もエラー扱い

Paper Trading 検証レポート
- ペーパートレードの検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI / ニュース NLP
- OpenAI キーが必要（環境変数 OPENAI_API_KEY か関数引数で指定）
- ニュースのセンチメントスコア付与:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行します（スクリプト化はされていませんが、research/ai 関数から呼べます）

ログ
- ログはデフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力されます。
- ログディレクトリは環境変数 LOG_DIR で変更できます。

重要ファイル / フラグ
- data/stop_requested.flag — run_execution/run_monitoring 停止用フラグ（停止検知に使用）
- data/kill.flag — Kill Switch（監視が条件に合致した際に作成）
- data/execution.pid — ExecutionEngine の PID（run_execution によって作成）
- DB（デフォルトパス）:
  - data/monitoring.db — 監視用 SQLite（init_monitoring_db がテーブル作成）
  - data/paper_trading.db — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時）

ディレクトリ構成
----------------
主要なソース構成（src/kabusys）:

- src/kabusys/
  - __init__.py               — パッケージ定義（バージョン等）
  - config.py                 — Settings クラス（環境変数/.env 読み込み・検証）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリングして ai_scores に書込む
    - regime_detector.py      — マクロニュース + ETF MA200 を使ったレジーム判定

  - portfolio/
    - portfolio_builder.py    — 銘柄選定・スコアソート
    - position_sizing.py      — 発注株数計算（単元丸め・スケールダウン）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py      — Momentum/Value/Volatility ファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ

  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化・永続化 API
    - system_monitor.py       — システム / データ鮮度チェック
    - trade_monitor.py        — （注文ログ監視、コード内参照）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 複数モニタの統合ポーリング
    - kill_switch.py          — Kill Switch 実装
    - alert_manager.py        — （アラート送信管理、LINE 等への UI）

  - execution/
    - execution_engine.py     — ExecutionEngine 本体（run_session など）
    - order_manager.py        — Order 管理ロジック
    - order_repository.py     — 発注ログ / DB 永続化
    - reconciler.py           — ブローカ同期用の差分解消
    - broker_factory.py       — BrokerClient の生成（実ブローカ / Mock 切替）

  - monitoring/monitoring_db.py — 監視テーブル定義 / DB 操作

  - utils/
    - logging_setup.py        — 統一ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート

補足 / 注意事項
----------------
- KABUSYS_ENV を live に設定する前に必ず validate_config を実行して設定を検証してください。live モードは本番発注が有効になります。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーと課金が必要です。失敗時はフェイルセーフ（代替値）で継続する実装ですが、利用時は注意してください。
- ローカルでの開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理をスキップできます（テスト等で便利）。
- monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。ペーパートレード用 DB と混同しないようにご注意ください。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

以上。README に記載のコマンドや環境変数を参照し、まずは .env を作成 → validate → monitoring / execution を順に動かして動作確認してください。