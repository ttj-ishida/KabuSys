KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買フレームワーク（KabuSys）の一部実装です。
主要機能は、戦略／ポートフォリオ構築、実行エンジン（ExecutionEngine）、監視（Monitoring）、研究用ファンクション、AI を使ったニュースセンチメント/レジーム判定などを含みます。

以下は本コードベースの概要、機能、セットアップと実行方法、ディレクトリ構成の説明です。

プロジェクト概要
---------------
KabuSys は次の役割を分離して実装した自動売買基盤です。

- Execution（ExecutionEngine）: 発注ロジック、注文管理、リスク管理、発注先ブローカーの抽象化
- Monitoring（監視）: システム稼働、データ鮮度、注文状態、ドローダウン等を定期チェックしてアラートや Kill Switch を発動
- Portfolio（選定・配分・サイズ決定）: シグナルに基づく候補選定、重み計算、株数決定（単元丸め含む）
- Research（ファクター・特徴量解析）: DuckDB を使ったファクター計算、将来リターンやIC評価、統計サマリ
- AI（ニュース NLP / レジーム判定）: OpenAI を利用したニュースセンチメント/レジーム判定のスコアリング
- Tools（ユーティリティ）: ペーパートレード検証レポート生成など

主に DuckDB（分析）と SQLite（監視・ペーパートレード用ログ）を永続化に使用します。
環境変数・.env による設定管理を行い、.env の自動ロード機構を備えています。

主な機能一覧
--------------
- run_execution.py: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading.db に記録（本番 DB と分離）
  - 停止制御: data/stop_requested.flag / data/execution.pid を利用
- run_monitoring.py: SystemMonitor のポーリング起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境に依存せず）
- monitoring: 各種モニタ（SystemMonitor, TradeMonitor, RiskMonitor）と MonitoringEngine、KillSwitch、永続化層（monitoring_db）
- portfolio: 候補選定、重み付け、ポジションサイジング、セクター制約、レジーム乗数
- research: DuckDB を用いたファクター計算（momentum/volatility/value 等）と特徴量解析（IC、統計）
- ai:
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄毎のセンチメント（ai_scores）を書き込む
  - regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を判定・記録
- tools:
  - paper_verification_report: ペーパートレード DB を解析し検証レポートを出力
- config_setup.py: 対話式ウィザードで .env を生成・更新
- validate_config.py: .env や config/*.yaml の事前チェック（--strict オプションあり）
- utils:
  - logging_setup: 統一的なログ設定（stdout と 日次ローテーションファイル）
  - process_priority: プロセス優先度 / CPU affinity のユーティリティ

セットアップ手順
----------------
前提:
- Python 3.10 以上（型注釈の union 表現などを使用）
- SQLite は標準で利用可能
- システムによっては psutil のインストールにビルドツールが必要

1. リポジトリをクローン
   - git clone <このリポジトリ>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要な Python パッケージをインストール
   - 基本的な依存（例）
     pip install duckdb psutil openai
   - 追加（設定検証で YAML を使う場合）
     pip install pyyaml
   - （実運用やブローカークライアントが別に必要な場合、それらの依存を追加してください）

4. .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - or 手動で .env を作成（ルートに配置）
   - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env を自動ロードします。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意だが強く推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

主な必須環境変数（.env に設定）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV（development | paper_trading | live） — デフォルト development
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/…）

使い方
--------
基本的なコマンド例（ルートで実行）:

1. 実行エンジン（ExecutionEngine）を起動
   - 本番/開発/ペーパートレードは KABUSYS_ENV に依存します。
   - python -m kabusys.run_execution
   - ペーパートレード環境の例:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   停止・制御:
   - ExecutionEngine は data/stop_requested.flag を監視して安全に終了します。
   - 実行中の PID は data/execution.pid に書き込まれます。

2. 監視プロセスの起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定できます（例: MONITOR_POLL_INTERVAL=30）。
   - 監視は Settings.sqlite_path（通常は data/monitoring.db）を使用して永続化します。

3. .env を生成・編集
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

6. 研究・AI モジュールの利用（ライブラリとしてインポート）
   - 例: duckdb 接続を与えてファクター計算
     from kabusys.research import calc_momentum
   - AI:
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="...")

ログとデータ
- ログ: デフォルト logs/<app_name>.log（app_name は "execution" や "monitoring" など）
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に出力
- 永続化:
  - DuckDB: data/kabusys.duckdb（分析データ）
  - SQLite（監視）: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading で分離）
- Kill Switch:
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（monitoring のルールで書かれる）。

設定ローディングの注意
- config.py はプロジェクトルートを検出し .env / .env.local を自動ロードします（OS 環境変数が優先）。
- 自動ロードを無効にする場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な挙動と安全設計
- ExecutionEngine と Monitoring は stop flag（data/stop_requested.flag）を用いてプロセスの外部停止をサポート
- Paper Trading は本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH）
- AI 呼び出しはリトライ・エラーハンドリング・部分成功の保護（部分書き込み）を考慮
- monitoring_db は最低限のテーブル作成・マイグレーション機能を備え、冪等に初期化可能

ディレクトリ構成
----------------
（リポジトリルート /src を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動ロード）
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定、等重/スコア重み
    - position_sizing.py            — 株数計算・制約・丸め
    - risk_adjustment.py            — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — momentum/volatility/value ファクター
    - feature_exploration.py       — 将来リターン、IC、統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（OpenAI）
    - regime_detector.py           — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py            — （trade 関連監視; ファイル内に実装あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py            — （アラート送信機構; 実装に応じて）
  - utils/
    - __init__.py
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - portfolio/, research/, ai/ 等にテスト可能な純粋関数群が多数含まれます。

補足ドキュメント・注意点
----------------------
- Python バージョン: 3.10 以上を推奨（型ヒントの構文使用のため）
- OpenAI の利用:
  - OPENAI_API_KEY を .env に設定または score_news / score_regime の api_key 引数で渡してください
  - API コールはリトライロジックを持ちますが、API 料金やレート制限に注意
- ログ出力:
  - logs ディレクトリが作成できない場合はコンソール出力のみで継続します
- 実運用時:
  - KABUSYS_ENV=live の場合、LINE 通知設定や Kill Switch の挙動を事前に確認してください
  - validate_config.py のライブ向けのガードをよく確認すること（LINE 未設定や KILL_FLAG_CLEAR_ON_START 等）

ライセンス / 貢献
-----------------
（このリポジトリのライセンス情報や貢献ガイドラインがある場合に追記してください）

以上がこのコードベースの主要な README 情報です。README に追加したい内容（例: 具体的な環境変数の .env.example、詳細な実行フロー図、サンプルデータの準備方法など）があれば指示ください。