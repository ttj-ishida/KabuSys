KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / リサーチ / モニタリングを行うための小規模なフレームワークです。  
主要機能（信号生成・ポートフォリオ構築・発注エンジン・監視・AI を使ったニュース解析）をモジュール化しており、ローカル環境での開発・ペーパートレード・本番運用を想定した設計になっています。

主な特徴
---------
- ExecutionEngine：発注フロー（ブローカラッパー、OrderManager、RiskManager、Reconciler）を備えた実行エンジン
- Monitoring：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を監視
- Portfolio Construction：候補選定・重み計算・ポジションサイズ計算等の純粋関数群
- Research：DuckDB を使ったファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- AI モジュール：OpenAI（gpt-4o-mini）を利用したニュースセンチメント（news_nlp）／市場レジーム判定（regime_detector）
- ユーティリティ：環境設定ウィザード、設定検証 CLI、ロギング設定、プロセス優先度調整など
- ペーパートレード対応：KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、本番 DB から分離

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要パッケージ（プロジェクトの実際の requirements.txt を参照してください）
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時にあると詳細検証を行います）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env（デフォルト: プロジェクトルート/.env）を生成または更新します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env は機密情報を含むため絶対に Git にコミットしないでください。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）として扱います。

6. データディレクトリ・ログディレクトリ
   - デフォルトの DB / ログパスは .env で変更可能
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/<app_name>.log
   - 実行前に data/ および logs/ に書き込み権限があることを確認してください（多くの処理は自動でディレクトリを作成します）。

環境変数（代表）
----------------
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（デフォルト: 60）
- LOG_LEVEL / LOG_DIR: ログレベル・ログディレクトリ
- PAPER_FILL_MODE: ペーパートレード時のフィルモード ("instant" | "partial" | "never" | "reject")

使い方
------
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱いにできます。

- 実行エンジン（Execution）
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に書き込み（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動を中止します
    - 実行中に stop flag を設置するとエンジン停止処理が走ります
    - 起動時に実行ファイルは data/execution.pid に PID を書きます

- 監視ループ（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に基づいて SQLite / DuckDB に接続し SystemMonitor を定期実行
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
    - 監視は常に本番 sqlite_path（KABUSYS_ENV に依らず）を使用
    - data/stop_requested.flag を検出するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI モジュール（ニュース / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（prices_daily / raw_news 等）を受け取り、結果を DB に書き込みます

停止・キルスイッチ
-----------------
- ExecutionEngine を外部から停止させたい場合:
  - data/kill.flag を作成すると KillSwitch が発動して実行を停止します（監視が評価して書き込みます）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します
- KillSwitch の動作は監視結果（ドローダウンやポジション上限）に基づいて自動で書き込まれます

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- デフォルト設定:
  - コンソール（stdout）出力 + 日次ローテートされたファイル出力（logs/<app_name>.log）
  - ログレベルは環境変数 LOG_LEVEL、または引数で上書き可能
- ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はリポジトリの主要なモジュール／ファイルと簡単な説明です（src/kabusys を基準）。

- __init__.py
  - パッケージ初期化、バージョン定義

- config.py
  - Settings クラス: 環境変数読み込み（.env 自動ロード機能）、各種設定プロパティ

- config_setup.py
  - .env を対話式に生成・更新するウィザード

- validate_config.py
  - .env と config/*.yaml を起動前に検証する CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番／ペーパートレード対応）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- monitoring/
  - monitoring_db.py: SQLite を使った監視ログ永続化層
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: （注文滞留や約定異常検出）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - monitoring_engine.py: 各 Monitor を束ねる
  - kill_switch.py: kill.flag 操作（Execution 停止シグナル）
  - alert_manager.py: （LINE などへの通知管理：コード内で利用）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - Execution のコア実装群（ブローカー抽象化、リスク管理、注文管理など）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数計算（ロット丸め・利用率調整等）
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: モメンタム／ボラティリティ／バリュー等の計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC 計算・統計サマリ

- ai/
  - news_nlp.py: ニュースを LLM でスコアリングし ai_scores に書き込み
  - regime_detector.py: マクロ+MA による市場レジーム判定（LLM 補助）

- tools/
  - paper_verification_report.py: ペーパートレードの振る舞い検証レポート生成

- utils/
  - logging_setup.py: ログの共通設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
------------
- 本番（KABUSYS_ENV=live）環境では設定（API キー・LINE 通知先・Kill Switch の設定等）を十分に確認してください。validate_config は本番向けのガードチェックを含みます。
- .env 等に秘密情報を置く場合はアクセス管理・バックアップに注意してください。
- OpenAI に依存する機能は API キーと課金が必要であり、失敗時はフェイルセーフによりデフォルト値で継続する設計になっていますが、運用方針を明確にしてください。
- データベースファイル（DuckDB / SQLite）はバックアップポリシーを作ってください。特に本番の発注・ログは重要です。

参考コマンド一覧
----------------
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベース（src/kabusys 以下）に基づいて作成しました。追加の運用手順、依存関係の明確化（requirements.txt の整備）、ユニットテスト・CI 設定などはプロジェクトに応じて追記してください。質問や補足したい箇所があれば教えてください。