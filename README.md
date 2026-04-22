KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／リサーチ基盤の一部実装です。
主に次の責務を持つモジュール群を含みます：実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を用いたニュース NLP / レジーム判定、及びユーティリティ類。

この README ではプロジェクト概要、機能、セットアップ手順、主要コンポーネントの起動方法、ディレクトリ構成を日本語で説明します。

プロジェクト概要
---------------
KabuSys は日本株の自動売買および研究用のコード群です。主な設計方針は以下の通りです。
- 実行ロジックと監視を分離：ExecutionEngine と MonitoringEngine を別プロセスで実行
- 本番／ペーパー（paper_trading）環境を環境変数で切り替え可能
- DuckDB を分析用、SQLite を監視／トレードログ用に使用
- LLM（OpenAI）を使ったニュースセンチメント / 市場レジーム判定機能を提供
- pure 関数で表現されたポートフォリオ構築・ポジションサイズ計算のユーティリティ

主な機能一覧
-------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、ペーパー専用 SQLite（data/paper_trading.db）へ記録
  - 本番では実際のブローカークライアントを使用
  - PID ファイル作成 / stop フラグの監視で安全停止

- Monitoring（run_monitoring.py / monitoring/*）
  - システムヘルス（CPU/メモリ/ディスク）、Execution プロセス生存確認、データ鮮度チェック
  - トレードログ・リスクログ・ダッシュボードの永続化（SQLite）
  - Kill Switch（一定条件で data/kill.flag を書き込み、ExecutionEngine 停止を要求）
  - アラート管理フック（AlertManager による通知）

- ポートフォリオ構築（portfolio/*）
  - 候補選定、等ウェイト／スコア加重、スコアベースの重み計算
  - セクター制限、レジーム乗数（risk_adjustment）
  - 株数決定・単元丸め・aggregate cap の実装（position_sizing）

- 研究用関数（research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）計測、ファクター統計サマリ

- AI モジュール（ai/*）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を算出・保存

- ユーティリティ
  - ロギング設定（utils/logging_setup.py）: stdout + 日次ローテートファイル
  - プロセス優先度設定（utils/process_priority.py）
  - 環境設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

前提・依存ライブラリ
-------------------
最低限の依存（抜粋）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を使う場合）

インストール例（仮）:
- 仮想環境の作成
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)
- 必要パッケージのインストール
  - pip install duckdb psutil openai PyYAML
（パッケージ化/requirements.txt はこのリポジトリに含まれていないため、必要に応じて上記を調整してください）

セットアップ手順（クイックスタート）
-----------------------------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成して依存をインストール（上記参照）

3. .env の作成
   - python -m kabusys.config_setup
   - ウィザード形式で J-Quants トークンや Kabu API パスワード等を入力して .env を生成できます。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
   - 任意・デフォルト:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - LOG_LEVEL (default: INFO)
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の成行約定動作

4. 設定検証（起動前のチェック）
   - python -m kabusys.validate_config
   - 警告も失敗とみなす場合は --strict を付ける

5. 実行（例）
   - ペーパー取引で Execution を動かす:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - ExecutionEngine は data/paper_trading.db を使用し、本番 DB と分離されます
   - 監視プロセスを起動:
     - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
   - Paper Trading 検証レポート:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - --db で SQLite ファイルを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

停止・Kill スイッチ
-------------------
- プロセスを強制停止させるにはプロジェクトルートの data/kill.flag を作成します（KillSwitch がこれを検知して Execution を停止する設計）。
- run_*.py で使用している停止フラグ: data/stop_requested.flag（停停止用のグローバルフラグ）
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）

ロギング・DB パス
-----------------
- ログ: デフォルト logs/<app_name>.log（utils.logging_setup が設定）
- DuckDB: data/kabusys.duckdb（分析用）
- SQLite 監視 DB: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

主要な起動 / 利用コマンドまとめ
-----------------------------
- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ExecutionEngine（本番 / paper_trading）
  - python -m kabusys.run_execution

- Monitoring（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # 例: ポーリング間隔 30 秒

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 研究用 / AI モジュール（Python API）
  - Python スクリプト内でインポートして利用可能:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    - from kabusys.ai import score_news  # AI スコアリング（OpenAI API キーが必要）

環境変数（主なもの）
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行モード:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development

- データ / ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - LOG_DIR（ログ保存先）

- Monitoring/制御:
  - MONITOR_POLL_INTERVAL（run_monitoring でポーリング秒数を上書き）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START

- AI:
  - OPENAI_API_KEY（ai.news_nlp / regime_detector で使用）

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールの抜粋ツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                     — 環境変数・.env 自動読み込みロジック / Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前の設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py          — 市場レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ / 永続化層
    - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py            — （トレード検査コード）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 制御
    - monitoring_engine.py        — 複数モニタを束ねるエンジン
    - alert_manager.py            — （アラート管理）
  - portfolio/
    - portfolio_builder.py        — 候補選定 / 重み計算
    - position_sizing.py          — 株数決定 / aggregate cap
    - risk_adjustment.py          — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py          — Momentum / Volatility / Value 等
    - feature_exploration.py      — 将来リターン / IC / 統計
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / affinity 設定

注意事項・運用上のポイント
-----------------------
- .env に機密情報（API トークン等）を格納する場合は絶対に Git にコミットしないでください（config_setup.py のヘッダにも同旨記載あり）。
- KABUSYS_ENV=live の場合は設定ミスが重大な被害を生む可能性があるため validate_config の実行と LINE 通知設定等の確認を強く推奨します。
- OpenAI を利用する機能は API 利用料が発生します。ローカルテストでは環境変数 OPENAI_API_KEY の設定に注意してください。
- monitoring_db.init_monitoring_db はマイグレーションを簡易サポートしています（例: カラム追加時の ALTER TABLE）。
- utils.logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップし、標準出力のみで継続します。

開発・拡張のヒント
-------------------
- 研究用途の関数群（research/*）は DuckDB 接続を受け取り SQL と Python で処理する設計です。DuckDB に prices_daily / raw_financials 等をロードすればローカルで解析できます。
- ExecutionEngine の具体的な実装（ブローカークライアント・注文管理等）は execution パッケージに実装されているので、Mock と実ブローカーを切り替える BrokerClientFactory を拡張できます。
- AI 周りはリトライやフェイルセーフが組み込まれていますが、実運用ではより厳格なレート制御やコスト管理が必要です。

お問い合わせ・貢献
-----------------
- 本 README はコードベース（src/kabusys/*.py）を基に作成しています。実行環境や運用ポリシーに合わせて .env を適切に設定してください。
- バグ報告や機能提案は Issue を立ててください。Pull Request は歓迎します。

以上がこのリポジトリの主要な説明です。実際に動かす際は validate_config → run_monitoring/run_execution の順で実行し、ログと DB を確認しながら進めてください。