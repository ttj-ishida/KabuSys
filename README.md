# KabuSys

日本株自動売買システムのコアライブラリと起動スクリプト群。  
このリポジトリは、戦略・ポートフォリオ構築、発注実行（本番／ペーパートレード分離）、監視、AI（ニュースセンチメント・レジーム判定）、および各種ユーティリティを含みます。

> バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要（プロジェクト概要）

KabuSys は日本株の自動売買エンジン向けに設計されたモジュール群です。主な機能は次のとおりです。

- 戦略／リサーチ（DuckDBを用いたファクター計算、将来リターン、IC等）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、ポジションサイズ計算）
- 実行エンジン（Broker クライアント抽象化、ペーパートレードと本番分離）
- 監視（システム・取引・リスク監視、Kill Switch）
- AI モジュール（ニュースセンチメント、レジーム判定：OpenAI を利用）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- 運用ツール（Paper Trading 検証レポート生成など）

---

## 機能一覧（ハイレベル）

- cli / 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV に応じて実際発注または Mock）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - validate_config.py — .env や config/*.yaml の事前検証
  - config_setup.py — .env の対話式生成／更新ウィザード
  - tools.paper_verification_report — ペーパートレード結果の集計レポート
- データ／DB
  - DuckDB: 分析用（デフォルト `data/kabusys.duckdb`）
  - SQLite: 監視／発注ログ（デフォルト `data/monitoring.db`、ペーパートレードは分離 `data/paper_trading.db`）
- 監視
  - system_monitor: CPU/メモリ/ディスク/実行プロセス・データ鮮度監視とログ書込み
  - trade_monitor: 発注ログの監視（滞留注文、約定異常等）
  - risk_monitor: ドローダウン・ポジション上限監視、dashboard 更新、risk_logs 追記
  - monitoring_engine: 各 Monitor をまとめてポーリング・アラート通知
  - kill_switch: 条件に応じた `data/kill.flag` 書き込み（ExecutionEngine 停止トリガ）
- ポートフォリオ
  - 候補選定、等配分・スコア配分、スコア正規化（zscore は data.stats 由来）
  - セクター上限適用、レジーム乗数、ポジションサイジング（単元株対応・コストバッファ・aggregate cap）
- AI
  - news_nlp.score_news: raw_news から銘柄毎にニュースを集約して OpenAI でセンチメント評価、`ai_scores`へ書込
  - regime_detector.score_regime: ETF(1321) の MA とマクロ記事センチメントを合成して market_regime を作成
- ユーティリティ
  - logging_setup.setup_logging: stdout と日次ローテートファイル出力を統一的に設定
  - process_priority.set_process_priority / set_cpu_affinity: クロスプラットフォームの優先度設定
  - config.Settings: 環境変数管理（自動 .env ロード機能あり）

---

## 前提条件 / 必要ライブラリ

少なくとも以下の Python パッケージが必要です（バージョンはプロジェクトポリシーに合わせてください）。

- Python 3.9+（型ヒントや pathlib 等を考慮）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を行う場合）

標準ライブラリ: sqlite3, logging, threading, datetime, json 等

（requirements.txt は本リポジトリに含まれていない想定です。プロジェクト配布時に追加してください。）

---

## セットアップ手順

例: Unix 系 (macOS / Linux)

1. レポジトリをクローン（省略）
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （AI 機能や config 検証が不要であれば openai / pyyaml を省略可能）
4. 環境変数設定 (.env)
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（例は下記「主要な環境変数」参照）
5. 設定検証（起動前のチェック）
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再度検証
6. DB・データディレクトリ
   - 監視スクリプト実行時に必要フォルダ（data, logs）は自動作成されることが多いですが、権限や配置を確認してください。

注意:
- .env は機密情報（API トークン、パスワード）を含むため Git に絶対にコミットしないでください。

---

## 主要な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に分離
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- OPENAI_API_KEY — OpenAI を利用する場合必須（news_nlp / regime_detector）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行管理・Kill Switch 関連

より詳細は src/kabusys/config.py を参照してください。

---

## 実行方法（基本的な使い方）

- 環境ファイルの作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit code 1）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データはペーパー用 SQLite に記録され本番 DB と分離されます。
  - 停止: `data/stop_requested.flag` を作成するとスレッドが検知して停止します。
  - エンジンは `data/execution.pid` を使用してプロセス管理を行います。

- 監視ループ起動（SystemMonitor）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  - 監視は Settings に従って本番 sqlite_path を使用（監視は環境に依存せず本番 DB を参照する仕様）。
  - 停止: `data/stop_requested.flag` を作成するとループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能。指定がなければ PAPER_TRADING_SQLITE_PATH 環境変数、さらにデフォルト `data/paper_trading.db` の順で決定。

- AI バッチ処理（プログラムやスケジューラから呼び出す）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

注意:
- OpenAI を使う関数は OPENAI_API_KEY を必要とし、未設定時は ValueError を送出します。
- AI 呼び出しはリトライ・バックオフの仕組みを持ちますが、API の失敗は基本的にフェイルセーフ（スコア 0 など）で継続する設計です。

---

## 停止／Kill Switch と運用ノート

- 停止フラグ（run_monitoring/run_execution）
  - data/stop_requested.flag を作成するとスクリプトは安全にループを抜けます（再起動時は削除が必要）。

- Kill Switch（KillSwitch）
  - リスク条件（ドローダウン超過やポジション上限超過）を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START=0`（自動クリア無効）を推奨します。

- PID ファイル
  - ExecutionEngine は `data/execution.pid` を使用して自身の PID を管理します。

- ログ
  - logs/<app_name>.log に日次ローテーションでログを保存（デフォルト 30 日分保持）。
  - ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLU / OpenAI 呼び出し
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py       — システム状態・データ鮮度チェック
    - trade_monitor.py        — 取引ログ監視（概念）
    - risk_monitor.py         — ドローダウン・ポジション監視
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - kill_switch.py          — Kill Switch 制御
    - alert_manager.py        — アラート送信（概念）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記に含まれないファイルは実装詳細や補助モジュールです。実運用では execution 以下のブローカー実装等が必要になります。）

---

## 使い方の例（短いワークフロー）

1. 仮想環境を用意して依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で検証
4. 本番発注を行う場合:
   - KABUSYS_ENV=live python -m kabusys.run_execution
5. 監視プロセスを別プロセスで起動:
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
6. ペーパートレードの評価:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-30

---

## よくあるトラブルとヒント

- OPENAI_API_KEY が未設定で AI 機能を実行すると ValueError になります。環境変数か関数引数で指定してください。
- psutil で優先度設定がアクセス拒否されることがあります（権限不足）。その場合は警告が出て処理は継続します。
- DuckDB / SQLite のパスに指定したディレクトリが存在しない場合、validate_config は警告を出します（多くのスクリプトは起動時にディレクトリを作成しますが、権限に注意）。
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください。

---

## 開発者向けメモ

- モジュールは可能な限り副作用を避け、DB 接続や DuckDB 接続は呼び出し元で注入するスタイルです（テスト容易性向上）。
- AI 呼び出し部分はリトライ・バックオフを備えています。テスト時には _call_openai_api をモックしてください。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB にないカラムを追加する簡易マイグレーション処理を含みます。

---

必要であれば、README に「API リファレンス」「実行時の環境変数一覧の詳細」「運用手順（systemd / supervisor 用のユニット例）」などの節を追加できます。どの追加情報が必要か教えてください。