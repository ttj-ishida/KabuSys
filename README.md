KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
主な機能は「信号生成 → ポートフォリオ構築 → 発注管理（ExecutionEngine）」「監視・アラート」「研究用ファクター計算」「ニュースNLP による AI スコアリング」などで、DuckDB / SQLite を使ったデータ分析・ログ永続化を行います。

注記:
- パッケージ名: kabusys（src/kabusys）
- バージョン: 0.1.0（src/kabusys/__init__.py）

主な機能一覧
--------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading の場合は MockBroker を使用し DB を分離）
  - プロセス優先度を High に設定、PID ファイル管理、停止フラグ監視
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、取引ログ・リスク監視
  - Kill Switch（条件満足で data/kill.flag を作成して ExecutionEngine 停止）
  - アラート管理（LINE 等の連携用設定を想定）
- Portfolio モジュール（portfolio パッケージ）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム補正
- Research（research パッケージ）
  - Momentum / Volatility / Value 等のファクター計算、Forward returns、IC 計算、統計サマリ
  - DuckDB 接続を受けて SQL と Python で計算
- AI モジュール（ai）
  - news_nlp: OpenAI を使ったニュースのセンチメントスコアリング（ai_scores テーブルへの書込み）
  - regime_detector: ETF の MA とマクロニュースの LLM 評価を合成して市場レジーム判定
- 便利スクリプト
  - config_setup.py: .env の対話的生成・更新ウィザード
  - validate_config.py: 環境設定の事前検証 CLI
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成
- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテーションファイル）
  - process_priority: プラットフォームを吸収する優先度 / CPU affinity 設定

セットアップ手順
----------------
前提
- Python 3.9+（ソースは型注釈を使用）
- SQLite（標準ライブラリで利用）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML を使う場合は任意）

推奨インストール例:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

環境変数設定
- .env をプロジェクトルートに作成（config_setup.py で対話的に生成推奨）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要な環境変数（抜粋）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（monitoring 用 DB。monitoring は常に本番 sqlite_path を使用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
  - OPENAI_API_KEY: OpenAI を使う場合に必須
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
- 自動読み込み:
  - .env / .env.local は自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

使い方（主要コマンド）
--------------------
- .env を作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗とする）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（CLI スクリプト）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag をクリアする設定があるため注意
    - 停止: data/stop_requested.flag を作成するとエンジンは終了します
    - PID ファイル: data/execution.pid（デフォルト）

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します
  - 停止: data/stop_requested.flag を作成すると監視ループは終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI 機能（Python から実行例）
  - news_nlp.score_news や regime_detector.score_regime は DuckDB 接続を受ける関数です。例:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026,4,1), api_key="...")

ログ / ファイル
----------------
- ログ:
  - デフォルトは logs/<app_name>.log に日次ローテートで出力（30日分保持）
  - setup_logging() により stdout とファイルの両方へ出力
- DB / 制御ファイル（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID: data/execution.pid
  - stop フラグ: data/stop_requested.flag（両スクリプトで起動/停止判定に使用）
  - kill flag: data/kill.flag（KillSwitch による ExecutionEngine 停止指令）
- 注意:
  - monitoring は監視用 DB に対して永続化（init_monitoring_db）を行います（テーブル/マイグレーション対応あり）
  - ExecutionEngine は paper_trading 時に本番 DB と完全に分離する設計

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / Settings 管理（.env 自動ロード機能含む）
    - config_setup.py         — .env 対話式ウィザード
    - validate_config.py      — 起動前の設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py      — ログ設定ユーティリティ
      - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py      — SQLite 監視ログ層（テーブル作成・読み書き）
      - monitoring_engine.py  — 各モニタの束ねとポーリング
      - system_monitor.py     — システム状態・データ鮮度監視
      - trade_monitor.py      — 発注ログ・注文滞留など監視（実装参照）
      - risk_monitor.py       — ドローダウン・ポジション上限監視
      - kill_switch.py        — kill.flag 管理
      - alert_manager.py      — アラート送信（LINE 等。実装参照）
    - execution/
      - execution_engine.py   — 実行エンジン本体（EngineConfig 等）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py    — レジーム判定（MA + LLM）
    - tools/
      - paper_verification_report.py
    - data/                   — 実行時生成されるファイル（DB、PID、flags 等）

設計上の注意点 / 運用上のヒント
--------------------------------
- 本番運用時は KABUSYS_ENV=live を使用。validate_config で各種警告を確認してください。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に既存の kill.flag を自動クリアしますが、本番では 0 を推奨します（誤動作による復帰を防ぐため）。
- Monitoring は本番の monitoring DB（SQLITE_PATH）を参照します。paper_trading モードでも monitoring DB は本番 DB を参照する設計です（監視の独立性維持）。
- OpenAI API を使用する機能は API キーが必須（OPENAI_API_KEY）であり、コスト・レート制限に注意してください。API 呼び出しはリトライ・バックオフ実装あり。
- ログディレクトリ作成に失敗した場合はコンソール出力のみ継続します。ログディレクトリの書込み権限を確認してください。
- プロセス優先度設定はプラットフォーム依存（psutil を使って Windows/Linux/Mac を抽象化）。権限不足で設定に失敗することがあります（警告でスキップ）。

開発・拡張ポイント（参考）
-------------------------
- ストラテジーの増減、ブローカークライアントの実装差し替え、単元株（lot）を銘柄ごとに扱う拡張などを想定した設計になっています。
- DuckDB を用いたファクター計算／研究部分は SQL と組み合わせることで高速に処理可能です。
- AI 関連は JSON Mode を利用したレスポンス検証とクリップ処理を行い、フェイルセーフにより API 障害時はスコア 0.0 等で継続します。

ライセンス / 貢献
-----------------
- 本リポジトリにはライセンスファイルが含まれていないため、利用・配布の際は著作権者に確認してください。
- バグ報告・改善提案は Issue/PR を通じて行ってください。

付録（よく使うコマンドまとめ）
-----------------------------
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

以上。README の内容に関して補足や、より詳細な設定サンプル（.env.example）や運用手順書が必要であれば教えてください。