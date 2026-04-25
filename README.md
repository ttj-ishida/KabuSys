KabuSys — 日本株自動売買システム
================================

本ドキュメントはリポジトリ内の主要なスクリプト／モジュールの使い方やセットアップ手順、ディレクトリ構成をまとめた README です。開発・ペーパートレード・本番運用それぞれを想定した設計になっています。

概要
----
KabuSys は日本株の自動売買フレームワークです。主な役割は以下の通りです。

- 実行エンジン（ExecutionEngine）: 発注ロジック・リスク管理・注文管理を実行
- 監視（Monitoring）: システム状態、注文状態、リスク指標をポーリングしてログ＆アラートを発行、必要に応じて Kill Switch を発動
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制約適用等
- リサーチ/ファクター計算: DuckDB の時系列データを用いた因子計算・検証
- AI モジュール: OpenAI を用いたニュースのセンチメント評価 / 市場レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証ツール 等

主な機能一覧
-------------
- 実行環境分離:
  - KABUSYS_ENV によるモード切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- 監視:
  - system_status / trade_logs / risk_logs / positions / dashboard の SQLite 永続化
  - 定期ポーリング、アラート発行、Kill Switch（data/kill.flag）による外部停止
- ポートフォリオ構築:
  - 候補選定（score ベース等）、等配分・スコア加重配分、リスクベースのポジションサイズ計算
  - セクター集中制限、レジームに応じた投下資金乗数
- リサーチ:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - forward return・IC・統計サマリ等のユーティリティ
- AI（OpenAI）:
  - ニュース記事の銘柄別センチメント算出（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA 乖離から市場レジーム判定（market_regime テーブル）
  - API エラーに対するリトライ・フェイルセーフ実装
- ツール:
  - .env 対話式生成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.10+ を想定（typing 構文などを使用）
- SQLite は標準ライブラリに含まれます

1. リポジトリをチェックアウト
   - パッケージを適切に配置していること（例: setup が不要なローカル開発なら src を PYTHONPATH に含める／パッケージインストール）

2. 依存パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定検証で YAML 検証を行う場合に任意）
   - 例:
     pip install duckdb psutil openai PyYAML

3. 環境変数 (.env) の作成
   - 対話式ウィザードで .env を作成・更新できます:
     python -m kabusys.config_setup
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - その他（代表例）:
     - KABUSYS_ENV (development / paper_trading / live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - LOG_LEVEL (DEBUG/INFO/...)
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant/partial/never/reject）
   - 生成後は設定検証を実行:
     python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります。

4. データディレクトリ等の作成
   - ログディレクトリはデフォルトで logs/
   - DB 等は data/ に置かれる想定（.env のパスを参照）
   - 必要に応じてディレクトリを作成しておくとエラーが減ります（ただしログユーティリティは自動作成も試みます）

基本的な使い方
--------------

1. 実行エンジンの起動（Execution）
   - 本番/開発/ペーパーは KABUSYS_ENV に従う
   - 起動:
     python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH または data/paper_trading.db に書き込みます
     - 実行中は PID ファイル（デフォルト data/execution.pid）が生成されます
     - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl+C）を送る

2. 監視ループの起動（Monitoring）
   - 起動:
     python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
   - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使います（環境にかかわらず）
   - 停止フラグ: data/stop_requested.flag を配置すると監視ループが終了します
   - 監視の流れ:
     - SystemMonitor, TradeMonitor, RiskMonitor を順に呼び出し、必要であれば KillSwitch を書き込む（data/kill.flag）

3. Paper Trading 検証レポート生成
   - レポートを生成して標準出力へ出すツール:
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
   - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定します

4. AI 機能
   - ニュースセンチメントのスコア付け:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - OPENAI_API_KEY（または明示的な api_key 引数）が必要
   - 市場レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - API 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 等で継続）を備えています

停止・Kill Switch
-----------------
- 外部的に実行エンジンや監視を停止したい場合:
  - Kill Switch（実行エンジンを強制停止させる）: data/kill.flag を書き込む（通常は MonitoringEngine が自動で書き込む）
  - stop_requested.flag: run_execution / run_monitoring 側がポーリングで検出すると安全に終了します
- run_execution は起動時に stop flag が立っていると起動を停止します

ログ
----
- 共通のログ設定ユーティリティを使用しています（kabusys.utils.logging_setup.setup_logging）
- デフォルトログディレクトリ: logs/
- 各アプリケーション（execution / monitoring など）は logs/<app_name>.log に日次ローテーションで保存されます
- 標準出力も StreamHandler で stdout に出力されます

主要ファイル / ディレクトリ構成
-----------------------------

リポジトリの src/kabusys 以下の主要な構成を抜粋します（実際のファイル数は多いです）。

- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — 環境変数/設定管理（.env 自動ロード・Settings クラス）
  - config_setup.py            — .env を対話式に生成するウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py         — （実装ファイルあり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （アラート送信の抽象化）
  - execution/
    - execution_engine.py      — 実行エンジン本体
    - broker_factory.py        — ブローカクライアント生成（実際の API / Mock の切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュースの LLM スコアリング
    - regime_detector.py       — マクロ + ETF MA で市場レジーム判定

注意事項 / 運用上のポイント
--------------------------
- 環境 (KABUSYS_ENV) を正しく設定してください。live では取り扱いに注意が必要な設定（LINE通知の有無や KILL_FLAG_CLEAR_ON_START 等）があります。
- .env は機密情報（API トークン等）を含むため絶対に Git にコミットしないでください。
- OpenAI API を利用する機能は外部 API 呼び出しのため、API キーと利用制限に注意してください。失敗時のフォールバックが実装されていますが、費用やレート制限に留意してください。
- DuckDB / SQLite のパスは Settings で参照されます。運用時は定期的なバックアップ・保守を検討してください。
- ログや DB のディレクトリ作成に失敗した場合、ログはコンソール出力のみになるなどのフォールバックがあります。起動ログを確認して問題の有無を必ず確認してください。

補足: よく使うコマンドまとめ
---------------------------
- .env を作る（対話ウィザード）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # 30 秒間隔に変更

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はコードベースから抽出した利用方法の概要です。実運用前に必ず設定検証（kabusys.validate_config）を行い、ログ出力や DB の動作を監視しながら段階的に移行してください。追加の実装詳細や設計文書（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクト内にあることを想定しています。必要であればそれらの参照も行ってください。