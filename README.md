README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買とそれを支える研究/監視ツール群をまとめた Python パッケージです。
主な目的は以下です。

- 株式取引の発注エンジン（ExecutionEngine）
- 監視・アラート（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio）
- ファクター計算や特徴量探索（Research）
- ニュース NLP を用いた AI スコアリング（AI モジュール）
- 開発支援ツール（設定ウィザード、設定検証、レポート生成）

設計上の特徴：
- 環境変数 / .env による設定（Settings クラス）
- 本番 / ペーパートレードの DB を分離（KABUSYS_ENV）
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB に使用
- OpenAI API を利用した NLP 処理（任意）

主な機能一覧
-------------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring.py）
  - システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視
  - kill.flag の書き込みにより ExecutionEngine に停止シグナルを送出
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - 対話式で .env を生成・更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の存在・基本整合性のチェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・約定率・レイテンシ等のサマリと PASS/FAIL 判定を出力
- Portfolio 関連（portfolio/）
  - 候補選定、ウェイト計算、リスク調整、株数決定ロジック（純粋関数）
- Research（research/）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算等
  - DuckDB を使ったオフライン計算を想定
- AI（ai/）
  - news_nlp: raw_news をまとめて LLM（OpenAI）でセンチメントスコア化して ai_scores に保存
  - regime_detector: 指標＋LLM による市場レジーム判定
- ユーティリティ（utils/）
  - ロギング設定、プロセス優先度／CPU affinity 設定など

セットアップ手順
----------------
1. リポジトリをクローン
   - 例: git clone <repo_url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なライブラリをインストール
   - 本プロジェクトで使用されている主要パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注: sqlite3 は標準ライブラリに含まれます。

4. .env を作成する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成（.env を Git にコミットしないこと）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリの確認
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要に応じて環境変数で上書き

主要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API を使う場合に設定
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時のモック約定モード: instant|partial|never|reject）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト logs/）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
- PID_FILE_PATH / KILL_FLAG_PATH（ファイルパスを変更したい場合）

使い方（主要コマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（本番 / ペーパーいずれも同スクリプト）
  - python -m kabusys.run_execution
  - ポイント:
    - KABUSYS_ENV=paper_trading のとき paper_trading 用 DB に記録され、本番 DB と分離されます
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します
    - 実行中に data/stop_requested.flag を作成すると停止します
    - 実行中は設定で指定した PID ファイル（デフォルト data/execution.pid）を使用

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）
  - 監視は常に本番用の sqlite_path を使って監視テーブルを初期化します（環境に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（プログラム API）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
    - API キーを引数で渡すか、OPENAI_API_KEY を環境変数で設定
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

停止・Kill Switch
-----------------
- 監視系モジュールは評価により data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動で停止したい場合は data/stop_requested.flag（run scripts が参照する停止フラグ）を作成してください。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を削除します（本番では危険なので 0 推奨）。

ディレクトリ構成（主要ファイル）
--------------------------------
（プロジェクトルート: src/kabusys を想定）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings クラス（デフォルト値・検証）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py          — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py            — SQLite 監視テーブルの初期化・ラッパ
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — （注文系監視。実装参照）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 管理
    - monitoring_engine.py        — 各モニタの統合ループ
    - alert_manager.py            — （通知管理。実装参照）
  - execution/
    - execution_engine.py         — ExecutionEngine（起動・セッション管理）
    - broker_factory.py           — Broker クライアント生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...
  - portfolio/
    - portfolio_builder.py        — 候補選定・ウェイト計算
    - risk_adjustment.py          — セクター上限・レジーム乗数
    - position_sizing.py          — 株数決定・aggregate cap
  - research/
    - factor_research.py          — ファクター計算（mom, vol, value）
    - feature_exploration.py      — 将来リターン・IC・統計サマリ
  - data/                         — 生成される DB / フラグファイル など（runtime）
    - monitoring.db (default)
    - paper_trading.db (default)
    - kabusys.duckdb (default)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - utils/
    - logging_setup.py            — 統一的なログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity 設定

注意事項 / 運用上のヒント
------------------------
- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の扱いに注意してください。
- OpenAI を利用する機能は API キーとコストが必要です。API 呼び出しはリトライやフェイルセーフを組み込んでいますが、実運用ではレートやコストに注意してください。
- DuckDB / SQLite のファイルは運用環境で適切にバックアップしてください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR を環境変数で変更できます。
- unit tests は本 README に含まれていませんが、各モジュールは純粋関数で設計された箇所が多く、単体テストが書きやすくなっています。

ライセンス / 貢献
-----------------
- プロジェクトのライセンスやコントリビュート手順はリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください。

問い合わせ
----------
- 実装に関する質問やバグ報告はリポジトリの issue を作成してください。

以上。必要であれば、README にサンプル .env や systemd / supervisor のサービス設定例、Dockerfile などの運用例も追記します。どの情報を追加しますか？