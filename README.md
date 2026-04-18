README
=====

概要
---
KabuSys は日本株の自動売買および関連ツール群のライブラリ/スクリプト群です。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ / ファクター計算、AI を使ったニュース・レジーム判定、ペーパートレード検証レポート生成などの主要コンポーネントが含まれます。

主な設計方針：
- 本番データとペーパートレードの分離（SQLite DB を用途ごとに分ける）
- DuckDB を使った分析用データストア（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を用いたニュース NLP 機能（任意）
- 環境変数 / .env による設定管理と対話式ウィザード
- ログはコンソール + 日次ローテートファイルに出力

機能一覧
-------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）
- Monitoring（run_monitoring.py / monitoring モジュール）
  - システム稼働監視（CPU / メモリ / ディスク / プロセス）
  - 注文・約定ログ監視（stale orders / 異常約定）
  - リスク監視（ドローダウン / ポジション上限）と Kill Switch（kill.flag）
  - アラート管理（AlertManager と連携）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選択、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC 計算・統計サマリー
- AI 機能（kabusys.ai）
  - ニュース NLP による銘柄センチメント（ai_scores）書き込み
  - マクロニュース + ETF MA による市場レジーム判定（market_regime）
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

前提・依存関係
---------------
主な Python ライブラリ（例）:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config で YAML 内容検証を行う場合）

インストール例:
- 仮想環境作成:
  python -m venv .venv
  source .venv/bin/activate
- 必要パッケージのインストール例:
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動

2. .env の作成（対話式ウィザード推奨）
   - 対話式ウィザードを実行:
     python -m kabusys.config_setup
   - 生成される .env は絶対に Git にコミットしないでください（シークレット情報を含む）。

3. 設定検証（任意）
   - 基本的な環境変数や config/*.yaml を事前検証:
     python -m kabusys.validate_config
   - 警告をエラー扱いにする（CI 等）:
     python -m kabusys.validate_config --strict

4. 必要な DB / ディレクトリ
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 実行時に自動作成されますが、権限等を確認してください。

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ファイル:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト data/paper_trading.db）
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
- ログ:
  - LOG_LEVEL（例: INFO, DEBUG）
  - LOG_DIR（デフォルト logs/）
- AI:
  - OPENAI_API_KEY（AI 機能使用時に必要）
- 監視ループ間隔:
  - MONITOR_POLL_INTERVAL（秒。run_monitoring でオーバーライド、デフォルト 60）
- .env 自動読み込みの無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（実行例）
----------------

- ExecutionEngine（通常実行）
  - 本番 / ペーパートレードは KABUSYS_ENV で切り替え
  - 実行:
    python -m kabusys.run_execution

- Monitoring（監視ループ）
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（SQLite パス、期間指定可能）:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  または環境変数:
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report

- AI 機能（ニューススコア、レジーム判定）はライブラリ API を直接呼ぶ:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  ※ OpenAI API キーは OPENAI_API_KEY 環境変数で渡すか、関数引数で指定します。

運用上の注意
-------------
- run_execution / run_monitoring は起動直後にプロセス優先度を "high" に設定しようとします（set_process_priority）。権限が必要な場合は失敗してもログに警告が残るだけで継続します。
- Kill Switch（data/kill.flag）を作ることで ExecutionEngine を安全に停止できます。kill.flag は KillSwitch（monitoring）によって作成されます。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env / .env.local を自動読み込みします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング:
  - 共通の setup_logging() を使ってコンソールと logs/<app_name>.log に日次ローテーションで出力します。
- データベースマイグレーション:
  - monitoring DB は init_monitoring_db() により必要なテーブル・カラムを冪等に作成します（既存 DB へのマイグレーション処理あり）。

ディレクトリ構成（簡易）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env ロード・Settings クラス
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリングループ起動スクリプト

- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py      — マクロ + ETF MA によるレジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py       — システム・データ鮮度監視
  - trade_monitor.py        — （注文監視ロジック）
  - risk_monitor.py         — ドローダウン／ポジション監視
  - kill_switch.py          — kill.flag 制御
  - monitoring_engine.py    — 各 monitor を束ねるエンジン
  - alert_manager.py        — （アラート送信ロジック）
- execution/
  - execution_engine.py     — ExecutionEngine 実装（主ループ等）
  - broker_factory.py       — BrokerClientFactory（本番 / モック分岐）
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
- data/
  - pipeline.py             — DuckDB / prices データパイプライン（get_last_price_date 等）
  - stats.py                — 正規化ユーティリティ等
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（上記は代表的なファイル一覧です。実際のツリーはリポジトリの内容を参照してください）

開発・貢献
----------
- .env にシークレットを含めないでください。README などにトークンを貼らないこと。
- 新しい設定項目を追加したら config_setup.py と .env.example（存在する場合）を更新してください。
- validate_config.py に検証ロジックを追加して事前チェックを強化してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報が別途ある場合はリポジトリの LICENSE を参照してください。

補足
----
- 実運用では KABUSYS_ENV=live の設定に非常に注意してください。validate_config の警告や LINE 通知の設定などを確認してください。
- OpenAI を利用する機能は API コストとレイテンシが発生します。API キーの権限管理、レート制限、ログの取り扱いに注意してください。

もし README に追記してほしい内容（例: 実行フローの図、特定スクリプトのパラメータ仕様、より詳細な依存関係リストなど）があれば教えてください。README を拡張して反映します。