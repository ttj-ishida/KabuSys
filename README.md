README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）起動スクリプト
- システム監視（Monitoring）および監視用 DB 操作
- ペーパートレード検証ツール（レポート生成）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- ファクター計算・リサーチ用ユーティリティ（DuckDB を利用）
- ニュース NLP（OpenAI を用いたセンチメントスコアリング）
- 設定ウィザード（.env 生成）と設定検証 CLI
- 共通ユーティリティ（ログ設定、プロセス優先度設定など）

特徴
----
- モジュール化された監視・実行・研究コンポーネント
- DuckDB を用いたオフライン分析（prices_daily / raw_financials 等を前提）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント／レジーム判定（オプション）
- ペーパートレード用に本番 DB と分離された SQLite をサポート
- 簡易的な Kill Switch（data/kill.flag）で ExecutionEngine を安全に停止可能
- .env 対話ウィザード + 設定検証ツールで初期セットアップを支援

セットアップ手順
----------------
1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化してください（venv / pipenv / poetry 等）

   例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - コード内で使用している主要パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使用する場合)
     - PyYAML (config 検証時に YAML ファイル検証を行う場合)
   - インストール例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env の作成（対話式ウィザード）
   - 初期設定を対話式で行う:
     python -m kabusys.config_setup
   - これによりプロジェクトルートに .env が書き込まれます（Git 管理下に置かないでください）

4. 設定の検証
   - 作成後、設定検証を実行して不足項目や注意点を確認します:
     python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     python -m kabusys.validate_config --strict

5. データディレクトリ等の作成
   - デフォルトでは以下のパスが使われます。必要に応じて .env で上書きしてください。
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視 DB): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
     - 実行 PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

使い方
------

環境変数（主要なもの）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")。デフォルト "development"。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）。
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）。
- SQLITE_PATH: 監視 DB (SQLite)（デフォルト data/monitoring.db）。
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）。
- OPENAI_API_KEY: OpenAI を使う場合の API キー。
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。
- PAPER_FILL_MODE: ペーパートレードのフィルモード ("instant" | "partial" | "never" | "reject")。

起動スクリプト
- 監視ループ（SystemMonitor）を起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60秒）。
  - 監視は環境（KABUSYS_ENV）にかかわらず sqlite_path に書き込みます（監視ログは production DB を想定）。

- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid を利用します。停止は stop フラグの作成で制御します。

停止 / Kill Switch
- Kill Switch: data/kill.flag を書くことで ExecutionEngine に停止シグナルを送ります（KillSwitch モジュール）。
- run_* スクリプトは data/stop_requested.flag を参照して安全にループを終了します。

ログ
- 共通の logging 設定ユーティリティがあり、コンソール出力（stdout）と日次ローテートファイルログ（logs/<app>.log）を生成します。
- ログディレクトリは環境変数 LOG_DIR で上書き可能。

ツール
- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
  - 注文成功率、稼働率、レイテンシ等を判定し PASS/FAIL を出力します。

ライブラリ利用例（プログラム的に）
- ポートフォリオ構築:
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- ファクター計算:
  from kabusys.research import calc_momentum, calc_volatility, calc_value
- ニュース NLP / レジーム判定:
  from kabusys.ai import score_news
  - OpenAI API キー（OPENAI_API_KEY）を設定して利用してください。

ディレクトリ構成
----------------
（src/kabusys をルートとした主要ファイル／モジュール）
- src/kabusys/
  - __init__.py                      - パッケージ初期化、バージョン情報
  - config.py                        - 環境変数 / Settings 管理、.env 自動読み込みロジック
  - config_setup.py                  - .env 対話式ウィザード
  - validate_config.py               - .env と config/*.yaml の検証 CLI

  - run_monitoring.py                - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 - ExecutionEngine 起動スクリプト

  - utils/
    - logging_setup.py               - 統一ログ設定ユーティリティ
    - process_priority.py            - プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py               - SQLite 監視 DB の初期化・読み書き
    - system_monitor.py              - CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py                - （発注トレース監視、滞留注文検知等）※実装ファイルあり
    - risk_monitor.py                - ドローダウン・ポジション上限監視
    - kill_switch.py                 - kill.flag の管理
    - monitoring_engine.py           - 複数 Monitor を束ねるエンジン
    - alert_manager.py               - （LINE 等へ通知を行うコンポーネント）※実装ファイルあり

  - execution/
    - broker_factory.py              - ブローカークライアント生成（Mock / 実ブローカー）
    - execution_engine.py            - 実行エンジン本体（セッション管理等）
    - order_manager.py               - 発注管理
    - order_repository.py            - 発注履歴永続化（SQLite 等）
    - reconciler.py                  - ブローカーとローカル状態の整合処理
    - risk_manager.py                - 発注前のリスクチェック

  - portfolio/
    - portfolio_builder.py           - 候補選定・スコアソート
    - position_sizing.py             - 株数算出・集計上限スケールダウン
    - risk_adjustment.py             - セクター上限・レジーム乗数

  - research/
    - factor_research.py             - Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py         - 将来リターン計算・IC 等の解析ユーティリティ

  - ai/
    - news_nlp.py                    - raw_news を集約し OpenAI でセンチメントを算出、ai_scores に保存
    - regime_detector.py             - ETF MA + マクロ NLP を合成して市場レジーム判定

  - tools/
    - paper_verification_report.py   - ペーパートレード検証レポート生成スクリプト

注意事項 / 運用上のヒント
------------------------
- 本プロジェクトは本番環境（KABUSYS_ENV=live）で動かす際は十分な注意が必要です。validate_config の警告を良く確認してください。
- .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- OpenAI API を使う機能は外部 API に依存します。API キー管理・料金・レート制限を考慮してください。
- run_execution は paper_trading モードであれば本番 DB と分離して動作します。実運用時は KABUSYS_ENV を正しく設定してください。
- 監視ロジックはデフォルトで監視 DB（SQLITE_PATH）へログを書きます。監視 DB は起動スクリプトから自動初期化されます。

付録：よく使うコマンド例
-----------------------
- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（バックグラウンド等で実行）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 開発
----------------
- コード構成はモジュール単位で分かれているため、ユニットテストやモック差替えで個別コンポーネントを検証しやすく設計されています。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）は外部で準備して利用してください（本プロジェクトはそのテーブル定義そのものは含みません）。

以上。README の内容に加え、具体的な要件（Python バージョン、依存ライブラリバージョン、DB テーブルスキーマ等）が決まり次第、requirements.txt や docs/ に追記すると運用がより容易になります。