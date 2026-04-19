KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム「KabuSys」の実装（モジュール群）を含みます。
設計のポイントは安全性（ペーパートレード分離、Kill Switch、監視）、再現性（DuckDB を用いたリサーチ）、
および実運用で必要なユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証）にあります。

主な特徴
--------
- 本番 / ペーパートレードの明確な分離
  - KABUSYS_ENV により "development" / "paper_trading" / "live" を切り替え
  - paper_trading モードでは MockBroker を用い、専用の SQLite（data/paper_trading.db）へ記録
- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Monitoring のポーリングループ（run_monitoring.py）
- 監視機能（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager（アラート送信は LINE 等へ拡張可）
  - 監視ログは SQLite（monitoring.db）へ永続化
- ポートフォリオ構築ロジック（純粋関数）
  - 候補選定、等金額／スコア加重、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（DuckDB を利用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI 統合（OpenAI）
  - ニュース NLP（news_nlp）で銘柄ごとのセンチメントスコアを生成して ai_scores に書き込み
  - レジーム判定（regime_detector）で ma200 とマクロセンチメントを合成
- 運用ユーティリティ
  - 設定ウィザード（config_setup.py）で .env を対話的に作成
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

必須依存（概略）
----------------
- Python >= 3.10（typing の "|" 記法を使用）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合に有用だが必須ではない）
- sqlite3 は標準ライブラリに含まれます

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリに移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（プロジェクトルートに配置）
     - 最低限設定が必要な環境変数:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
     - 便利な環境変数:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
       - SQLITE_PATH — 監視 DB: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時）
       - LOG_LEVEL — DEBUG/INFO/...
       - OPENAI_API_KEY — AI モジュール利用時に必要
       - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする (0/1)

   - 自動ロード:
     - パッケージ起動時にプロジェクトルートの .env と .env.local を自動読み込みします（OS環境変数を上書きしない）。
     - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. ログディレクトリ
   - デフォルトで logs/ にアプリ別ログ（例: logs/execution.log, logs/monitoring.log）が日次ローテーションで書かれます。
   - 必要に応じて LOG_DIR を設定してください。

基本的な使い方
--------------

- 実行エンジンを起動（本番またはペーパー）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBroker が使用され PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません（安全措置）。
    - プロセス優先度は起動時に高（"high"）へ設定されます（set_process_priority）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 補足:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。
    - 停止は data/stop_requested.flag を作成することで行えます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能（プログラムから呼び出し）
  - ニュース NLP（ai.score_news）
    - 例: from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...) で実行（DuckDB 接続を渡す）
  - レジーム判定（ai.regime_detector.score_regime）
    - stock prices と raw_news を用いて market_regime テーブルへ書き込む

運用上の重要なファイル／フラグ
------------------------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py がポーリングループを終了するために参照する停止フラグ
- data/kill.flag
  - KillSwitch によって書き込まれ、ExecutionEngine に安全停止を促すためのフラグ
  - 本番では KILL_FLAG_CLEAR_ON_START=0（自動クリアしない）を推奨
- data/execution.pid
  - ExecutionEngine の PID ファイル（起動時に Engine に渡される）

設定（主な環境変数）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル（"DEBUG","INFO",...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（paper_trading 用）
- OPENAI_API_KEY — OpenAI を利用する AI モジュールで必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動消去するか（"0" or "1"）

ディレクトリ構成（抜粋）
-----------------------
（src/kabusys 以下。重要なファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py          — .env 対話的ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / DB 操作ラッパー
    - system_monitor.py      — システム監視ロジック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （発注監視ロジック、ファイル内で定義）
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねる Engine
    - alert_manager.py       — アラート送信（LINE 等へ拡張可能）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動 / セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py      — ブローカクライアント生成（Mock/実API 切替）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケールダウンロジック
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/ボラ/バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — IC / 統計サマリー 等
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - data/                    — 実行時に生成されることがある（DB ファイル・フラグ等）

開発・運用上の注意
-----------------
- 本番運用時（KABUSYS_ENV=live）は環境変数を慎重に管理してください（.env を Git へコミットしないこと）。
- Kill Switch / Stop フラグの取り扱いに注意してください。KILL_FLAG_CLEAR_ON_START=1 は開発時のみ推奨。
- AI 機能は外部 API（OpenAI）に依存します。API キーや呼び出し回数/レート制限に注意してください。
- DuckDB / SQLite のパスは .env で指定可能です。バックアップ / ファイルローテーション方針を検討してください。
- ロギングは logs/<app_name>.log に日次ローテーションで保存されます。ディスク容量に注意してください。

貢献・拡張
----------
- アラート送信（AlertManager）は LINE 以外の宛先へ拡張可能です。
- BrokerClientFactory に新しいブローカー実装（kabuステーション以外）を追加可能です。
- portfolio や research のロジックは純粋関数として設計されているため、ユニットテストが容易です。

ライセンス / バージョン
-----------------------
- __version__ は src/kabusys/__init__.py にて管理（現在 0.1.0）

最後に
------
この README はコードベースからの推測に基づく概要です。実際の運用やデプロイ前には
python -m kabusys.validate_config で設定検証を行い、.env の内容と DB パス・権限・ログ出力先を必ず確認してください。質問やドキュメント追記の要望があれば教えてください。