README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なフレームワークです。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理のランタイム
- 監視（Monitoring）: システム状態・注文状態・リスクをポーリングしてログ・アラート・Kill Switch を管理
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ決定・セクター制限などの純粋関数群
- 研究（Research）: ファクター計算・特徴量探索（DuckDB を利用）
- AI 補助モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- 設定管理ツール: .env ウィザード & 設定検証 CLI、Paper Trading 向けレポート生成ツール

主な設計方針は「本番 DB とペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API 失敗時にスキップ）」です。

主な機能
--------
- run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録）
- run_monitoring.py: SystemMonitor を定期ポーリングする起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定ウィザード: python -m kabusys.config_setup で .env を対話的に作成/更新
- 設定検証: python -m kabusys.validate_config で環境変数 / config/*.yaml の妥当性チェック
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report で検証用レポートを出力
- ポートフォリオ関連純粋関数群: 候補選定、重み付け、単元丸め、リスク調整、ポジションサイズ計算
- AI モジュール: ニュースセンチメント scoring（OpenAI）と市場レジーム判定（DuckDB のデータと LLM を組み合わせる）
- 監視 DB 層: SQLite（monitoring.db）にシステム状態 / 取引ログ / リスクログ / ダッシュボードを永続化

セットアップ手順
----------------
注意: 以下はリポジトリをローカルで動かすための一般的な手順です。プロダクション環境では追加の運用手順が必要です。

1. リポジトリをクローンして作業ディレクトリに入る
   - git clone <repo-url>
   - cd <repo-root>

2. Python 環境の準備
   - 推奨: Python 3.10+ の仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須例:
     - pip install duckdb psutil openai
   - 任意（設定検証で YAML を検証したい場合）:
     - pip install PyYAML
   - 実際の requirements.txt がある場合はそれを使用してください:
     - pip install -r requirements.txt

4. 初期ディレクトリ・ファイルの準備
   - data/ ディレクトリ（デフォルト DB やフラグファイル用）
     - mkdir -p data logs
   - ログディレクトリ: デフォルトは logs/
   - SQLite / DuckDB ファイルは自動作成されます（デフォルト: data/monitoring.db, data/kabusys.duckdb）

5. .env の作成（推奨）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参考にしてください）
   - 自動ロード: config モジュールはプロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

6. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります

基本的な環境変数（抜粋）
------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI コールを行う場合に必要
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant/partial/never/reject）

使い方
------
主要なスクリプトと実行例:

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution

  実行時に data/execution.pid が作られ、data/stop_requested.flag を作成すると停止リクエストを送れます。
  - ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用し、実際のブローカー呼び出しをモックします。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます（デフォルト 60 秒）。
  - Monitoring は Settings に従って SQLite（monitoring DB）および DuckDB に接続します。監視は常に本番の sqlite_path を参照します（KABUSYS_ENV にかかわらず）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（ライブラリ関数として利用）
  - 例（Python REPL / スクリプトで直接呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
      import duckdb, datetime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")

停止方法・フラグ
----------------
- 停止要求（外部からプロセスを優雅に停止したい場合）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します
- Kill Switch（自動停止判定）
  - KillSwitch は risk_monitor などからトリガーされると data/kill.flag を書き込みます
  - ExecutionEngine は kill.flag の存在を参照して停止します（本番環境では特に注意）

ログ
---
- ログはデフォルトで logs/ ディレクトリに日次ローテートで保存されます（app_name に応じてファイル名を決定: execution.log, monitoring.log 等）。
- ログの出力先は環境変数 LOG_DIR、レベルは LOG_LEVEL で変更できます。

ディレクトリ構成
----------------
主要なファイル・ディレクトリと簡単な説明:

- src/kabusys/
  - __init__.py                         : パッケージ定義・バージョン
  - run_execution.py                    : ExecutionEngine 起動スクリプト
  - run_monitoring.py                   : SystemMonitor ポーリング起動スクリプト
  - config.py                           : Settings（環境変数/.env 読み込み・検証）
  - config_setup.py                     : .env 対話式ウィザード
  - validate_config.py                  : 設定検証 CLI
  - tools/
    - paper_verification_report.py      : Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py                       : ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py                : マーケットレジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py                  : SQLite ベースの永続化層（system_status, trade_logs 等）
    - system_monitor.py                 : サーバー状態・データ鮮度チェック
    - trade_monitor.py                  : （取引関連監視ロジック）
    - risk_monitor.py                   : ドローダウン・ポジション上限チェック
    - monitoring_engine.py              : 各 Monitor を束ねるエンジン
    - kill_switch.py                    : kill.flag を書き込むユーティリティ
    - alert_manager.py                  : （通知送信：LINE など、実装場所）
  - execution/
    - execution_engine.py               : ExecutionEngine 本体（発注・セッション管理）
    - order_manager.py                  : 注文管理
    - order_repository.py               : 注文永続化
    - risk_manager.py                   : 発注前リスク判定
    - broker_factory.py                 : BrokerClient の生成（Mock / 実ブローカーの分岐）
    - reconciler.py                     : ブローカーと DB の整合性確保
  - portfolio/
    - portfolio_builder.py              : 候補選定・重み計算
    - position_sizing.py                : 発注株数計算
    - risk_adjustment.py                : セクター制限・レジーム乗数
  - research/
    - factor_research.py                : Momentum / Value / Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py            : forward returns / IC / 統計サマリー等
  - utils/
    - logging_setup.py                  : 共通ログ設定ユーティリティ
    - process_priority.py               : プロセス優先度・CPU affinity 設定
  - data/（実行時に生成されることが想定）
    - monitoring.db / paper_trading.db / kabusys.duckdb
    - stop_requested.flag, execution.pid, kill.flag
  - config/
    - *.yaml（system_config.yaml, strategy_config.yaml 等） — サンプル/テンプレートを配置

補足・運用ノート
----------------
- monitoring は MONITOR_POLL_INTERVAL（秒）環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
- 設定の自動ロードはプロジェクトルートの .env / .env.local を読み込みます。OS 環境変数が優先されます。
- Paper Trading と本番 DB は明確に分離されています（settings.is_paper による切替）。Paper Trading では data/paper_trading.db を使用して実運用 DB に影響を与えません。
- OpenAI を使う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API 呼び出し失敗時はフェイルセーフで処理をスキップまたはデフォルト値を用いる設計です。
- 本 README はコードベースの説明を簡潔にまとめたものです。各モジュールの実装コメントや docstring を参照すると詳細な振る舞いが確認できます。

ライセンス・貢献
----------------
- ライセンス情報や貢献ルールがリポジトリルートにある場合はそちらに従ってください。

もし README に追記したい項目（例：requirements.txt の実内容、実行時のログサンプル、より詳細な運用手順、Docker 化手順など）があれば教えてください。必要に応じて追記・整備します。