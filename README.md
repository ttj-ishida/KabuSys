README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード切替）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- DuckDB を使ったファクター計算・リサーチ機能
- OpenAI を使ったニュース NLP（銘柄別センチメント）とレジーム判定
- 開発支援ツール（.env ウィザード / 設定検証 / ペーパートレード検証レポート）

特徴
----
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切替可能
- 発注系と監視系の DB を分離（ペーパートレード時は専用 SQLite を使用）
- DuckDB による高速な時系列・ファクター計算（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（フェイルセーフ設計）
- ログはコンソール + 日次ローテート（logs/ に保存）

必要要件（主な依存）
-------------------
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（設定検証時に config/*.yaml を検証する場合）

セットアップ手順
----------------

1. リポジトリをクローンしてワークディレクトリに移動します。

2. Python 仮想環境を作成・有効化して依存パッケージをインストールします（例）。

   - pip を使う例:
     - pip install -r requirements.txt
     - （requirements.txt が無い場合は duckdb, psutil, openai, pyyaml 等を個別にインストール）

3. .env の作成（対話式ウィザード）

   - 初期 .env を生成 / 更新する:
     - python -m kabusys.config_setup

   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 重要な環境変数（主なもの）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - OPENAI_API_KEY: OpenAI API を使う機能を利用する場合に必要

4. 設定検証

   - 自動的に読み込んだ .env / config/*.yaml をチェック:
     - python -m kabusys.validate_config
     - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリの確認
   - デフォルトでは data/ と logs/ を使用します。起動時に作成されますが、権限等で失敗する場合は手動で作成してください。

使い方
------

基本的な起動スクリプト
- 監視ループを起動する（定期的に System/Trade/Risk をチェック）:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring

  備考:
  - 監視は KABUSYS_ENV の値に関わらず本番の sqlite_path（SQLITE_PATH）を使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます（存在を検知してループを終了）。

- 実行エンジン（ExecutionEngine）を起動する:
  - python -m kabusys.run_execution

  備考:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録し、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動をスキップします。
  - 実行中は data/execution.pid に PID が書き込まれます。停止は stop flag を作成するか ExecutionEngine.stop() が呼ばれます。

ツール類
- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱いにできます

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を使用

AI（OpenAI）機能
- ニュース NLP スコアリング:
  - kabusys.ai.score_news を利用（プログラムから呼ぶ）
  - OpenAI API キーは OPENAI_API_KEY 環境変数、または関数引数で渡します
  - 大量の API 呼び出しを行うため、レート制限やリトライの設計が組み込まれています

- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime を利用（DuckDB 接続と target_date を渡す）
  - OpenAI API キーが必要

ログ
---
- ロギングは共通ユーティリティ kabusys.utils.logging_setup.setup_logging を通じて設定されます。
- デフォルト: コンソール（stdout）と logs/<app_name>.log（毎日ローテート、30日保持）
- LOG_DIR 環境変数や setup_logging の引数でログディレクトリを変更できます。

停止 / Kill Switch
- ExecutionEngine を強制停止するための Kill Switch:
  - kabusys.monitoring.kill_switch は条件を満たすと data/kill.flag を書き込み、外部から ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill flag を自動クリアします（本番では推奨されません）。

設定例（重要な環境変数）
- 最小セット（.env に記載する例）
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_password_here
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=sk-...

ディレクトリ構成（主なファイル）
--------------------------------

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブモジュール
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコアリング
  - regime_detector.py     — マクロ + MA200 を組み合わせたレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — （取引監視ロジック）※本 README では省略（コード参照）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 操作用ユーティリティ
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — （アラート送信管理、LINE 等）※実装参照
- execution/
  - execution_engine.py    — ExecutionEngine 実装（run_session 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py      — BrokerClient の生成（Mock / 実ブローカー切替）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数算出・スケーリング
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- data/
  - pipeline.py            — データパイプライン（例: get_last_price_date 等）
  - stats.py               — 正規化ユーティリティ（zscore 等）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上のヒント
-------------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。基本は 0 を推奨します。
- OpenAI を利用する機能は API コストおよびレート制限に注意してください。API キーは .env で管理してください。
- DuckDB / SQLite ファイルはバックアップ・監視を行ってください。特にペーパートレード用 DB は本番 DB と分離されていますが、混同しないよう注意してください。
- ログや data/ ディレクトリの権限、ディスク空き容量に注意してください（監視モジュールがディスク使用率をチェックします）。

貢献 / テスト
--------------
- 設定周り（config_setup / validate_config）はユニットテストや手動検証がしやすい設計になっています。
- AI 呼び出しは _call_openai_api をパッチしてモック化できます（テスト容易性を考慮した設計）。

ライセンス / バージョン
------------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

さらに詳しく
--------------
- 各モジュールの詳細な使用方法やパラメータは該当ファイルの docstring / コメントを参照してください（特に portfolio/*、research/*、ai/*、monitoring/*）。

必要であれば、特定の起動例や環境変数テンプレート（.env.example）、systemd/cron 用の起動スクリプト例なども追加できます。必要な場合は教えてください。