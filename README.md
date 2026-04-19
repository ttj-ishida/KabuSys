KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・モニタリングを行う小規模なシステム群です。  
主要な機能は「戦略（ファクター計算・ポートフォリオ構築）」「実行エンジン（発注/リスク管理）」「監視/アラート」「AI 支援（ニュース NLP / レジーム判定）」「Research ツール群」です。  
コードはモジュール化されており、コマンドラインから各コンポーネントを起動できます。

主な特徴
--------
- 実行環境切替（development / paper_trading / live）
  - paper_trading では MockBrokerClient を使い、本番 DB と分離された SQLite に記録
- モニタリング機能
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログ、リスクイベント、ダッシュボードを SQLite に永続化
  - Kill Switch（条件達成で data/kill.flag を書き、ExecutionEngine を停止）
- ExecutionEngine（発注／注文管理／リスク管理／再整合）
  - リスクルール（最大ポジション比率、利用率、ドローダウン等）
- ポートフォリオ構築ライブラリ（候補選定・重み付け・サイズ決定・セクター制約）
- Research（DuckDB を用いたファクター計算・将来リターン・IC 計算等）
- AI モジュール
  - ニュースのセンチメントを OpenAI でスコアリング（ai_scores テーブルへ書き込み）
  - マクロ＋ETF MA を組み合わせた市場レジーム判定
- ユーティリティ
  - .env 対話ウィザード（config_setup）、設定検証 CLI（validate_config）
  - Paper Trading 用検証レポート生成ツール

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の構文や機能を使用）
- SQLite は標準ライブラリで利用
- 推奨パッケージ: duckdb, psutil, openai, PyYAML（設定検証で任意）

1. リポジトリをクローン / ソースを取得
   - ソースツリーには src/kabusys 以下のモジュールがあります。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - 設定検証で YAML チェックを使う場合: pip install PyYAML

4. .env を用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくはルートに .env を作成。重要な環境変数:
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 任意/推奨:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
       - SQLITE_PATH — デフォルト: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
       - LOG_LEVEL — デフォルト: INFO
       - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート用（任意）
       - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)（本番では 0 推奨）
       - OPENAI_API_KEY — AI モジュール利用時に必要
       - PAPER_FILL_MODE — paper_trading 時の約定モード（instant | partial | never | reject）

   - 自動ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml がある場所）から .env, .env.local を自動読み込みします。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. ディレクトリ作成（任意）
   - data/ および logs/ は実行時に自動作成されますが、必要に応じて事前に作成して権限を調整してください。

使い方（主要コマンド）
--------------------
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（監視は環境に依存しない）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みます
  - 起動中に data/stop_requested.flag を作成するとエンジンを停止します
  - 実行中の PID は data/execution.pid に書き込まれます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（DB パスを明示）

- AI モジュール（プログラム呼び出し）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、DB のテーブル（raw_news, news_symbols, prices_daily, 等）を参照します。api_key は OPENAI_API_KEY 環境変数で代替可能。

監視 / 停止フラグについて
-------------------------
- Kill Switch:
  - 条件（ドローダウン超過、ポジション上限超過等）が満たされると data/kill.flag が書かれ、ExecutionEngine 側で停止判断に使われます。
  - KillSwitch.clear() により起動時に kill.flag を削除するオプション（KILL_FLAG_CLEAR_ON_START）。
- stop_requested.flag:
  - run_monitoring と run_execution は data/stop_requested.flag の存在を見てループを終了します。手動停止時に利用できます。

重要な設定（抜粋）
-----------------
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker で安全に挙動を検証可能
  - live: 実際に発注が行われるため注意
- PAPER_FILL_MODE（paper_trading 時の約定挙動）:
  - instant | partial | never | reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: データベースファイルパス
- OPENAI_API_KEY: AI モジュール利用時に必要

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/.env の読み込みと Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブパッケージ（主要モジュール）
- kabusys/execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 実際の発注・注文管理・リスク管理ロジック（発注側）
- kabusys/monitoring/
  - monitoring_db.py         — SQLite の永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py        — システム状態・データ鮮度のチェック
  - trade_monitor.py         — 注文の整合性 / 約定異常チェック（概念上）
  - risk_monitor.py          — ドローダウン・ポジション上限チェック
  - kill_switch.py           — kill.flag を書くロジック
  - monitoring_engine.py     — 各 Monitor を束ねるループ
  - alert_manager.py         — （アラート送信：LINE 等）（詳細は実装を参照）
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み計算・株数決定・セクター制約
- kabusys/research/
  - factor_research.py, feature_exploration.py
  - ファクター計算・将来リターン・IC・統計サマリ
- kabusys/ai/
  - news_nlp.py              — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py       — ETF MA とマクロセンチメントを合成してレジーム判定
- kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- kabusys/utils/
  - logging_setup.py         — 統一ロギング設定
  - process_priority.py      — OS 横断のプロセス優先度設定（psutil を利用）
- kabusys/monitoring/monitoring_db.py — DB 初期化・簡易マイグレーション含む

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config は live 時に追加警告を出します。
- .env と秘密情報は絶対に Git にコミットしないでください。
- OpenAI API の呼び出しはコストとレイテンシに注意。AI モジュールはリトライ・フォールバックロジックを持ちますが、APIキーの管理を徹底してください。
- psutil を使ったプロセス優先度設定は権限不足で失敗することがあり、その場合は警告ログにより通知されます。

開発・拡張ガイド
----------------
- DuckDB（分析データ）は SQL ベースで簡単にクエリ可能です。research モジュールは DuckDB 接続を受け取り純粋関数で処理を行います。
- AI モジュールは外部 API 呼び出し部を小さくまとめてあるため、テスト時は該当関数をモックして動作確認できます。
- monitoring_db.init_monitoring_db はマイグレーション（既存カラムの追加）を内包しているため、既存 DB の互換性に配慮しています。

トラブルシューティング
---------------------
- ログが出ない / ファイルが作れない:
  - logs/ または data/ ディレクトリの権限を確認。logging_setup は作成失敗時にコンソールのみで継続します。
- 設定が読み込まれない:
  - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を検出して行います。手動で .env を指定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI 呼び出し失敗:
  - OPENAI_API_KEY の設定、ネットワーク、API レート制限を確認。AI モジュールはリトライとフォールバック（0 またはスキップ）を行いますが、ログで詳細を確認してください。

付録: よく使うコマンド例
---------------------
- .env を対話生成:
  - python -m kabusys.config_setup
- 設定の事前検証:
  - python -m kabusys.validate_config
- 監視プロセス起動（デバッグ）:
  - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
- 実行エンジン（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート（過去期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上がこのリポジトリの概要と使い方です。必要があれば各モジュールの詳細な API ドキュメント（関数引数・返り値・例）も作成しますので、どの部分を優先して欲しいか教えてください。