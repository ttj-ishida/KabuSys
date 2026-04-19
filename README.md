KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主要コンポーネントは ExecutionEngine（発注実行）と Monitoring（監視）で、DuckDB を使ったリサーチ／ファクター計算、OpenAI を使ったニュース NLP、ペーパートレーディング用の分離 DB 等を備えています。プロジェクトは環境変数ベースで設定し、.env ウィザードと検証ツールを提供します。

主な機能
-------
- 発注実行（ExecutionEngine）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（実ブローカ or Mock）
  - リスク管理・リコンサイル・オーダーマネージャ
- 監視（Monitoring）
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック、滞留注文・約定異常検出
  - Kill Switch（条件に応じて Execution を停止するフラグ）
- ポートフォリオ構築（Portfolio）
  - 候補選定 / 重み計算（等金額・スコア重み）
  - セクター制約・レジーム補正・ポジションサイズ決定
- リサーチ（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ニュース NLP（AI）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のセンチメントスコア算出
  - 市場レジーム判定のためのマクロセンチメント評価
- ツール
  - Paper Trading 検証レポート生成スクリプト
- 設定管理
  - 対話式 .env ウィザード（config_setup）
  - 起動前の設定検証 CLI（validate_config）
- ロギング / プロセス優先度ユーティリティ

前提 / 必要なライブラリ
---------------------
- Python 3.10+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml（validate_config の YAML 検証を行う場合）
インストール例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
-------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - プロジェクトルートには .git または pyproject.toml が存在する想定です。

2. .env を作成
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他の主な環境変数（省略時のデフォルト値は下記）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: （AI 機能で必要）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

   注: 自動 .env ロードはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

3. 設定検証
   - 起動前に validate を実行して警告・エラーを確認:
     python -m kabusys.validate_config
   - 警告を厳格に失敗扱いする:
     python -m kabusys.validate_config --strict

4. （任意）ログディレクトリ作成
   - デフォルトのログ出力先は logs/。必要に応じて LOG_DIR を設定。

使い方
-----
- ExecutionEngine を起動
  - 本番・ペーパーを切り替えるには KABUSYS_ENV を設定
  - 実行:
    python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と完全分離）
    - 実行開始時に process priority を "high" に設定し、data/execution.pid に PID を出力
    - 停止は data/stop_requested.flag を作成するか、Execution 側で kill.flag（KILL_FLAG_PATH）を検出して停止

- Monitoring を起動
  - 実行:
    python -m kabusys.run_monitoring
  - ポーリング間隔の調整:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60 秒）
  - Monitoring は常に本番用の sqlite_path を参照して監視テーブルを初期化します（環境に依存せず本番 DB を使う仕様）

- Paper Trading 検証レポート
  - 実行例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db。--db で指定可能。

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して利用
  - duckdb 接続を渡して各スコア関数（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）を呼び出す

重要ファイル / フラグ
-------------------
- data/execution.pid : Execution の PID（run_execution が使用）
- data/stop_requested.flag : run_monitoring / run_execution が監視する停止フラグ
- data/kill.flag : KillSwitch が書き込む停止理由フラグ（Settings.kill_flag_path により変更可能）
- .env / .env.local : 環境変数定義（.env は絶対に Git にコミットしないこと）

ログ
---
- ログは標準出力とファイル（logs/<app_name>.log）へ出力されます（TimedRotatingFileHandler 日次ローテーション、30日保持）。
- ログレベルは LOG_LEVEL または setup_logging の引数で制御可能。

ディレクトリ構成（主要部分）
-------------------------
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / 設定読み込みロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity
  - execution/ — 発注エンジン関連（BrokerFactory, EngineConfig, OrderManager 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 発注ログ・異常検出（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（LINE 等のラッパー想定）
  - portfolio/ — 銘柄選定・配分・リスク補正・ポジションサイズ計算
  - research/ — ファクター計算・特徴量探索
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄別スコアを作成
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — ペーパー検証レポート生成
  - data/ — (実行時に作成されることが多い) sqlite/duckdb ファイル・フラグファイル等

注意事項 / 運用上のポイント
--------------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定に注意してください（validate_config は live 用の追加警告を出します）。
- .env は絶対にリポジトリにコミットしないこと（API トークン等が含まれる）。
- DuckDB のパス・SQLite のパスは環境変数で上書きできます。ペーパートレードでは専用 SQLite を使用して本番 DB と分離してください。
- OpenAI を利用する処理はネットワーク不安定時に冗長性（リトライ）を持つよう設計されていますが、APIキーの漏洩・コスト管理に注意してください。
- スクリプトは KeyboardInterrupt での安全な停止や stop_requested.flag の検出に対応しています。

トラブルシューティング
---------------------
- YAML 検証を実行したいが PyYAML が無い場合、validate_config は YAML チェックをスキップして警告を出します。PyYAML を入れると内容も検査されます。
- ログファイルが作成されない場合はログディレクトリのパーミッションや LOG_DIR 設定を確認してください。ディレクトリ作成に失敗するとファイルハンドラの作成はスキップされ、コンソールのみ出力されます。

ライセンス・貢献
----------------
（ここにライセンス表記や貢献方法を追加してください）

付録: よく使うコマンドまとめ
----------------------------
- .env ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
- Execution 起動:
  python -m kabusys.run_execution
- Monitoring 起動:
  python -m kabusys.run_monitoring
  (MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring)
- Paper レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。README に追加したい運用ルールや導入手順（CI/CD、コンテナ化、systemd ユニット例等）があれば追記します。