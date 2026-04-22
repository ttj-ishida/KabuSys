KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視フレームワークです。  
発注実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（DuckDB ベースのファクター計算）、およびニュース NLP / レジーム判定などの機能を備えています。  
コードは純粋関数や小さなクラス群で構成され、paper_trading（ペーパートレード）モードと live（本番）モードを切り替えて利用できます。

主な特徴
--------
- Execution
  - ExecutionEngine：ブローカーを抽象化し、発注・注文管理・リスク管理・再突合せを実行
  - paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめた MonitoringEngine
  - SQLite に監視ログ（system_status、trade_logs、risk_logs、positions、dashboard）を永続化
  - Kill Switch：ドローダウンやポジション上限を検知してフラグファイルにより ExecutionEngine を停止可能
- Portfolio Construction
  - 候補選定・重み計算（等金額 / スコアベース）
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元株丸め・aggregate cap）
- Research
  - DuckDB を利用したファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 特徴量探索・IC 計算・ランク変換ユーティリティ
- AI（OpenAI 統合）
  - ニュース NLP による銘柄別センチメントスコア（ai_scores へ書き込み）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（market_regime へ書き込み）
  - OpenAI 呼び出しはリトライ・バリデーションを備えフェイルセーフ設計
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- 設定管理
  - .env の対話式作成（config_setup.py）
  - 起動前の設定検証 CLI（validate_config.py）

前提・依存関係
--------------
- Python 3.10+
- 必須外部ライブラリ（一例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の中身を検証したい場合）
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワーク接続（本番ブローカー / OpenAI を使用する場合）

インストール（開発環境向け）
----------------------------
1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートに移動（src を PYTHONPATH に含める/パッケージ化）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の例）
   - pip install duckdb psutil openai pyyaml

設定（.env）
-----------
自動ロード: config.py がプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

推奨手順（対話式ウィザードで .env を作成）
1. python -m kabusys.config_setup
   - 対話形式で KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等を設定できます。
2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗と扱います。

重要な環境変数（代表）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使用する場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant | partial | never | reject）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

セットアップ（ディレクトリ・DB）
--------------------------------
- data/ ディレクトリを作成しておく（自動作成される箇所もありますが、手動で準備しておくと安心）
- DuckDB データベース（prices_daily、raw_financials、raw_news 等のテーブル）には別途 ETL でデータを投入する必要があります（パイプラインは本リポジトリ外の可能性あり）。
- 監視 DB（SQLite）は初回起動時に init_monitoring_db() によりテーブル生成が行われます。

使い方（主要スクリプト）
-----------------------

1) 実行エンジン（Execution）
- 本番・ペーパートレード共通起動スクリプト:
  - python -m kabusys.run_execution
- 動作:
  - Settings に応じて本番 DB / ペーパートレード DB を切替
  - BrokerClientFactory により実ブローカー／MockBroker を生成
  - data/execution.pid に PID を書く（設定による）
  - 停止は data/stop_requested.flag を作成することで行える

2) 監視ループ（Monitoring）
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
- system / trade / risk を周期的にチェックして SQLite / DuckDB に記録、必要に応じて kill.flag を書き込み実行エンジンへ停止シグナルを与える

3) 設定・検証
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]

4) ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

5) AI / リサーチ関数（ライブラリ利用）
- ニュース NLP（銘柄スコア化）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 引数 conn は duckdb connection、api_key を省略すると環境変数 OPENAI_API_KEY を使用
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- Research（ファクター等）:
  - kabusys.research.calc_momentum(conn, date), calc_volatility, calc_value など

停止・Kill Switch
-----------------
- 実行エンジンを外部から停止したい場合:
  - data/stop_requested.flag を作成すると run_execution のループは停止します
  - monitoring 側は条件を満たすと data/kill.flag を書き込み、Execution 起動時のクリーンアップや手動確認に利用できます
- KillSwitch は risk_monitor の結果（ドローダウン、ポジション上限）に基づいて動作します

ログ
----
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- デフォルトは logs/<app_name>.log に日次ローテートで保存（30日分保持）
- コンソール出力は stdout

ディレクトリ構成（主要ファイル）
-------------------------------
src/
  kabusys/
    __init__.py                 — パッケージ定義、バージョン
    config.py                   — 環境変数・Settings（自動 .env ロード含む）
    config_setup.py             — .env 対話式ウィザード
    validate_config.py          — 設定検証 CLI
    run_execution.py            — ExecutionEngine 起動スクリプト
    run_monitoring.py           — Monitoring 起動スクリプト
    tools/
      paper_verification_report.py — Paper Trading 検証レポートツール
    ai/
      news_nlp.py               — ニュース NLP（OpenAI 連携）
      regime_detector.py       — 市場レジーム判定（MA + マクロ NLP）
    research/
      factor_research.py       — ファクター計算（momentum / volatility / value）
      feature_exploration.py   — forward returns / IC / summary utilities
    portfolio/
      portfolio_builder.py     — 候補選定・重み計算
      position_sizing.py       — 発注株数計算・キャップ処理
      risk_adjustment.py       — セクター上限・レジーム乗数
    monitoring/
      monitoring_db.py         — SQLite 永続化層（テーブル初期化・CRUD）
      system_monitor.py        — システム / データ鮮度監視
      trade_monitor.py         — （注文監視ロジック）※ファイルあり
      risk_monitor.py          — ドローダウン・ポジション数監視
      kill_switch.py           — kill.flag 制御
      monitoring_engine.py     — 各 Monitor 統合ループ
      alert_manager.py         —（アラート通知ロジック）※ファイルあり
    execution/
      execution_engine.py      — ExecutionEngine（セッション実行）
      order_manager.py         — 注文管理
      order_repository.py      — 注文永続化（SQLite など）
      broker_factory.py        — BrokerClient の生成（Mock / 実ブローカー）
      reconciler.py            — 発注結果の再突合せ
      risk_manager.py          — 実行時リスク管理
    data/
      pipeline.py              — データ取得パイプライン（prices 等）※ファイルあり
      stats.py                 — 正規化ユーティリティ（zscore）
    utils/
      logging_setup.py         — ログ初期化ユーティリティ
      process_priority.py      — プロセス優先度 / CPU affinity 設定

補足・運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では設定ミスが致命的になり得るため validate_config の確認を必ず行ってください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- OpenAI API を使う機能は API キーの使用料が発生します。テスト時はモック化を推奨します（モジュール内で _call_openai_api を patch 可能）。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news など）は外部の ETL から整備する必要があります。
- process_priority.set_process_priority() は OS によって権限が必要な場合があります。失敗しても警告でスキップされます。

よく使うコマンド例
-------------------
- .env を作る（対話式）:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 監視を起動（デフォルト 60 秒間隔）:
  - python -m kabusys.run_monitoring
- 実行エンジンを起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（このリポジトリのライセンス・貢献ルールをここに記載してください。README に追記を推奨）

以上。セットアップや実行で不明点があれば、利用する環境（OS/ Python バージョン / .env の主要設定）を教えてください。具体的な起動例やトラブルシュートを支援します。