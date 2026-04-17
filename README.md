README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究用ライブラリ群です。  
主な機能は次のとおりです:

- 実運用向け ExecutionEngine（発注管理・リスク管理・さくせん連携）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ポートフォリオ構築（銘柄選定・重み付け・株数計算・セクター制限）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- AI を使ったニュース NLP（OpenAI）と市場レジーム判定
- ペーパートレード用の分離 DB / 検証レポート生成ツール
- 環境設定ウィザードと設定検証 CLI

このリポジトリは「分析用 DuckDB」「監視用 SQLite」「（ペーパー用）SQLite」を使って動作します。実行環境は .env で設定します。

主な機能一覧
------------
- run_execution: ExecutionEngine の起動スクリプト（本番 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
  - 停止フラグ（data/stop_requested.flag）や kill.flag による安全停止処理
  - PID ファイル管理（data/execution.pid）

- run_monitoring: SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - SystemMonitor は常に本番用 sqlite_path を使用して監視ログを残す

- monitoring モジュール
  - SystemMonitor: CPU/メモリ/ディスク/プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン / ポジション上限の監視とログ化
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite テーブル（system_status / trade_logs / positions / risk_logs / dashboard）の作成・操作

- portfolio モジュール
  - 候補選定（select_candidates）、等重・スコア重み（calc_equal_weights / calc_score_weights）
  - リスク調整（apply_sector_cap / calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- research モジュール
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- ai モジュール
  - news_nlp.score_news: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM スコアを合成して market_regime を作成
  - OpenAI API キー（OPENAI_API_KEY）が必要。API 呼び出しはリトライ/フェイルセーフ実装あり

- tools
  - paper_verification_report: ペーパートレード SQLite（デフォルト data/paper_trading.db）から検証レポートを出力

セットアップ手順
----------------
1. リポジトリをクローンし、ソースがあるディレクトリへ移動
   - ソースは src/kabusys 以下に配置されています

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
     - その他標準ライブラリ（sqlite3 は標準）
   - オプション:
     - PyYAML（config/*.yaml の検証に利用）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # YAML 検証をしたい場合

4. .env の作成（推奨: ウィザードを使う）
   - python -m kabusys.config_setup
     - 対話式で .env を作成・更新します（.env は絶対に Git にコミットしないこと）
   - もしくは .env を直接作成し、必要な環境変数をセットしてください

5. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN（任意、アラート用）
- LINE_USER_ID（任意、アラート用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレードの約定モード: instant|partial|never|reject、デフォルト: instant）
- KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト 60）
- OPENAI_API_KEY（AI モジュールで必要）

使い方（CLI / 実行例）
---------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に書き込み（実口座と分離）
    - 起動時に data/stop_requested.flag が存在すれば起動せず終了
    - 実行中は data/execution.pid に PID を書きます（PID ファイルを用いたプロセス監視）

- Monitoring（SystemMonitor ポーリング）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で指定（例: MONITOR_POLL_INTERVAL=30）
  - 停止:
    - data/stop_requested.flag を作成すると監視ループは終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で SQLite ファイルを指定、環境変数 PAPER_TRADING_SQLITE_PATH も利用可

- AI / レジーム判定（プログラム呼び出し）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数 または関数呼び出しで api_key を渡す）
  - 例（Python から）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="sk-...")

停止と Kill Switch
------------------
- 常駐プロセスの停止は 2 パターン:
  - 管理的停止（監視/エンジンそれぞれ）:
    - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して終了します
  - 自動停止（Kill Switch）:
    - RiskMonitor が閾値（ドローダウンやポジション上限）を検知すると data/kill.flag を書き込みます
    - ExecutionEngine は起動時に kill.flag の存在をチェックし、存在する場合は起動しない／停止します

データベースと初期化
-------------------
- 監視 DB（SQLite）: デフォルト data/monitoring.db
  - init_monitoring_db() が必要なテーブル・インデックスを作成します（冪等）
  - run_execution / run_monitoring 起動時に自動でテーブルを作成します

- 分析 DB（DuckDB）: デフォルト data/kabusys.duckdb
  - research / ai モジュールは DuckDB 接続を受け取り SQL を直接実行します

- ペーパートレード DB（SQLite）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

実装上の注意点・設計方針
-----------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込みます
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能

- 本番 / ペーパーの分離:
  - ペーパートレード時は発注クライアントや DB を完全に分離する設計です

- LLM 呼び出し:
  - OpenAI 呼び出しはリトライやエラーハンドリングを行い、失敗時はフェイルセーフ（スコア 0.0 など）で継続します
  - 出力は厳密な JSON を期待して検証を行います

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — 市場レジーム判定

- monitoring/
  - monitoring_db.py       — SQLite テーブル作成 / 永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py       — （アラート送信ラッパー、詳細はソース参照）

- execution/               — 発注関連（OrderRepository 等）※一部ファイルはここに存在すると想定
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- tools/
  - paper_verification_report.py

- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

補足
----
- config/*.yaml のテンプレートや生成スクリプトはプロジェクトの別箇所（またはスクリプト）で用意されている想定です（validate_config による検証で警告が出ます）。
- ログレベルや挙動は .env の設定に依存します。KABUSYS_ENV を "live" に設定する際は注意して下さい（validate_config が警告を出します）。
- この README はソースコード内のドキュメント文字列に基づいて作成しています。実行前に .env を適切に用意し、validate_config でチェックしてください。

ライセンスや貢献ガイドなどはリポジトリルートの別ファイルを参照してください。