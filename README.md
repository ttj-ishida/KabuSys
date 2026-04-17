README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリには次の主要機能が含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine）/ 監視用ポーリングループ
- 監視ログ永続化（SQLite）と監視ロジック（CPU/メモリ/ディスク、データ鮮度、注文滞留、ドローダウン等）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算、将来リターン、IC、統計サマリー）
- AI 関連ユーティリティ（ニュースセンチメント、レジーム判定。OpenAI を利用）
- ペーパートレード検証レポート生成ツール

注: ここに記載の内容はリポジトリに含まれるソースから抜粋・要約したものです。

機能一覧
--------
- 設定管理
  - .env 自動ロード（.env, .env.local）、Settings クラス（kabusys.config）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行 / 監視
  - run_execution: ExecutionEngine の起動スクリプト（paper_trading 環境は専用 DB を使用）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - プロセス優先度設定ユーティリティ（psutil を使用）

- 監視系
  - MonitoringDB: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor: プロセス生存確認、CPU/Memory/Disk、データ鮮度チェック
  - TradeMonitor: 注文の滞留チェック・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクイベント記録
  - KillSwitch: 条件到達時に data/kill.flag を書いて ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Messaging API を使った一方向通知（クールダウン実装）

- ポートフォリオ構築
  - 候補選択（スコア降順）
  - 等ウェイト / スコア加重ウェイト
  - セクターキャップ適用
  - ポジションサイズ計算（risk_based / equal / score、単元株丸め、資金スケーリング）

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- AI（OpenAI を使用）
  - news_nlp: ニュース記事を集約して LLM による銘柄別センチメントを ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースを組み合わせて市場レジームを判定し DB に書込

- ツール
  - paper_verification_report: ペーパートレード DB（data/paper_trading.db）からレポートを生成

セットアップ手順
----------------

1. Python 環境（推奨: 3.9+）
   - 仮想環境を作成して有効化することを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本コードで使われる主要パッケージ（例）
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（config ファイルの検査に必要、任意）
   - 例:
     - pip install duckdb psutil openai requests PyYAML

3. 環境変数設定 (.env)
   - プロジェクトルートに .env（または .env.local）を作成してください。
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY
   - 代表的な変数（デフォルト値は .env.example を想定）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、default: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
   - 自動ロード:
     - kabusys.config はプロジェクトルートに .env/.env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. データディレクトリ
   - デフォルトでは data/ 以下に DB やフラグファイルを作成します。必要に応じて作成してください。
     - mkdir -p data

5. 設定ウィザード / 検証
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config
     - 警告も失敗とする場合: python -m kabusys.validate_config --strict

使い方
------

基本的な実行例

- ExecutionEngine を起動する（デフォルト: KABUSYS_ENV に応じて paper/live を切替）
  - python -m kabusys.run_execution
  - 補足:
    - paper_trading 環境では MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag があると起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます。
    - 停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）で制御できます。

- Monitoring（SystemMonitor ポーリング）を起動する
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を指します（monitoring 用 DB）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で上書き可。環境変数 PAPER_TRADING_SQLITE_PATH も使用可能。

- AI モジュール（プログラム内 API）
  - ニュースセンチメント:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)
  - 注意:
    - OpenAI API キー（OPENAI_API_KEY）を設定するか、api_key を関数に渡してください。
    - API 呼び出しはリトライ・フェイルセーフ処理がありますが、API クォータに注意してください。

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB 関連:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用: data/paper_trading.db)
- ログ / プロセス:
  - LOG_LEVEL (INFO 等)
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START (0/1)
- 監視:
  - MONITOR_POLL_INTERVAL（run_monitoring 用、秒）
- AI:
  - OPENAI_API_KEY（AI 機能使用時に必要）
- その他:
  - PAPER_FILL_MODE（paper_trading の約定挙動）

停止・Kill Switch の仕組み
- KillSwitch がトリガー条件に達すると data/kill.flag を書き込みます。ExecutionEngine はこのフラグを監視して安全に停止します。
- run_execution/run_monitoring は data/stop_requested.flag（および data/execution.pid 等）を利用して起動/停止の動作を制御しています。

トラブルシューティング
- 必須環境変数が未設定の場合、Settings が例外を投げます。まず python -m kabusys.validate_config で確認してください。
- .env が読み込まれない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。必要なら直接エクスポートして起動してください。
- OpenAI を使う機能で API が失敗する場合はログに WARN が出力され、フェイルセーフで継続されます（スコア 0.0 等でフォールバック）。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理（自動 .env ロード含む）
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP（OpenAI 連携）
  - regime_detector.py           — 市場レジーム判定（OpenAI 連携）

- monitoring/
  - monitoring_db.py             — Monitoring DB 初期化・永続化 API
  - system_monitor.py            — システム / データ鮮度監視
  - trade_monitor.py             — 注文滞留 / 約定異常監視
  - risk_monitor.py              — ドローダウン / ポジション上限監視
  - kill_switch.py               — Kill Switch（flag 書き込み）
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - alert_manager.py             — LINE 通知ユーティリティ

- portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 発注株数計算（単元丸め・資金配分）
  - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py           — Momentum / Volatility / Value ファクター
  - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - __init__.py

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
  - __init__.py

- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

data/
- デフォルトで使用されるディレクトリ（DB ファイル、pid、kill.flag、stop_requested.flag などを置く）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

ライセンス・注意
---------------
- .env ファイルには機密情報（API トークン等）が含まれます。決して Git にコミットしないでください。
- 本システムを live 環境で運用する際は、特に KABUSYS_ENV=live の警告を熟読し、kill スイッチや通知経路を適切に設定してください。
- AI（OpenAI）利用は API コストが発生します。利用には十分な注意と鍵の管理を行ってください。

問い合わせ・開発
----------------
- 開発者向け: 各モジュールはユニットテストしやすいように分離されています（DB 接続や API 呼び出し箇所は差し替え可能）。
- テスト時に .env の自動読み込みを止めたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

以上。必要なら README に追加してほしいコマンドや例（systemd ユニット、Dockerfile、requirements.txt のサンプル等）を教えてください。