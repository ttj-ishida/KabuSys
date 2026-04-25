KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買・調査・モニタリングを行うためのモジュール群です。  
この README は配布されたソースコード（src/kabusys 以下）を元に、導入・実行・構成の手順や各モジュールの役割を日本語でまとめたものです。

概要
----
KabuSys は以下の主要機能を提供します。

- 実行エンジン（ExecutionEngine）: 発注ロジック・オーダーマネージャ・リスク管理を組み合わせて発注を実行
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク指標を定期的にチェックしログ／アラート／Kill Switch を管理
- ポートフォリオ構築（Portfolio）: 候補選定・重み計算・サイズ決定・セクター制限などの純粋関数群
- 研究（Research）: ファクター計算、将来リターン、IC 等の分析ユーティリティ（DuckDB ベース）
- AI ユーティリティ（AI）: ニュース NLP（OpenAI）によるセンチメントスコア算出、レジーム検出
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ファイル自動ロード等
- ツール: ペーパートレード検証レポート生成スクリプト など

主な特徴
--------
- .env による環境変数管理（自動ロード機能、.env/.env.local の優先順位）
- 開発/ペーパートレード/本番（KABUSYS_ENV）を切り替え可能
- ペーパートレード用 DB を本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を分析基盤として活用
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／レジーム判定（API キー必要）
- モジュールはテストしやすい純粋関数／小さなクラスに分割

セットアップ手順（概略）
---------------------
1. Python 環境準備
   - 推奨: 仮想環境（venv / pyenv 等）を作成
   - Python 3.9+ を想定（コードは型ヒント等を使用）

2. 依存ライブラリ（代表例）
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML のパースを行う場合）
   - （実際の requirements.txt はプロジェクトに応じて用意してください）
   例:
     pip install duckdb psutil openai PyYAML

3. リポジトリルートに移動して .env を作成
   - 対話式ウィザードを使う:
       python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記に例あり）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit(1)）になります:
       python -m kabusys.validate_config --strict

5. ディレクトリとデータファイル
   - デフォルトの DB / ログパスは .env の設定または以下デフォルト値
     - データベース（DuckDB）: data/kabusys.duckdb
     - 監視 SQLite: data/monitoring.db
     - ペーパートレード SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 起動スクリプトは data/ 以下のフラグファイル（stop_requested.flag / kill.flag 等）や pid ファイルを参照・更新します。

推奨 .env（例）
----------------
以下は .env の最低限の必須項目の例です（.env.example を参考に作成してください）。

    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
    KABU_API_PASSWORD=your_kabu_api_password_here
    KABU_API_BASE_URL=http://localhost:18080/kabusapi
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    KILL_FLAG_CLEAR_ON_START=0

- OpenAI を使う機能を使う場合:
    OPENAI_API_KEY=sk-...

主要コマンド・使い方
-------------------

1) 環境ウィザード（.env 作成）
   - 対話式で .env を生成 / 更新:
       python -m kabusys.config_setup

2) 設定検証
   - 起動前にチェック:
       python -m kabusys.validate_config
   - 警告を fail としたい場合:
       python -m kabusys.validate_config --strict

3) ExecutionEngine（発注エンジン）を起動
   - 実行:
       python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
     - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
     - 実行中に data/stop_requested.flag が出現すると安全に停止を試みる
     - 起動時にプロセス優先度を high に設定（可能な場合）
     - PID ファイル: data/execution.pid（設定により変更可）

4) Monitoring（監視ループ）を起動
   - 実行:
       python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）
     - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用して monitoring DB を初期化/更新
     - 監視ループは data/stop_requested.flag の存在で終了
     - プロセス優先度を high に設定（可能な場合）

   - 例（ポーリング間隔 30 秒）:
       MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5) Paper Trading 検証レポート生成
   - 使用方法:
       python -m kabusys.tools.paper_verification_report
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db で指定、指定がなければ環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使う

注意: 停止・Kill 操作
---------------------
- run_execution.py と run_monitoring.py は data/stop_requested.flag をポーリングして安全終了します。停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成してください。
- KillSwitch（自動停止判定）は data/kill.flag を書き込みます。KillSwitch がトリガーした場合は ExecutionEngine 側で検知して停止する設計です。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動でクリアする挙動になります（本番では 0 推奨）。

主要設定項目（環境変数）
-----------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live

- DB / ログ
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR (default: logs/)

- Monitoring
  - MONITOR_POLL_INTERVAL (秒、run_monitoring で上書き可能)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START などは Settings 経由で取得

- Paper trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject

- OpenAI
  - OPENAI_API_KEY（AI 機能使用時に必要）

モジュール構成（ディレクトリ構成）
------------------------------
以下は src/kabusys 以下の主要なパッケージ・ファイル構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の読み込み・ラッパー
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI

  - run_execution.py         — ExecutionEngine 起動スクリプト（発注）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - execution/               — 発注関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite のテーブル作成・永続化ラッパー
    - system_monitor.py      — システム監視（CPU/MEM/DISK、データ鮮度、実行プロセス検出）
    - trade_monitor.py       — 注文ログ監視（滞留注文・約定異常など）※詳細は該当ファイル参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag を書くロジック
    - monitoring_engine.py   — 監視コンポーネントを束ねる実行エンジン
    - alert_manager.py       — アラート送信（LINE 等） ※実装参照

  - portfolio/
    - portfolio_builder.py   — 候補選定・スコア順ソート
    - position_sizing.py     — 株数計算・単元丸め・集約キャップ
    - risk_adjustment.py     — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — momentum/value/volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — raw_news を LLM で評価して ai_scores へ書き込み
    - regime_detector.py     — ETF MA とマクロ NLP に基づいて市場レジーム判定

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

  - utils/
    - logging_setup.py       — 統一ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

ログとファイル
---------------
- デフォルトのログディレクトリ: logs/
  - setup_logging(app_name="execution") などで logs/<app_name>.log に日次ローテーション出力
- データファイル: data/ 以下に SQLite / pid / flag ファイルを置く想定
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

注意事項・運用上のポイント
------------------------
- .env ファイルにはシークレット（API トークン等）を含むため、絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live の場合は設定ミスが重大な資金被害につながるため、validate_config の警告を必ず確認してください。
- OpenAI を用いる機能は API コストとレイテンシに注意し、apikey の管理を厳重に行ってください。
- プロセス優先度設定や CPU affinity は権限（root 等）が必要な場合があります。設定に失敗しても警告を出して続行する実装です。

開発者向けメモ
--------------
- .env の自動読み込みはデフォルトで有効（config.py）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定検証（validate_config）は PyYAML があれば config/*.yaml の構文チェックを行います。インストールされていない場合はスキップします。
- AI API 呼び出し部分はリトライ・バックオフ・レスポンスバリデーションを含む堅牢な実装となっていますが、テスト時は該当呼び出し関数をモック（unittest.mock.patch）して切り替え可能です。
- DuckDB 接続を前提とする research / ai モジュールは、テーブルが期待どおりに存在することを前提としています。データ準備スクリプト等を別途用意してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報は本リポジトリの LICENSE を参照してください（必要に応じて追加／修正してください）。

問い合わせ・貢献
----------------
バグ報告、機能提案、プルリクエストはリポジトリの issue/PR を利用してください。README の改善提案も歓迎します。

以上がコードベース（src/kabusys）の主要な README 内容です。README に追加したい具体的な起動例（systemd unit、Dockerfile、CI 設定など）や、各モジュールの詳細ドキュメント生成を希望する場合は、それに合わせて追加します。