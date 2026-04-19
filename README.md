KabuSys — 日本株自動売買フレームワーク
=================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージです。  
本リポジトリは以下の主要機能を持ち、実運用・検証（ペーパートレード）・研究ワークフローをサポートします。

主な特徴
--------
- 実行エンジンと監視（Execution / Monitoring）プロセスの起動スクリプトを提供
  - run_execution: 発注エンジン（本番 / ペーパートレード切替対応）
  - run_monitoring: システム状態・データ鮮度・取引ログ等のポーリング監視
- 設定管理・ウィザード
  - .env 自動読み込み、対話式 .env 生成（config_setup）、起動前検証（validate_config）
- 監視永続化
  - SQLite に監視ログ・トレードログ・ダッシュボードを永続化（monitoring_db）
- ポートフォリオ構築モジュール（銘柄選定、重み計算、位置サイズ決定、セクター制限 等）
- 研究用モジュール（DuckDB を使ったファクター計算、特徴量解析）
- AI 支援モジュール（OpenAI を利用したニュースセンチメント評価、レジーム判定）
- 各種ユーティリティ（ロギングセットアップ、プロセス優先度設定、ツール類）
- ペーパートレード検証レポート生成ツール

必須環境変数（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う場合（news_nlp/regime_detector）
- KABUSYS_ENV — 実行モード: development / paper_trading / live（省略時: development）

その他よく使う環境変数
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード時の専用 SQLite）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring で上書き可）
- PAPER_FILL_MODE（ペーパートレードの約定振る舞い: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（実行開始時に data/kill.flag を自動クリアするか）

セットアップ手順（開発環境）
--------------------------
1. リポジトリをクローンし、作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   注: requirements.txt がない場合は少なくとも次を入れてください:
     - duckdb, psutil, openai（AI 機能利用時）、PyYAML（設定検証で任意）、pandas 等は任意

4. 初期設定（対話式ウィザード）
   - python -m kabusys.config_setup
     → .env を対話式で作成します（.env は絶対に Gitへコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
     → 必須環境変数や config/*.yaml の存在をチェックできます。--strict を使うと警告も失敗扱いになります。

起動・使い方
------------

共通
- ログ: デフォルトは logs/ ディレクトリ配下に app_name.log（日次ローテート、30日保持）
- データディレクトリ: data/ 配下に DB・フラグファイル等を格納（デフォルト）

ExecutionEngine 起動（本番 / ペーパー）
- 本番（KABUSYS_ENV=live）:
  - 環境変数を設定後:
    - python -m kabusys.run_execution
- ペーパートレード:
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。

監視プロセス起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings に従い、監視用の sqlite_path を使用して永続化します。

プロセス停止 / Kill スイッチ
- 停止フラグ: data/stop_requested.flag
  - run_execution / run_monitoring はこのファイルの存在を検知して安全終了します（冪等）。
- Kill Switch（自動停止）:
  - リスク監視により KILL 条件が満たされた場合、data/kill.flag に理由が書き込まれます。ExecutionEngine はこのファイルを検出して停止する設計です。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動消去しますが、本番では 0 を推奨します。

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

研究・分析 API（DuckDB）
- DuckDB 接続を渡してファクター計算や特徴量解析が行えます:
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary
- DuckDB ファイルは DUCKDB_PATH で指定（デフォルト data/kabusys.duckdb）

AI 機能
- ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - api_key を渡すか環境変数 OPENAI_API_KEY を設定してください
  - raw_news / news_symbols テーブルを参照し、ai_scores テーブルへ書き込みます
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

設定ファイル・自動読み込みの仕組み
- config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索し、自動で .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- Settings クラスから各種設定値へアクセスできます（settings = Settings()／settings.jquants_refresh_token 等）。

ディレクトリ構成（抜粋）
----------------------
src/
  kabusys/
    __init__.py
    config.py                  — 環境変数 / 設定読み込み
    config_setup.py            — .env 対話式ウィザード
    validate_config.py         — 起動前設定検証 CLI
    run_execution.py           — ExecutionEngine 起動スクリプト
    run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
    tools/
      paper_verification_report.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    monitoring/
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py         (この README では省略一覧)
      risk_monitor.py
      kill_switch.py
    execution/                  (実際のブローカー/エンジン実装を含む)
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
    utils/
      logging_setup.py
      process_priority.py
      __init__.py
    research/, portfolio/, data/ などその他サブパッケージ

（注）上記はこの README に含まれるファイルの抜粋です。リポジトリ内にさらに補助スクリプトやデータ定義が存在する可能性があります。

実運用時の注意点
----------------
- .env の管理:
  - センシティブな鍵やトークンは .env に保存することが多いですが、決して Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では各種安全措置（LINE 通知、Kill Switch、ログレベルの設定等）を十分に確認してください。
- データベースのパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）をプロダクション用の安全な場所に設定してください。
- OpenAI を使う部分は API コストが発生します。API キーの権限・使用料に注意してください。
- psutil によるプロセス優先度・CPU affinity 設定は OS に依存します。権限不足だと警告が出ますが処理自体は継続します。

開発者向けメモ
----------------
- ロギングは kabusys.utils.logging_setup.setup_logging を経由して統一しています。スクリプト起動時に呼び出すことを想定しています。
- MonitoringDB は監視用テーブルの初期化とマイグレーション（列の追加等）を行います。init_monitoring_db() は冪等です。
- ペーパートレードは本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH を使用）。
- テスト時は OpenAI 呼び出し箇所（news_nlp/regime_detector）の内部 API 呼び出しラッパーをモックすることを推奨します。

よくあるコマンド
----------------
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

ライセンス
----------
- この README に示すコードベースのライセンス表記はリポジトリに従ってください（本 README はドキュメント目的の要約です）。

サポート / 追加情報
-------------------
実装の詳細や追加ファイル（data ディレクトリ、config/*.yaml、Broker 実装など）はリポジトリ内のドキュメント（例: PortfolioConstruction.md, StrategyModel.md）があれば参照してください。動作や実行方法で不明点があれば、具体的なファイル名・実行ログを添えて質問してください。