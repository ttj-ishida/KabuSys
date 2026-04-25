KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究基盤を想定した Python パッケージです。本リポジトリは以下を目的としたモジュール群を含みます。

- ExecutionEngine: 発注ロジック・リスク管理・約定処理（paper_trading 時は MockBroker）
- Monitoring: システム稼働監視・注文／リスク監視・Kill Switch
- Research: ファクター計算・特徴量探索
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制約
- AI: ニュース NLP を用いた銘柄センチメント・市場レジーム判定（OpenAI 利用）
- ユーティリティ群: ログ設定、プロセス優先度、設定読み込み等
- ツール: ペーパートレード検証レポート生成スクリプト等

主な設計方針:
- 本番 DB（monitoring 等）と paper_trading 用 DB を分離
- ルックアヘッドバイアス防止（date.today() を直接参照しない設計）
- フェイルセーフ（API 失敗時はフォールバックし継続）
- ロギングの統一（setup_logging）

機能一覧
--------
- 起動スクリプト:
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV により本番/ペーパー分離）
  - run_monitoring.py — SystemMonitor のポーリングループ
- 設定管理:
  - config_setup.py — .env 初期作成／対話ウィザード
  - validate_config.py — .env / config/*.yaml の検証 CLI
  - Settings クラスで環境変数を集約
- 監視:
  - monitoring_engine.py — 各モニタを束ねるループ
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 詳細監視
  - kill_switch.py — kill.flag による実行停止
  - monitoring_db.py — SQLite ベースの永続化層（テーブル作成・マイグレーション含む）
- 発注・実行:
  - execution.* — ブローカー抽象、注文管理、リスク管理、リコンサイル等（エンジン本体は ExecutionEngine）
  - BrokerFactory により paper_trading では MockBroker を使用
- 研究・解析:
  - research.factor_research — Momentum/Value/Volatility 等のファクター計算（DuckDB 経由）
  - research.feature_exploration — 将来リターン・IC・統計サマリー等
- ポートフォリオ構築:
  - portfolio.portfolio_builder, position_sizing, risk_adjustment
- AI:
  - ai.news_nlp.score_news — OpenAI を使ったニュースセンチメント（ai_scores テーブルへ書込）
  - ai.regime_detector.score_regime — MA とマクロセンチメントを合成した市場レジーム判定
- ツール:
  - tools.paper_verification_report — Paper Trading 結果の検証レポート生成

要件（推奨）
-------------
- Python 3.9+（コードの型注釈や一部機能に依存）
- 必須ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML （config 検証で YAML を解析する場合）
- その他: sqlite3 は標準ライブラリで提供

セットアップ手順
--------------
1. リポジトリをクローン / 展開する:
   - ソースルートに移動して作業を行ってください（config auto-load はプロジェクトルート検出を行います）。

2. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）:
   - pip install duckdb psutil openai PyYAML

   注: requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. .env の作成:
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成。最低必須:
     - JQUANTS_REFRESH_TOKEN=<your_token>
     - KABU_API_PASSWORD=<your_password>
   - OpenAI を使う場合:
     - OPENAI_API_KEY=<your_key>

   主要な環境変数（抜粋）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb（分析 DB）
   - SQLITE_PATH: data/monitoring.db（監視用 SQLite）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - LOG_LEVEL: INFO|DEBUG|...
   - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 用）
   - KILL_FLAG_CLEAR_ON_START: 0|1（Execution 起動時の kill flag 自動消去）

5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
起動方法（代表的なもの）:

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - 挙動:
    - Settings に従い DB 接続を作成（paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用）
    - BrokerClientFactory によりブローカークライアントを生成（paper_trading では Mock）
    - エンジンは別スレッドで run_session を実行、data/execution.pid へ PID を書くような動作（内部実装に依存）
    - 停止は data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が書かれると検知し停止

- Monitoring を起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルを記録します。

- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

AI 機能（OpenAI）
- ai.news_nlp.score_news / ai.regime_detector.score_regime は OpenAI API を利用します。環境変数 OPENAI_API_KEY を設定するか、api_key 引数を渡してください。
- レート制限・ネットワーク障害時はリトライロジックが入っていますが、API キー未設定時は ValueError を投げます。

停止・Kill Switch 等
- 手動停止フラグ: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します（両スクリプトで利用）。
- Kill Switch: RiskMonitor 等の判定で KillSwitch がトリガーされると data/kill.flag に理由が書き込まれ、ExecutionEngine 側で検出して安全に停止します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（TimedRotatingFileHandler）。
- 環境変数 LOG_DIR でログディレクトリを変更可能。コンソールには stdout へ出力されます。

ディレクトリ構成
----------------
（src/kabusys をルートとした主要ファイル／フォルダ）

- src/kabusys/
  - __init__.py
  - config.py                — 設定読み込み / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — Execution エントリポイント
  - run_monitoring.py        — Monitoring ポーリングエントリポイント
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化層
    - monitoring_engine.py   — 各 Monitor を束ねる
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - alert_manager.py*      — アラート管理（実装参照）
    - trade_monitor.py*      — 発注ログ・異常検知（実装参照）
  - execution/                — ExecutionEngine 周りの実装（broker, order_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度／CPU affinity 設定
  - data/ (実行時に作成される想定)
    - kabusys.duckdb (デフォルト位置)
    - monitoring.db
    - paper_trading.db

(*) 一部モジュールは上位の実装に依存するため、さらに実装ファイルがあります。

開発者向けノート
----------------
- DB マイグレーション: monitoring_db.init_monitoring_db() は起動時にテーブルの作成と簡易マイグレーション（カラム追加）を行います。
- プロセス優先度: 起動時に set_process_priority("high") を呼び出し、可能ならプロセス優先度を上げます（権限により警告でスキップされます）。
- DuckDB は分析用途で用いられ、research / ai モジュールはいずれも DuckDB 接続を受け取りローカルテーブルを参照します（本番 API へはアクセスしません）。
- テスト時に外部 API 呼び出しをモックできるよう設計されています（例: _call_openai_api の差替え）。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続します。

よくある操作例
--------------
- 開発環境でペーパートレードを開始する:
  1. .env で KABUSYS_ENV=paper_trading を設定
  2. python -m kabusys.run_execution
  3. 取引ログは data/paper_trading.db に保存される

- 監視ループを短間隔で動かす（デバッグ）:
  - MONITOR_POLL_INTERVAL=5 python -m kabusys.run_monitoring

- Paper Trading の検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- 本 README はソース内の docstring と実装を基に作成しています。実行時の詳細な振る舞いは各モジュールの docstring / 関数コメントを参照してください。
- ライセンス表記や requirements.txt、CI 設定は本リポジトリに応じて追加してください。

問題や不明点があれば、どの部分（起動、設定、AI 機能、DB 周りなど）について詳しく知りたいか教えてください。README をその内容に合わせて追記・修正します。