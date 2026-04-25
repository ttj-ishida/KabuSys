KabuSys — 日本株自動売買システム
=================================

本 README は提供されたコードベース（src/kabusys 以下）についての概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

※ この README はソースに含まれる docstring やコードコメントを基に作成しています。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システム（実運用とペーパートレードの両対応）です。  
主な機能は次のとおりです。

- 注文実行（ExecutionEngine）／ペーパートレード対応（MockBroker）
- 監視（Monitoring）: システム状態・データ鮮度・注文の異常検知・リスク監視・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 計算、特徴量解析）
- AI（OpenAI）ベースのニュースセンチメント評価・市場レジーム判定
- ユーティリティ: .env ウィザード、設定検証、レポート生成（Paper Trading 検証）

主要機能一覧
-------------
- 実行（run_execution.py）
  - KABUSYS_ENV により実運用 / ペーパートレードを切替
  - PaperTrading 時は専用 SQLite DB（data/paper_trading.db）に記録
  - リスク管理（RiskManager）や注文管理（OrderManager）を内包
- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - 異常があればアラートや kill.flag 書き込み
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）
- ポートフォリオ（kabusys.portfolio）
  - 銘柄選定、等金額/スコア重み付け、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- リサーチ（kabusys.research）
  - モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB 経由）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI（kabusys.ai）
  - news_nlp: OpenAI によるニュースセンチメントの取得・ai_scores への書き込み
  - regime_detector: MA + マクロニュースを組み合わせた市場レジーム判定（DuckDB 使用）
- ツール
  - config_setup: .env を対話式で生成・更新
  - validate_config: .env / config/*.yaml の静的チェック
  - paper_verification_report: Paper Trading の期間別検証レポート生成

前提条件 / 依存ライブラリ
-------------------------
想定 Python バージョン: 3.9+（ソースは型注釈と pathlib を多用）  
主な依存ライブラリ（例）:
- duckdb
- psutil
- openai
- PyYAML（設定検証時に YAML ファイルを検証する場合）
標準ライブラリ: sqlite3, logging, threading, datetime, os, time など

インストール例:
- 仮想環境作成（推奨）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローン / コピー
2. Python 仮想環境を用意して依存をインストール（上記参照）
3. .env の用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - もしくはプロジェクトルートに .env を手動作成
   - 自動ロード:
     - config モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込みします。
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗（exit 1）扱いになります
5. ログディレクトリ・データディレクトリ作成
   - デフォルトで logs/（ログ）や data/（SQLite, pid, flag 等）を使用します。起動時に自動作成されますが権限に注意してください。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- LOG_LEVEL: ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）

使い方（実行コマンド）
--------------------

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 起動前に KABUSYS_ENV を適切に設定（paper_trading / live / development）
  - 停止: プロジェクト内 data/stop_requested.flag を作成すると安全に停止します。
  - 実行時は data/execution.pid に PID を書きます。

- 監視（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能
  - 停止: data/stop_requested.flag により監視ループが終了します
  - 監視は常に本番の sqlite_path を参照する（環境に関わらず）

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告を FAIL 扱いにできます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書きできます

AI 関連
-------
- OpenAI を使う機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です
- news_nlp.score_news は DuckDB 接続を受け取り ai_scores テーブルへ書き込みを行います
- API エラーはリトライ処理あり。失敗時はフォールバックして継続する設計です

重要なファイル / フラグ
-----------------------
- data/kill.flag: Kill Switch（監視が問題を検出した際に ExecutionEngine を停止するために書き込まれる）
- data/stop_requested.flag: 開発用・運用用の停止フラグ。run_monitoring/run_execution はこのファイルの存在を見て終了する
- data/execution.pid: ExecutionEngine の PID（起動時に書き込み）
- logs/<app>.log: 日次ローテートで出力されるログ（デフォルト logs/ ディレクトリ）

ディレクトリ構成
-----------------
（src/kabusys 以下の主要なファイル・パッケージを示します）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込みロジック（.env 自動読み込み含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - utils/
    - logging_setup.py        — 統一ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB レイヤ
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — (trade 監視、コード省略)
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 制御
    - monitoring_engine.py    — 複数 Monitor を束ねるエンジン
    - alert_manager.py        — (アラート送信ロジック、コード省略)
  - execution/
    - execution_engine.py     — 実行エンジン本体
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文リポジトリ（DB）
    - broker_factory.py       — ブローカークライアント生成（Mock/実装）
    - reconciler.py           — ブローカーと DB の突合せ
    - risk_manager.py         — 発注時のリスクチェック
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み付け
    - position_sizing.py      — 株数計算 / aggregate cap
    - risk_adjustment.py      — セクター制約 / レジーム乗数
  - research/
    - factor_research.py      — モメンタム / ボラ / バリュー計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - data/                     — デフォルトで使用するデータファイル（logs, sqlite, duckdb 等）

（省略されているファイルや完全な一覧はリポジトリの実ファイルを参照してください）

運用上の注意 / トラブルシューティング
-----------------------------------
- 本番（KABUSYS_ENV=live）では設定ミスによる誤発注を防ぐため validate_config で警告・必須値を厳密に確認してください
- KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（kill.flag を自動クリアして保護機能を無効化するため）
- logs ディレクトリの作成に失敗するとファイルハンドラが無効化されコンソール出力のみになります。パーミッションに注意
- OpenAI 利用部分は API 費用が発生します。API キー管理とコスト管理を行ってください
- DuckDB / SQLite のパスは .env で変更できます。監視用 DB とペーパートレード DB は分離推奨です
- MONITOR_POLL_INTERVAL に 0 以下を設定すると無効値扱いでデフォルト 60 秒が使われます

開発・拡張のヒント
-------------------
- DuckDB 接続をテスト用に in-memory で作るとロジック単体テストが書きやすいです
- OpenAI 呼び出しは各モジュール内でラップされているため unittest.mock.patch で差し替えてテスト可能です
- portfolio / research の関数群は副作用を持たない純関数設計が基本なので単体テストを追加しやすいです

ライセンス・貢献
----------------
この README ではライセンスや貢献ルールについての記載はありません。実プロジェクトに適用する場合は LICENSE ファイルや CONTRIBUTING.md をプロジェクトルートに用意してください。

最後に
-------
まずは .env を作成し、python -m kabusys.validate_config でチェック、続いて python -m kabusys.run_monitoring と python -m kabusys.run_execution（または paper_trading モード）で動作を確認してください。必要があれば AI 機能を有効にするため OPENAI_API_KEY を設定してください。

必要に応じて README の補足（依存バージョン、例の .env、systemd / supervisor 用の起動例 等）を追加します。どの情報を追記したいか教えてください。