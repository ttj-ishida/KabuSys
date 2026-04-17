# KabuSys

KabuSys は日本株向けの自動売買・監視・リサーチ基盤を想定した Python コードベースです。本リポジトリは以下の主要機能群を含みます：注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ユーティリティ、ファクター計算 / リサーチ、AI（OpenAI を用いたニュースセンチメント / レジーム判定）、および運用用ツール。

以下にプロジェクトの概要・主要機能・セットアップ手順・使い方・ディレクトリ構成をまとめます。

## プロジェクト概要
- 目的：日本株の自動売買に必要な実行・監視・リサーチ機能を提供するライブラリ群と実行スクリプト。
- 設計方針：
  - 本番・Paper Trading の分離（KABUSYS_ENV による切替）。
  - データは主に SQLite（監視用・paper_trading 用）と DuckDB（時系列データ / リサーチ）に格納。
  - OpenAI（gpt-4o-mini 等）を用いるモジュールは API キーが必要で、失敗時はフォールバック動作をするようフェイルセーフ設計。
  - .env ファイルを自動で読み込む仕組みを備える（プロジェクトルートの検出に基づく）。

## 主な機能一覧
- Execution（起動スクリプト: run_execution.py）
  - Broker クライアントの切替（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）。
  - OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ。
- Monitoring（起動スクリプト: run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングで実行。
  - 監視ログを SQLite（data/monitoring.db デフォルト）に永続化。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）。
- Monitoring Dashboard
  - Streamlit ベースのダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）。
- Tools
  - paper_verification_report：Paper Trading DB を解析して検証レポートを出力。
- Portfolio（選定・配分・サイズ計算）
  - 銘柄選定、等配分・スコア配分、リスク調整（セクターキャップ・レジーム乗数）、単元株丸めなどの純粋関数群。
- Research
  - ファクター計算（momentum, volatility, value）、将来リターン計算、IC 計算、統計サマリ。
- AI
  - news_nlp: raw_news テーブルを集約し OpenAI でセンチメント評価 → ai_scores に書き込み。
  - regime_detector: ma200 乖離 + マクロニュースの LLM 評価を合成し market_regime を算出・保存。
- ユーティリティ
  - 設定管理（kabusys.config.Settings）: .env 読み込み、自動ロード、必須チェック。
  - process_priority / CPU affinity 設定ユーティリティ。
  - MonitoringDB: 監視用 DB の初期化・読み書きメソッド群。

## 必須環境・依存
- Python 3.9 以上（型注釈やモダンな構成に合わせた想定）
- 主な外部ライブラリ（参考）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリに含まれる）
- 実際のプロジェクトでは requirements.txt / Poetry 等で依存を固定してください。

## 環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK閾値など（Settings 参照）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動ロードを無効化

※設定は .env / .env.local / OS 環境変数の優先順位で自動ロードされます（プロジェクトルートが特定できた場合）。

## セットアップ手順（ローカル開発向け・例）
1. リポジトリをクローンしてプロジェクトルートへ移動。
2. Python 仮想環境を作る:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil requests openai streamlit
   - 実際は requirements.txt を用意して pip install -r requirements.txt を推奨
4. data ディレクトリを作成:
   - mkdir -p data
5. .env を作成し必要な環境変数を設定（.env.example を参照して必要値を用意してください）。
   - 例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
6. DuckDB / SQLite の初期データを用意（プロジェクトにスクリプトがある場合は実行）。
   - まずは最低限 monitoring DB を作るために run_monitoring/run_execution 実行時に init_monitoring_db が実行されます。

## 実行方法（代表的なコマンド）
- ExecutionEngine を起動（通常はサーバ上でデーモンとして実行）:
  - python -m kabusys.run_execution
  - 注意: 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - KABUSYS_ENV=paper_trading の場合は paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能。
  - Monitoring は KABUSYS_ENV に関わらず production sqlite_path（設定された SQLITE_PATH）を使用します。
- Streamlit ダッシュボード（監視 UI）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB が存在しない / 開けない場合はエラー表示（監視プロセスを先に起動してください）。
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）

## 運用に関する注意点
- プロセス優先度: run_execution / run_monitoring は起動時に set_process_priority("high") を試みます。権限がない環境では警告が出ますが処理は継続します。
- 停止フラグ:
  - data/stop_requested.flag: run_execution/run_monitoring はこのファイルを検知すると安全に終了します（運用側で stop 要求を行う仕組み）。
  - data/kill.flag: KillSwitch（リスク基準到達時）により作成され、ExecutionEngine に停止シグナルを送ります。KillSwitch は reason をファイルに書きます。
- Monitoring の永続データ:
  - init_monitoring_db は冪等でテーブル・インデックスを作成し、必要に応じて軽微なマイグレーション（カラム追加）を行います。
- Paper Trading と本番 DB の分離:
  - KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH を使用して本番 DB と完全に分離します。
- OpenAI 呼び出し:
  - API キーが必須（ai モジュール）。ネットワーク障害や 5xx、429 などの一部エラーはエクスポネンシャルバックオフでリトライし、最終的にはフォールバック（例: macro_sentiment = 0.0）して安全に継続します。
- ログレベル:
  - LOG_LEVEL 環境変数で制御可（DEBUG/INFO/...）。
- 注意点（よくある問題）:
  - streamlit で DB を読み込めない場合はパスや読み取り権限を確認してください（streamlit がローカルファイルを読み取れること）。
  - psutil による優先度/affinity 設定は権限不足で失敗することがあります（警告のみ）。
  - DuckDB executemany に空リストを渡すとエラーになる点に注意（コード中で対策済み）。

## ディレクトリ構成
主要なファイル・モジュールを概観します（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - portfolio/
      - __init__.py
      - portfolio_builder.py         — 候補選定・重み計算
      - position_sizing.py           — 株数計算・リスク制限
      - risk_adjustment.py           — セクター上限・レジーム乗数
    - research/
      - __init__.py
      - factor_research.py           — momentum / volatility / value 等
      - feature_exploration.py       — 将来リターン・IC・統計
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュース → OpenAI センチメント
      - regime_detector.py           — レジーム判定（MA + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py             — 監視 DB 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py             — LINE Push 通知
      - monitoring_engine.py         — 複数 monitor をまとめて実行
      - streamlit_dashboard.py       — Streamlit ダッシュボード
    - execution/
      - (order_manager.py, reconciler.py, order_repository.py, broker_factory 等のモジュール)
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - ...（ブローカー抽象・API 組込モジュールを想定）
    - data/                            — 実行時に利用される data/ 以下のファイル群（DB、pid、flag）
      - monitoring.db (デフォルト)
      - paper_trading.db (paper 用)
      - kabusys.duckdb (DuckDB)
      - execution.pid
      - stop_requested.flag
      - kill.flag

（注）実際のリポジトリには上記以外の補助モジュール・テストが含まれることがあります。

## 使い方の例（ワークフロー）
1. 開発環境でリサーチ:
   - DuckDB の prices_daily / raw_financials を用意し、kabusys.research.calc_* 関数を呼び出してファクターデータを計算。
2. Paper Trading（検証）:
   - KABUSYS_ENV=paper_trading を設定し run_execution を起動 → 発注は mock ブローカーで data/paper_trading.db に記録される。
   - 検証後に python -m kabusys.tools.paper_verification_report でレポートを確認。
3. 本番想定:
   - KABUSYS_ENV=live にして run_execution を運用環境で実行（実際には安全対策・監査が必要）。
4. 監視:
   - run_monitoring を常駐させて System/Trade/Risk を監視。問題を検知したら KillSwitch が data/kill.flag を書き込み ExecutionEngine を停止させる。

## トラブルシューティング（簡易）
- 「monitoring DB が見つからない／読み込めない」:
  - run_monitoring を先に起動して init_monitoring_db を実行するか、DB ファイルのパスを確認してください。
- 「OpenAI 呼び出しで失敗する」:
  - OPENAI_API_KEY の設定を確認。ネットワーク障害やレート制限が発生する場合、モジュール側でリトライ/フォールバックする設計です。
- 「PID / プロセス監視で stale PID が検出される」:
  - data/execution.pid を確認し、実際のプロセスが存在するか、ファイルのフォーマットが正しいか確認してください。stale の場合は自動で削除されます。
- 「プロセス優先度設定でエラー」:
  - psutil による優先度設定は権限が必要です。警告が出ますが通常は続行されます。

---

この README はコードベースから読み取れる設計意図・使用法をまとめたものであり、実際の運用では追加の安全対策（オーケストレーション、監査ログ、障害対応手順、権限管理など）が必要です。必要であれば、起動オプションの詳細、各モジュールの API ドキュメント、シーケンス図や運用チェックリストを別途作成します。どの情報を優先して追加しますか？