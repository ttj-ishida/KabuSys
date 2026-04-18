KabuSys
=======

日本株向けの自動売買 / 研究フレームワークの簡易実装です。  
取引実行（ExecutionEngine）、監視（Monitoring）、ファクター計算・研究、ポートフォリオ構築、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

プロジェクト概要
---------------
- 名前: KabuSys
- 目的: 日本株自動売買システムのコアロジック（発注管理、リスク監視、ポートフォリオ構築、ファクター計算、ニュースセンチメント評価など）を提供するライブラリ兼起動スクリプト群。
- 設計方針:
  - 本番/ペーパートレードを区別して DB を分離可能
  - ログ・監視・Kill Switch 等の運用機能を備える
  - DuckDB を使った分析・研究モジュール（外部 API を直接叩かない設計）
  - OpenAI を用いたニュースセンチメント / レジーム判定機能（APIキー必須、フェイルセーフ設計）

主な機能一覧
--------------
- ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
  - KABUSYS_ENV に応じて実際のブローカーまたは MockBroker を選択
  - paper_trading 環境では専用 SQLite（デフォルト: data/paper_trading.db）を使用
  - プロセス優先度設定、PID ファイル管理、停止フラグ検知

- Monitoring / MonitoringEngine (src/kabusys/monitoring/*)
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン、ポジション数上限監視
  - KillSwitch: 監視結果により data/kill.flag を書き込み ExecutionEngine を停止可能
  - 監視ログの永続化（SQLite）と簡易 DB マイグレーション機能 (monitoring_db)

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 候補選定、等分配・スコア加重配分、リスク調整（セクター制限・レジーム乗数）
  - 発注株数算出（単元丸め、利用可能現金の集約キャップ）

- 研究モジュール (src/kabusys/research/*)
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC 計算、統計サマリ等（DuckDB を用いた SQL ベース処理）

- AI モジュール (src/kabusys/ai/*)
  - news_nlp: raw_news を LLM（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存
  - regime_detector: ETF（1321）MA 乖離 + マクロニュースセンチメントで日次レジーム判定
  - OpenAI API 呼び出しはリトライやフォールバック（失敗時は安全なデフォルト）を持つ

- 運用ユーティリティ
  - 環境設定ウィザード: .env を対話式で作成 (src/kabusys/config_setup.py)
  - 設定検証 CLI: .env + config/*.yaml の事前検証 (src/kabusys/validate_config.py)
  - Paper Trading 検証レポート生成ツール (src/kabusys/tools/paper_verification_report.py)
  - ロギング設定ユーティリティ、プロセス優先度設定ユーティリティなど

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - duckdb
   - psutil
   - openai
   - PyYAML（config の YAML 検証を使う場合）
   例:
     pip install duckdb psutil openai PyYAML

   （requirements.txt が無い場合は上記を個別にインストールしてください）

4. 環境変数 (.env) を作成
   - 対話式ウィザードを使う:
       python -m kabusys.config_setup
   - 主要な必須環境変数:
       JQUANTS_REFRESH_TOKEN (必須)
       KABU_API_PASSWORD      (必須)
     任意 / 設定項目:
       KABUSYS_ENV            (development | paper_trading | live) — デフォルト development
       DUCKDB_PATH            (デフォルト data/kabusys.duckdb)
       SQLITE_PATH            (デフォルト data/monitoring.db)
       PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
       LOG_LEVEL
       LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート用)
       OPENAI_API_KEY         (AI 機能を使う場合必須)
       PAPER_FILL_MODE        (instant|partial|never|reject)
       KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか)

5. 設定の静的検証（推奨）
   - python -m kabusys.validate_config
   - 問題がある場合はエラー/警告が表示されます。--strict を付けると警告も失敗扱いになります。

6. ディレクトリ権限・ログディレクトリ
   - デフォルトで logs/ と data/ を使用します。必要に応じて作成・権限を確認してください。
   - ログは logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリが作成できないとファイル出力は無効になり、コンソールのみに出力します）。

基本的な使い方
--------------

- ExecutionEngine 起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定します（psutil を使用）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ paper_trading 用 DB に記録され、本番 DB と完全分離されます。
    - 停止シグナル:
      - data/stop_requested.flag を作成すると run_execution のループが検知して安全に停止します（run_execution はこのフラグを監視）。
      - 監視側からの Kill Switch は data/kill.flag を書き込み ExecutionEngine 停止を誘発します。
    - PID ファイルは data/execution.pid（設定により変更可）に書かれます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - デフォルトで 60 秒間隔のポーリングを行います。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒単位）。
    - Monitoring は KABUSYS_ENV にかかわらず production（settings.sqlite_path） の sqlite を使用して監視ログを保存します（運用観点で監視 DB を分離していないため）。
    - 同様にプロセス優先度を "high" に設定します。
    - 停止は data/stop_requested.flag を作成することで行えます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力内容: 稼働率、注文成功率、送信率、P95 レイテンシなど。基準値未達なら FAIL として表示。

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を .env または環境変数に設定してください。
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して実行
  - ai/regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - モデル: gpt-4o-mini を想定（設定に応じて変更可能）
    - API 呼び出しは 429 / タイムアウト / 5xx をリトライし、失敗時は安全なデフォルトで継続する（例: macro_sentiment=0.0）。

運用上のファイル・フラグ
-------------------
- data/stop_requested.flag
  - run_monitoring / run_execution のポーリングループを停止するためのローカルファイルフラグ（存在するとループが終了）。

- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine に対する停止要求を表す（監視が検出して書き込む）。
  - clear: KillSwitch.clear() を呼ぶか手動で削除。

- PID ファイル
  - data/execution.pid（デフォルト。Settings.pid_file_path で変更可能）

データベース
------------
- DuckDB: デフォルト data/kabusys.duckdb（分析・研究）
- SQLite (監視): デフォルト data/monitoring.db（monitoring_db がテーブルを作成・マイグレーションを行う）
- Paper trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

- monitoring_db が作成する主なテーブル:
  - system_status, trade_logs, positions, risk_logs, dashboard
  - 既存スキーマに不足カラムがあれば init_monitoring_db() が簡易マイグレーション（列追加）を行います。

ディレクトリ構成（主要ファイル）
----------------------------
以下はソースツリーの主なファイルと役割（src/kabusys 以下）:

- __init__.py
  - パッケージ定義、バージョン

- run_execution.py
  - ExecutionEngine 起動スクリプト

- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）

- config.py
  - 環境変数の読み込み・ラップ（Settings クラス）
  - 自動でプロジェクトルートの .env, .env.local をロード（無効化可能）

- config_setup.py
  - .env の対話式ウィザード作成スクリプト

- validate_config.py
  - 設定検証 CLI（.env と config/*.yaml の存在・基本検証）

- utils/
  - logging_setup.py: 統一的なロギング設定（stdout + 日次ローテート）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: 監視用 SQLite の永続化層（テーブル作成・読み書き）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py (監視関連各種)
    （SystemMonitor はデータ鮮度確認のため DuckDB を参照する）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注・注文管理・リスク管理のコアロジック（Engine 実装）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定、重み付け、ポジションサイズ計算、セクターキャップ等

- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を使ったファクター計算・将来リターン / IC 等の分析関数

- ai/
  - news_nlp.py, regime_detector.py
  - OpenAI を用いたニュースセンチメント・レジーム判定

- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート出力ツール

運用上の注意点 / ベストプラクティス
--------------------------------
- 本番運用前に必ず python -m kabusys.validate_config で設定を検証してください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI API キーは安全に管理してください（AI 機能を有効にする場合）。
- Paper trading と live の DB は分離して使用してください（Settings は paper_trading 用の別ファイルを参照するようになっています）。
- 監視・Kill Switch 設計により、危険な状態時に自動で ExecutionEngine を止めることができます。kill.flag の自動クリアは本番では無効（KILL_FLAG_CLEAR_ON_START=0 を推奨）にしてください。

問い合わせ・拡張
----------------
- 各モジュールは比較的モジュール化されており、ブローカー実装の差し替えやポートフォリオ戦略の拡張、AI モデルの変更などを容易に行えます。
- DuckDB 上のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）に合わせたデータ投入スクリプトや ETL は別途必要です。

以上が本リポジトリ（KabuSys）の概要、セットアップ、基本的な使い方、および主要ファイル構成です。必要であれば、run_execution/run_monitoring の起動オプション、settings の詳細、個別モジュールの API 仕様（関数シグネチャ）についてのドキュメントも作成します。どの部分を詳しく出力しますか？