KabuSys — 日本株自動売買システム（簡易 README）
================================================================================

このリポジトリは日本株向けの自動売買 / 研究 / 監視用ユーティリティ群を集めた
Python パッケージです。モジュールは発注エンジン、モニタリング、ポートフォリオ構築、
リサーチ（ファクター計算）、AI（ニュース NLP / レジーム判定）などで構成されています。

主要ポイント（概要）
- 発注・実行: ExecutionEngine（run_execution.py）で実際の発注／ペーパートレードを実行
- 監視: SystemMonitor / TradeMonitor / RiskMonitor を periodic に実行する監視プロセス（run_monitoring.py）
- 環境設定: 対話式ウィザードで .env を作るツール（config_setup.py）
- 設定検証: 起動前に .env / config/*.yaml を検証する CLI（validate_config.py）
- 研究用: DuckDB を用いたファクター計算・特徴量探索（research パッケージ）
- AI: OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）

機能一覧
- 実行モード切替: KABUSYS_ENV により development / paper_trading / live をサポート
  - paper_trading では MockBroker を利用し、本番 DB と分離して data/paper_trading.db に記録
- 監視サービス
  - システム資源（CPU/メモリ/ディスク）・Execution プロセスの死活チェック
  - 注文・約定ログ監視（滞留注文・異常約定の検出）
  - ドローダウン・ポジション上限などのリスク監視と Kill Switch（data/kill.flag）発動
  - アラート送信（LINE などの設定をサポート）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、リスクベースの株数決定、セクターキャップ適用
- 研究機能（DuckDB）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI 機能（OpenAI）
  - ニュース集合を LLM に投げて銘柄ごとのセンチメントスコアを ai_scores テーブルへ書込
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定
- 運用支援ツール
  - .env 対話ウィザード、設定検証、ペーパートレード検証レポート生成

セットアップ手順（ローカル開発向け）
1. 要件（推奨）
   - Python 3.10+
   - 必要なライブラリ: duckdb, psutil, openai, PyYAML（YAML検証用）など
     例:
       pip install duckdb psutil openai PyYAML

   必要に応じて virtualenv / venv を使って仮想環境を作成してください。

2. プロジェクトルートで .env の用意
   - 対話式ウィザードを推奨:
       python -m kabusys.config_setup
     ウィザードは .env を作成・更新します。
   - 主要な環境変数（抜粋）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など
   - 既存の .env がなければ上記ウィザードで作成してください。
   - 注意: .env は絶対にリポジトリにコミットしないでください。

3. ディレクトリ・DB 初期化
   - データディレクトリ（data）やログディレクトリ（logs）は通常自動作成されますが、
     必要に応じて手動で作成しても問題ありません。
   - SQLite / DuckDB ファイルは初回起動時にテーブル作成を行うコードが用意されています。

4. 設定検証（任意）
       python -m kabusys.validate_config
   - 警告も失敗とする厳格モード:
       python -m kabusys.validate_config --strict

使い方（主要コマンド）
- 監視ループ起動
    MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト: 60）。
  - 監視は .env の KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
  - 停止方法: プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが
    次のサイクルで検知して終了します（または Ctrl+C）。

- 実行エンジン（ExecutionEngine）起動
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、data/paper_trading.db に
    発注ログ等を記録します（本番 DB と完全分離）。
  - 実行中に停止させるには data/stop_requested.flag を作成するか、Kill Switch（監視が
    kill.flag を書き込んだ場合）でエンジンを停止できます。
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書き込まれます。

- 環境設定ウィザード
    python -m kabusys.config_setup
  - 対話式で .env を作成・更新します。

- 設定検証
    python -m kabusys.validate_config
  - 必須環境変数や config/*.yaml の存在／パースをチェックします。

- ペーパートレード検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションで指定可能。
  - 稼働率・注文成功率・P95 レイテンシなどを集計して PASS/FAIL を判定します。

- AI / 研究 API（ライブラリ呼び出し）
  - ニュース NLP（銘柄スコア生成）
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key=...)
  - レジーム判定
      from kabusys.ai.regime_detector import score_regime
  - 研究関数（例）
      from kabusys.research import calc_momentum, calc_volatility, calc_value

運用時のフラグ / ファイル
- data/kill.flag: KillSwitch によって作られるファイル。存在すると ExecutionEngine に停止シグナルを送る目的で使用。
- data/stop_requested.flag: run_monitoring / run_execution がループを抜けるための外部停止要求ファイル。
- data/execution.pid: ExecutionEngine の PID ファイル（デフォルト）。

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して行われます。
- デフォルト出力先:
  - コンソール（stdout）
  - logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
- 環境変数 LOG_DIR や LOG_LEVEL で上書き可能。

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live)
- OPENAI_API_KEY（AI 機能で必要）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
- LOG_LEVEL / LOG_DIR
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ヘルパ
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — 発注エンジン関連（OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（注）上記はリポジトリに含まれる主なファイル／モジュールの概要です。実際の実装は
細分化されたモジュール群（order_manager, broker_factory, execution_engine 等）によって構成されています。

運用上の注意事項
- KABUSYS_ENV=live を使用する場合は設定値（API トークン・通知設定・Kill Switch の挙動等）を
  十分に確認してください。本番モードでは実際に発注が行われます。
- .env は機密情報を含むため、絶対に Git 等へコミットしないでください。
- OpenAI を利用する機能は API キーが必須です。API 利用に伴うコストとレイテンシを考慮してください。
- DB（SQLite / DuckDB）やログの保存先ディスク容量を監視してください（監視モジュールはディスク使用率も記録します）。
- run_monitoring / run_execution は stop flag や kill.flag による外部制御を前提とした設計です。手動停止（Ctrl+C）も可能です。

トラブルシューティング
- 設定検証:
    python -m kabusys.validate_config
  まずこれで警告・エラーを解消してください。
- プロセス優先度設定や CPU affinity は psutil の権限制約で失敗することがあります（ログに警告が出ますが起動は継続します）。
- DuckDB / SQLite 接続エラーやテーブル欠損が出た場合、初期化処理（init_monitoring_db 等）が実行されるかログを確認してください。

貢献・拡張
- strategy / execution ロジックはモジュール化されているため、戦略アルゴリズムやブローカ連携を差し替えやすく設計されています。
- 将来的な拡張候補:
  - 銘柄ごとの lot_size をマスターに持たせる
  - 代替 LLM のサポート・API のバックエンド差し替え
  - 分散処理 / コンテナ運用（Dockerfile / systemd ユニット等の追加）

最後に
この README はコードベースの主要な使い方と設計意図のサマリです。各モジュール内の docstring やコメントも詳細な仕様を示しているため、
実装を理解・運用する際は該当モジュールのソースを参照してください。必要ならば、この README をベースにデプロイ手順書や運用 Runbook を作成することを推奨します。