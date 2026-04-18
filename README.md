KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株の自動売買 / 研究 / 監視のための内部ライブラリ群と起動スクリプト群を収めたミニマルなフレームワークです。
本 README はコードベース（src/kabusys 以下）の概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

前提
----
- Python 3.10 以上を想定（構文に match ではないが型の union 演算子 `|` を使用）。
- pip 等で外部依存パッケージをインストールする必要があります（下記参照）。

プロジェクト概要
--------------
KabuSys は次の主要コンポーネントで構成されます。

- 実行エンジン（ExecutionEngine 起動スクリプト run_execution.py）
  - ブローカークライアントを介して発注・注文管理を行う。
  - Paper Trading モードでは MockBroker を用い、本番 DB と分離して data/paper_trading.db に記録します。
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine により定期的にシステム状態や注文状況を監視。
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化。
  - KillSwitch による停止フラグ（data/kill.flag）で ExecutionEngine に停止指示を出せる仕組み。
- データ処理・研究（research / ai / portfolio）
  - DuckDB を用いたファクター計算、将来リターン計算、IC 計算などの研究モジュール。
  - ニュースの NLP（OpenAI）を用いた銘柄別センチメントスコアリング、レジーム判定モジュール。
  - 銘柄選定やポジションサイズ計算などのポートフォリオ構築ロジック。
- ユーティリティ（config, config_setup, validate_config, logging_setup, process_priority）
  - .env のウィザード生成、起動前設定検証、統一的なロギング設定、プロセス優先度設定等。

主な機能一覧
-------------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine の起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリング起動
  - python -m kabusys.config_setup : .env の対話的作成/更新ウィザード
  - python -m kabusys.validate_config : 設定検証 CLI
  - python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート生成
- 設定管理
  - .env の自動ロード（プロジェクトルートが推定できる場合）
  - Settings クラスで環境変数を型付きで取得（env・DBパス・各種閾値など）
- 監視
  - CPU / メモリ / ディスク使用率、プロセス存否、データ鮮度監視
  - リスク（ドローダウン・ポジション上限）検知とログ記録
  - Kill Switch の自動書き込み（条件に応じて data/kill.flag を作成）
- 発注・注文管理
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - Paper Trading と Live の分離（DB とブローカー挙動）
- 研究・分析
  - DuckDB によるファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC 計算、特徴量サマリ
- AI（OpenAI）
  - ニュース記事から銘柄別センチメントを LLM（gpt-4o-mini など）で算出して ai_scores に保存
  - マクロセンチメントを組み合わせた市場レジーム判定（bull/neutral/bear）
- ロギング
  - stdout と日次ローテートファイル（logs/<app_name>.log）に出力

セットアップ手順
----------------

1. リポジトリをクローンして Python 仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 基本的に以下をインストールしてください（requirements.txt がない場合は手動で）:
     - duckdb
     - psutil
     - openai
     - pyyaml (config 検証で optional)
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要:
     - OPENAI_API_KEY は AI 関連機能を使う場合に必要。
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH を設定するとペーパートレード DB のパスを変更できます。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

5. ディレクトリ作成（スクリプトが自動作成するが事前に作ると安全）
   - mkdir -p data logs

基本的な使い方
--------------

- ExecutionEngine の起動（本番 / ペーパー）
  - 環境変数でモードを切り替え:
    - export KABUSYS_ENV=paper_trading
    - export KABUSYS_ENV=live
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使用（設定で変更可）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に data/stop_requested.flag を作成すると実行エンジンは停止します（run_execution と run_monitoring 両方共通の停止フラグ）。

- Monitoring の起動
  - ポーリング起動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - python -m kabusys.run_monitoring
  - 挙動:
    - 監視は Settings で指定した sqlite_path（デフォルト data/monitoring.db）に書き込みます（環境に依らず本番 sqlite_path を使用）。
    - data/stop_requested.flag を作成すると監視ループを終了します。

- 停止方法
  - 優雅な停止（各スクリプトが参照する停止フラグ）:
    - touch data/stop_requested.flag
      - run_execution と run_monitoring はこのファイルを監視し、見つかれば終了処理を行います。
  - Kill Switch（監視から ExecutionEngine を止める）:
    - KillSwitch が条件を満たすと data/kill.flag を作成します。ExecutionEngine は起動時にこのフラグを検査し、KILL_FLAG_CLEAR_ON_START の設定によっては自動クリアの挙動になります（本番では 0 推奨）。

- ログ
  - ログは stdout と logs/<app_name>.log に出力されます。ログディレクトリは環境変数 LOG_DIR で変更可能。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。

主要な環境変数一覧
------------------
（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）
- PAPER_TRADING_SQLITE_PATH（paper_trading モードの SQLite ファイルパス、デフォルト data/paper_trading.db）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- DUCKDB_PATH（DuckDB データファイル、デフォルト data/kabusys.duckdb）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒））
- KILL_FLAG_CLEAR_ON_START（ExecutionEngine 起動時に既存の kill.flag を自動クリアするか: 0/1、デフォルト 0）
- LOG_DIR（ログファイル保存先ディレクトリ）

ディレクトリ構成（src/kabusys）
-------------------------------
主要ファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / 永続化ロジック
    - system_monitor.py
    - trade_monitor.py       — （未掲示の実装ファイルが想定される）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （通知管理）
  - execution/               — ExecutionEngine 周りの実装群（OrderManager 等）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — （データファイル置き場: data/*.db 等、実行中に作成される）

注意事項 / 実運用に関する補足
---------------------------
- 本リポジトリのコードは実証実験／内部運用向けの実装です。実際の発注・運用は十分なテストとガード（監査・資金管理）を行ってください。
- KABUSYS_ENV=live に設定すると本番動作となります。LINE 通知や Kill Switch の設定など、本番用のガードを必ず確認してください。
- OpenAI API の呼び出しはレイテンシ・レート制限・課金が発生します。API キーの管理に注意してください。
- SQLite / DuckDB のファイルはデフォルトで data/ 以下に作成されます。バックアップやアクセス権限に注意してください。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります（setup_logging の仕様）。

よくある操作（例）
------------------
- .env を作って設定検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視サービスをデバッグ実行（1回だけ実行したい場合は MonitoringEngine を直接インポートして run_once を呼ぶなどテスト可能）:
  - python -m kabusys.run_monitoring

- 実行エンジンを起動（paper_trading モードの例）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper Trading の検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 追加情報
-------------------
- 各モジュールの docstring に設計方針や入力/出力仕様が記載されています。実装を拡張する際は docstring をまず参照してください。
- config/*.yaml（設定テンプレート）は scripts やドキュメントが用意されている想定です。validate_config はそれらの存在・パースもチェックします（PyYAML があると参照可能）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理されています（現在 0.1.0）。
- ライセンス情報はリポジトリルートに LICENSE があればそちらを参照してください（本 README には含まれていません）。

以上。必要であれば README に含める具体的な起動例、systemd / supervisor 用のユニットファイルテンプレート、依存パッケージの requirements.txt 例などを追記します。どの情報を追加しますか？