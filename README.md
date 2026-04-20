KabuSys — 日本株自動売買システム
=============================

このリポジトリは、日本株自動売買システム「KabuSys」のコアライブラリ群です。  
本 README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

※ 本 README はソースコード（src/kabusys 以下）を基に作成しています。

プロジェクト概要
---------------
KabuSys は以下の責務を持つモジュール群で構成された自動売買基盤です。

- 注文実行エンジン（ExecutionEngine）: 発注・約定・リスク管理を統合して取引セッションを実行
- 監視（Monitoring）: システム稼働状況・注文状況・リスク指標をポーリングしてログ・アラート・Kill Switch を制御
- ポートフォリオ構築（Portfolio）: 候補選定・重み付け・ポジションサイズ算出・セクター制約
- リサーチ（Research）: DuckDB を使ったファクター計算・特徴量探索・IC 計算
- AI モジュール（news_nlp, regime_detector）: OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- ユーティリティ: 設定管理、ログ設定、プロセス優先度設定等
- ツール: ペーパートレード検証レポート生成など

主な機能一覧
--------------
- 環境設定管理 (.env 自動読み込み / config_setup ウィザード)
- 設定検証 CLI（kabusys.validate_config）
- ExecutionEngine（本番・ペーパートレード切替）
  - KABUSYS_ENV=paper_trading の場合は専用 MockBroker を使用し DB を分離
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor）
  - データ鮮度、プロセスの生存、ディスク/CPU/メモリ監視
  - アラート／Kill Switch（data/kill.flag）
- Portfolio構築ユーティリティ（候補選定・重みづけ・株数決定）
- Research（DuckDB を使ったファクター計算・将来リターン・IC）
- AI：OpenAI を用いたニュースセンチメント（ai.news_nlp）とレジーム判定（ai.regime_detector）
- ロギング: 標準出力 + 日次ローテートファイル（logs/<app>.log）
- 小物ツール: Paper Trading 検証レポート生成スクリプト

前提 / 依存関係
----------------
（プロジェクトに requirements.txt が含まれていないため最低限必要な主要ライブラリを列挙します）

- Python 3.9+（コードは型注釈を含む modern な Python を前提）
- pip/venv 等の環境
- パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（任意、config 検証時に YAML 検証を有効化する場合）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワーク接続（AI モジュールを使う場合、OpenAI API）

セットアップ手順
----------------

1. リポジトリをクローン / ソースを入手

   git clone ... などでソースを取得し、ワークディレクトリへ移動します。

2. 仮想環境を作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数（.env）を準備

   対話式ウィザードで .env を作成できます：

   python -m kabusys.config_setup

   生成された .env はプロジェクトルートに保存されます（.env は Git 管理しないでください）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用の DB)
   - OPENAI_API_KEY (AI モジュール利用時に必要)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)

5. 設定検証（任意）

   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

   このコマンドは .env や config/*.yaml の欠落や不整合を検出します（PyYAML が無い場合 YAML 検証はスキップされます）。

6. データディレクトリの確認

   デフォルトで使用されるファイル・ディレクトリ:
   - data/monitoring.db (SQLite; 監視ログ)
   - data/paper_trading.db (ペーパートレード用 DB)
   - data/execution.pid （実行中の PID 保存）
   - data/kill.flag （監視が Kill Switch を書く場合）
   - logs/ （ログファイルを出力）

基本的な使い方
--------------

- ExecutionEngine を起動

  本番／ペーパーは KABUSYS_ENV で制御されます。

  python -m kabusys.run_execution

  振る舞い:
  - 起動時にプロセス優先度を "high" に設定します（可能な場合）。
  - paper_trading 環境では MockBrokerClient を使用し、紙トレード用 DB (PAPER_TRADING_SQLITE_PATH) を使います。
  - data/stop_requested.flag が存在すると起動を中止または実行中に停止します。

- Monitoring を起動

  python -m kabusys.run_monitoring

  オプション:
  - MONITOR_POLL_INTERVAL=30 等でポーリング間隔を上書き（デフォルト 60 秒）
  動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を初期化してポーリングを行い、監視 DB（settings.sqlite_path）へ永続化します。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依らず）。

- Kill Switch 操作（監視→実行停止）

  - 監視モジュールはリスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させる設計です。
  - 手動で停止させたい場合は data/kill.flag を作成することでほぼ同じ効果を得られます（ただし実行中のプロセスの挙動は Engine 実装に依存します）。

- Paper Trading 検証レポート生成

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールの利用（例）

  - ニュースセンチメントをスコア化して DB に書く:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。

  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

その他の注意点・オプション
------------------------
- ロギング: すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼んで stdout と logs/<app>.log に出力します。ログディレクトリは環境変数 LOG_DIR で変更可。
- プロセス優先度: 起動時に set_process_priority("high") が呼ばれます（psutil の権限や OS に依存して失敗する場合があります）。
- 自動 .env ロード: config モジュールはプロジェクトルートの .env と .env.local を自動で読み込みます。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベース初期化: monitoring_db.init_monitoring_db はテーブル作成と最低限のマイグレーション（列追加）を行います。Execution 起動時に呼ばれますので通常は手動マイグレーションは不要です。
- ペーパートレードと本番 DB は分離されるよう設計されています。KABUSYS_ENV=paper_trading により paper_sqlite_path が使用されます。
- config/*.yaml ファイル（system_config.yaml, strategy_config.yaml 等）は一部モジュールで参照される想定です（validate_config で存在チェックを行います）。サンプル生成スクリプトがある場合はそちらを利用してください（README 検出できず）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割の抜粋です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB レイヤ
    - system_monitor.py      — システム稼働・データ鮮度監視
    - trade_monitor.py       — 注文監視（存在 / 滞留 / 約定異常など）※詳細はソース参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — アラート送信（LINE など）※存在を参照
  - execution/
    - execution_engine.py    — 実取引エンジン（EngineConfig, run_session 等）
    - order_manager.py       — 注文管理
    - order_repository.py    — DB に対する注文履歴永続化
    - reconciler.py          — ブローカーと DB の整合性を保つ
    - risk_manager.py        — 発注前リスク制御（RiskConfig）
    - broker_factory.py      — ブローカークライアント生成（実 / モック切替）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数算出・配分・単元丸め
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュースを OpenAI でスコア化し ai_scores に書込
    - regime_detector.py     — ma200 + マクロニュースでレジーム判定
  - data/ (実行時に作成されることが多い)
    - monitoring.db (default)
    - paper_trading.db (paper)
    - kill.flag
    - execution.pid
  - logs/
    - execution.log
    - monitoring.log
    - ...（日次ローテートで管理）

開発者向けメモ
----------------
- モジュールはできるだけ副作用を抑えており、ユニットテストしやすい純粋関数群（portfolio, research 等）と、DB/外部 API 呼び出しを行う手続き群に分離されています。
- AI API 呼び出しのラッパーはテスト時に差し替え可能（_call_openai_api を patch する等）。
- DuckDB をデータ分析用に使う設計で、prices_daily / raw_financials などのテーブルを参照して計算を行います。
- 本番環境では KABUSYS_ENV=live を設定し、LINE 等のアラート送信設定を必ず確認してください（validate_config による警告あり）。

ライセンス / 注意
----------------
- .env には機密情報（API キー等）が含まれます。絶対に Git にコミットしないでください。
- ライブトレード用に使用する場合は事前に十分なレビューとバックテスト、運用手順（Kill Switch 等）の確認を行ってください。

お問い合わせ / 貢献
-------------------
コードベースについて補足のためのドキュメントや追加説明が必要であれば、どのファイル／機能についての README を拡張すべきか指示してください。README の補完（コマンド例、環境例、CI／デプロイ手順など）を追加できます。