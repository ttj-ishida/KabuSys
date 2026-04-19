README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python コードベースです。
主要な機能は以下のとおりです。

- 注文実行エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視コンポーネント（Monitoring） — システム状態・注文・リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ — 候補選定、重み計算、ポジションサイズ決定
- リサーチ（Research） — ファクター計算・特徴量解析
- AI モジュール — ニュース NLP によるセンチメント評価、レジーム判定（OpenAI 経由）
- 運用支援ツール — .env ウィザード、設定検証、Paper Trading 検証レポート生成

このリポジトリはライブラリ的なモジュール群と、運用用の起動スクリプト / CLI を含みます。

主な機能一覧
-------------
- run_execution.py: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録
  - 停止は data/stop_requested.flag（プロジェクトルート内）で制御
- run_monitoring.py: SystemMonitor 起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60秒）
  - 監視データは監視用 sqlite に永続化
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env と config/*.yaml の基本検証 CLI
- tools/paper_verification_report.py: ペーパートレード結果のサマリ／判定レポート生成
- monitoring パッケージ:
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db 等
- portfolio パッケージ:
  - 銘柄選定・重み付け・ポジションサイズ計算・リスク調整
- research パッケージ:
  - ファクター計算（momentum/value/volatility）、将来リターン／IC 計算
- ai パッケージ:
  - news_nlp（OpenAI を使った記事のスコアリング）
  - regime_detector（MA + マクロセンチメントでレジーム判定）
- utils: ログ設定、プロセス優先度 / CPU affinity 設定 等
- monitoring_db: 監視ログ用 SQLite スキーマと読込/書込 API

前提・依存
-----------
- 必要 Python バージョン: 3.10+
  - 注: 型アノテーションの union (|) を使用しているため 3.10 以上を想定
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml のパース検証を行う場合、validate_config が利用）
- ログ出力先: デフォルト logs/ ディレクトリ（環境変数 LOG_DIR で変更可能）

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - あるいはプロジェクトに requirements.txt があれば pip install -r requirements.txt

4. データディレクトリの準備
   - mkdir -p data logs
   - run_monitoring / run_execution 実行時に自動作成される場合もありますが、事前に作成しておくと権限エラーを回避できます

5. .env を作成（推奨: 対話ウィザード）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
   - 自動ロードはプロジェクトルートの .env / .env.local（OS 環境変数が優先）

6. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗として扱います

使い方（主要スクリプト）
-----------------------

1) ExecutionEngine 起動（本番 / ペーパー）
- デフォルト: KABUSYS_ENV に応じた挙動
- ペーパートレード例:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - ペーパートレードは paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます
- 停止:
  - プロセスを直接止めるか、プロジェクトルートの data/stop_requested.flag を作成すると Engine が安全に停止します
- PID ファイル:
  - data/execution.pid（デフォルト）に PID を書きます

2) Monitoring 起動
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（例: export MONITOR_POLL_INTERVAL=30）
- 監視は monitoring_db のスキーマを冪等に初期化します（init_monitoring_db）
- 停止フラグ:
  - プロジェクトルートの data/stop_requested.flag を作成すると監視ループが終了します

3) .env ウィザード
- python -m kabusys.config_setup
- 対話的に入力して .env を生成・更新します

4) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗として exit 1 になります

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を利用

環境変数（主なもの）
-------------------
（詳細は kabusys/config.py を参照）

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 設定
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading の場合に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector を使う場合必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）

監視・停止フラグ
----------------
- data/stop_requested.flag: run_execution/run_monitoring の停止制御に使用
- data/kill.flag: KillSwitch（監視が問題を検出した場合に作成される停止要請フラグ）
- デフォルト PID ファイル: data/execution.pid（ExecutionEngine）

ログ
----
- setup_logging() によって stdout（StreamHandler）と日次ローテーションされたファイルハンドラ（logs/<app_name>.log）を使用します
- LOG_LEVEL / LOG_DIR でカスタマイズ可能

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定読み込み
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

パッケージ（サブディレクトリ）
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py (実装参照)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (実装参照)
- execution/
  - execution_engine.py (実装参照)
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

補足 / トラブルシューティング
----------------------------
- DB ファイル（SQLite / DuckDB）が存在しない場合、初回実行で自動作成されることが多いですが、事前に data/ ディレクトリと適切なパーミッションを用意してください。
- OpenAI を使う機能は API キーとネットワークが必要です。キー未設定時は明示的にエラーを出します（関数内でチェック）。
- validate_config.py は PyYAML がない場合、YAML の中身チェックをスキップします（警告表示）。
- プロセス優先度の設定や CPU affinity は OS により制限されるため、権限不足時は警告を出してスキップします（psutil を利用）。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

貢献・拡張
-----------
- AI モジュール、ブローカー統合、監視ルール、ポートフォリオ戦略はモジュール単位で差し替え・拡張できる設計です。
- テストや CI を追加する場合、環境変数ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うことでテスト環境を安定化できます。

以上。必要であれば、この README を英語版へ翻訳したり、より詳細な運用手順（systemd ユニット、Dockerfile、Kubernetes マニフェストなど）を追記します。どの情報を優先して追加しますか？