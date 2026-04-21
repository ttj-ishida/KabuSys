# KabuSys

日本株向け自動売買システムの軽量実装 (KabuSys)。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視（Monitoring）・研究用ユーティリティ・AI連携モジュール等を含むモジュール群を提供します。

以下はリポジトリ内の主要な使い方・セットアップ・構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するコンポーネント群を提供します。主な目的は次のとおりです。

- ファクター計算・特徴量生成（research）
- ポートフォリオ構築（portfolio）
- 注文管理・発注エンジン（execution）
- ランタイム監視とアラート（monitoring）
- Paper Trading（検証用の分離された DB を使用）
- ニュース NLP やレジーム判定のための OpenAI 連携（ai）
- 各種ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード・検証スクリプト等）

本 README は提供されているコードベース (src/kabusys/...) に基づく利用手順と構成説明です。

---

## 主な機能一覧

- 設定管理 (.env 自動読み込み / Settings API)
- 対話式 .env 作成ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い、paper_trading DB に記録して本番 DB と分離
- 監視ループ起動スクリプト（run_monitoring.py）
  - 定期的に System / Trade / Risk を監視し、kill_flag を書き込む等の処理を行う
- MonitoringDB: SQLite に監視ログを保存（system_status / trade_logs / positions / risk_logs / dashboard）
- RiskMonitor: ドローダウンやポジション数上限の監視とアラート記録
- KillSwitch: 条件を満たすと data/kill.flag を書き込んで ExecutionEngine を停止させる仕組み
- Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- 研究用モジュール（ファクター計算・forward returns・IC計算など）
- AI モジュール:
  - news_nlp: raw_news を LLM（OpenAI）に投げて銘柄単位のセンチメントスコアを ai_scores テーブルへ保存
  - regime_detector: ETF 1321 の MA 乖離とマクロニュースの LLM 評価を合成して市場レジーム判定

---

## 前提・依存関係

必須（最低限）:

- Python 3.10+
- sqlite3（標準ライブラリ）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- （オプション）PyYAML — `kabusys.validate_config` が config/*.yaml のパースチェックを行う場合に必要

例（pip）:
pip install duckdb psutil openai PyYAML

※ 実際の production では更に必要なパッケージ（ExecutionEngine のブローカー用 SDK など）がある可能性があります。requirements.txt があればそれを利用してください。

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話で J-Quants トークンや Kabu API パスワード、DB パス、KABUSYS_ENV などを設定します
   - 生成された .env は絶対に Git にコミットしないでください
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付ける
6. データ／ログディレクトリの作成（必要なら）
   - デフォルト DB / ログパス:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite for monitoring)
     - data/paper_trading.db (Paper trading SQLite, PAPER_TRADING_SQLITE_PATH で上書き可)
     - logs/ (ログ出力先。LOG_DIR 環境変数で変更可)

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: run_execution は MockBroker を使用し paper DB を使う
  - live: 本番モード
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" で有効）

---

## 使い方

### 1) .env の生成（対話式）
python -m kabusys.config_setup

ウィザードで入力後、.env ファイルが作成されます。

### 2) 設定検証
python -m kabusys.validate_config
（--strict を付けると警告も FAIL 扱い）

### 3) 監視ループの起動
- 監視ループを起動すると SystemMonitor.check_once を定期実行して monitoring DB を更新します。
- デフォルトポーリング間隔は 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）。

実行:
python -m kabusys.run_monitoring

環境変数例:
export MONITOR_POLL_INTERVAL=30

停止方法:
- data/stop_requested.flag を作成すると監視ループは安全に終了します（run_monitoring 内の STOP フラグ）。
- kill.flag は ExecutionEngine を停止させるためのフラグ（KillSwitch が書く）です。

注意:
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して監視 DB に接続します。

### 4) Execution（発注エンジン）の起動
python -m kabusys.run_execution

挙動:
- Settings.env が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全分離）。
- 起動時に data/stop_requested.flag があれば起動せず終了します。
- 実行中は data/execution.pid に PID を出力し、data/stop_requested.flag を検知すると ExecutionEngine.stop() を呼んで停止します。

### 5) Paper Trading 検証レポート生成
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11

- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
- 期間フィルタを指定してシステム稼働率・注文成功率・レイテンシ等の指標を表示します

### 6) AI 機能（ニュースセンチメント / レジーム判定）
- OPENAI_API_KEY 環境変数を設定してください
- `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)` などの関数 API を通じて実行します
- コマンドラインの直接エントリは組まれていませんが、スクリプトや定期ジョブで呼び出す想定です

---

## ログと優先度

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます（TimedRotatingFileHandler、日次ローテーション、30日保管）。
- setup_logging(app_name="...") を各スクリプトで呼び出して一貫したログ設定を行います。
- 実行開始直後にプロセス優先度を "high" に設定する処理が含まれています（set_process_priority）。psutil を使って OS に依存した優先度 / CPU affinity を設定します。権限不足等で失敗してもログに警告を出して継続します。

---

## 停止・Kill Switch の仕組み

- KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor / SystemMonitor / TradeMonitor の結果に基づき data/kill.flag を書き込みます。ExecutionEngine は Settings.kill_flag_path を監視して停止する想定です。
- 手動で ExecutionEngine を停止したいときは data/kill.flag に理由を書き込むか、監視コンポーネントが自動で書き込みます。
- run_monitoring/run_execution は data/stop_requested.flag によりループや起動を止めるためのフラグを検出します（stop_requested.flag は一般的にオペレータが作成して停止を指示するためのファイルです）。

---

## よく使うコマンドまとめ

- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要なモジュールと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み / Settings クラス（.env 自動読み込み機構含む）
  - config_setup.py
    - .env を対話式に作るウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可能）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB（テーブル作成 + 永続化 API）
    - system_monitor.py — システムリソース・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 評価
    - monitoring_engine.py — 複数 Monitor を束ねてポーリングするエンジン
    - (alert_manager, trade_monitor などを含む想定)
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数計算・ラウンド処理・aggregate cap
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB 参照）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）を使った銘柄別スコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース LLM 合成）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

（上記はコードベースの抜粋に基づく要約です。実際のディレクトリにはさらに execution/*、data/*、strategy/* 等のモジュールが存在する想定です。）

---

## 注意事項 / ベストプラクティス

- .env は機密情報が含まれるため、決して Git へコミットしないでください。
- 本番（KABUSYS_ENV=live）では kill_flag や KILL_FLAG_CLEAR_ON_START の設定に注意してください（誤って自動クリアすると Kill Switch が無効化される恐れがあります）。
- OpenAI API を利用する機能は API 利用料が発生します。API キーは適切に管理してください。
- Paper Trading は本番 DB と分離するため、検証用 DB パスを必ず確認してください。
- DuckDB / SQLite のパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）は .env で明示的に指定しておくことを推奨します。
- validate_config を定期的に実行して設定不備を事前に検出してください。

---

問題があれば、どの部分（セットアップ / 実行 / あるモジュールの挙動）について詳しく知りたいかを教えてください。必要に応じてサンプル .env テンプレートや起動シナリオ（開発 vs paper_trading vs live）別の手順を詳細に作成します。