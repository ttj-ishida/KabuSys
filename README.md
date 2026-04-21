KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買／リサーチ／モニタリングを目的とした小規模なコードベースです。
主な機能は次のとおりです。

- 戦略のためのファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（発注・リスク管理・注文整合処理） — paper_trading（モックブローカー）対応
- Monitoring（システム稼働性・注文ログ・リスク監視・Kill Switch）
- AI 補助機能（ニュースのセンチメント解析によるスコアリング、レジーム判定。OpenAI API利用）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、ペーパートレード検証レポート）

特徴
----
- 環境変数 / .env による設定管理（config.py）
- DuckDB を分析用 DB、SQLite を監視 / 発注ログ用 DB に使用（デフォルトファイルは data/ 配下）
- Paper Trading と Live を明確に分離（paper_trading 時は専用 SQLite を使用）
- ロギングはコンソール + 日次ローテーションファイル（logs/）で管理
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP・レジーム判定機能（APIキー必須）
- フェイルセーフ設計（API 失敗時の許容、DB マイグレーションを自動実施、冪等性など）

セットアップ
-----------

前提
- Python 3.10+
- Git

依存パッケージ（代表例）
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証オプション）

インストール（例）
1. レポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
   pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

初期設定 (.env)
1. 対話式ウィザードで .env を生成:
   python -m kabusys.config_setup

   - J-Quants / kabuステーション のトークン等の必須項目を入力します。
   - paper_trading と live の切り替えは KABUSYS_ENV で行います（development / paper_trading / live）。

2. 設定検証:
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い

データディレクトリ
- デフォルトで以下のファイルパスを使用します（.env で上書き可能）:
  - DuckDB: data/kabusys.duckdb (環境変数: DUCKDB_PATH)
  - SQLite (監視): data/monitoring.db (SQLITE_PATH)
  - SQLite (paper trading): data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - ログ: logs/
  - Kill flag / stop flag / pid: data/kill.flag, data/stop_requested.flag, data/execution.pid
- 初回起動時にディレクトリがなければ自動作成されることが多いですが、事前に data/ や logs/ を作成しておくと安心です。

使い方 / 実行例
----------------

主要な実行スクリプトはパッケージモジュールとして起動できます。

- ExecutionEngine（発注エンジン）起動:
  python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録します。本番 DB と完全分離されます。
  - 実行前に .env の KABUSYS_ENV を適切に設定してください。
  - プロセス優先度は起動時に "high" に設定されます（psutil による。権限によっては設定に失敗する場合があります）。
  - 停止は data/stop_requested.flag の作成で行えます（スクリプトはこのフラグを検知して停止します）。

- Monitoring（監視ループ）起動:
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満は無効扱いでデフォルトに戻ります。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視データは本番 DB に記録）。

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  - --from YYYY-MM-DD: レポート開始日
  - --to YYYY-MM-DD: レポート終了日
  - --db PATH: SQLite DB パス（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

AI 機能
- ニュース NLP（銘柄ごとのセンチメントを ai_scores に書き込む）
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY）
  - batch サイズやトークン上限に配慮した設計・リトライロジックあり

- レジーム判定（マクロセンチメント + ETF MA 乖離）:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要

注意:
- OpenAI を使用する機能は API 利用料が発生します。OPENAI_API_KEY を .env に設定してください。
- AI 呼び出しは失敗時でもフェイルセーフ（スコアを 0 にして継続）となる実装です。

ログ
----
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- デフォルトログディレクトリ: logs/
- ログレベルは .env の LOG_LEVEL または setup_logging の引数で設定できます。

設定項目（代表）
----------------
必須（少なくとも以下は設定する必要があります）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な設定（.env で管理）
- KABUSYS_ENV: development / paper_trading / live
- DUCKDB_PATH: 分析用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LOG_LEVEL, LOG_DIR
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意、アラート通知用）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔）

ディレクトリ構成（抜粋）
---------------------
以下はコードベースの主要ファイル・モジュール構成（src/kabusys 配下）です。実際のツリーはプロジェクトルート配下に src/ や config/、data/、logs/ が存在します。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / .env 自動読み込み・Settings
    - config_setup.py          # .env 対話式ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py            # （trade_monitor 実装あり）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py            # （アラート送信機能）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/              # 実行時に生成される（data/kabusys.duckdb, monitoring.db など）
    - logs/              # ログ格納先（デフォルト）

補足 / 運用メモ
---------------
- Kill Switch:
  - risk_monitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で停止を促す仕組みがあります。
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成・カラム追加を行います。

- 権限:
  - プロセス優先度や CPU affinity の設定は OS ごとに振る舞いが異なります。権限不足時は警告を出してスキップされます。

- テスト:
  - AI 呼び出しや外部 API 呼び出しはモック化してテスト可能な設計になっています（内部で分離された呼び出し関数を patch する想定）。

ライセンス / その他
-------------------
- この README はコードベースの主要設計・利用法のサマリです。詳細な仕様や設計ドキュメント（PortfolioConstruction.md 等）がプロジェクト内にあれば合わせて参照してください。

問題がある箇所や README に追加したい情報（例: CI / デプロイ手順、より詳しい設定例）があれば教えてください。必要に応じて追記します。